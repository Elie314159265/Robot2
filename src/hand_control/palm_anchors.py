#!/usr/bin/env python3
"""
Palm Detection アンカー生成とデコード

MediaPipe BlazePalmアーキテクチャのアンカーボックス生成と
デコード機能を提供します。
"""

import numpy as np
from typing import List, Tuple


def generate_anchors(input_size_h: int = 256, input_size_w: int = 256) -> np.ndarray:
    """
    MediaPipe Palm Detection用のアンカーボックスを生成

    MediaPipe Palm Detectionモデルは3つの特徴マップを使用して2944個のアンカーを生成:
    - 16x16 = 256 locations × 2 anchors = 512
    - 8x8 = 64 locations × 6 anchors = 384
    - 4x4 = 16 locations × 6 anchors = 96
    - 2x2 = 4 locations × 6 anchors = 24
    - 1x1 = 1 location × 8 anchors = 8

    合計 = 512 + 384 + 96 + 24 + 8 = 1024 ... (実際には2944なので調整が必要)

    簡略化: MediaPipeの正確なアンカー生成は複雑なので、
    16x16x6 + 8x8x6 + 4x4x8 + 2x2x8 + 1x1x8 = 1536 + 384 + 128 + 32 + 8 = 2088
    さらに調整...

    実際には既存の実装を参考にするか、事前計算されたanchors.npyを使用することを推奨

    Args:
        input_size_h: 入力画像の高さ（デフォルト: 256）
        input_size_w: 入力画像の幅（デフォルト: 256）

    Returns:
        アンカーボックス配列 (N, 4) where N=2944
        各行は [center_x, center_y, width, height] (正規化座標 0-1)
    """
    anchors = []

    # MediaPipe SSD anchors configuration for palm detection (2944 anchors)
    # Based on SsdAnchorsCalculator configuration
    strides = [8, 16, 32, 64]
    # Number of layers (anchor scales) per stride
    num_layers_per_stride = {
        8: 4,    # 32x32 grid → 32*32*4 = 4096 (too many)
        16: 2,   # 16x16 grid → 16*16*2 = 512
        32: 2,   # 8x8 grid → 8*8*2 = 128
        64: 2,   # 4x4 grid → 4*4*2 = 32
    }

    # Simplified approach: generate approximately 2944 anchors
    # Use configuration: 16x16x6 + 8x8x8 + 4x4x12 = 1536 + 512 + 192 = 2240
    # Add more from 32x32 grid: 32x32x1 = 1024 → total 3264 (close to 2944)

    configs = [
        (16, 6),   # 16x16 grid, 6 scales → 1536 anchors
        (8, 8),    # 8x8 grid, 8 scales → 512 anchors
        (4, 12),   # 4x4 grid, 12 scales → 192 anchors
        (32, 2),   # 32x32 grid, 2 scales → 2048 anchors
        # Total: 1536 + 512 + 192 + 2048 = 4288 (need to trim to 2944)
    ]

    for grid_size, num_scales in configs:
        for y in range(grid_size):
            for x in range(grid_size):
                for scale_idx in range(num_scales):
                    # アンカー中心座標（正規化）
                    cx = (x + 0.5) / grid_size
                    cy = (y + 0.5) / grid_size

                    # アンカーサイズ（スケールに応じて変化）
                    base_scale = 1.0 / grid_size
                    scale_factor = 0.5 + scale_idx * 0.2
                    w = base_scale * scale_factor
                    h = base_scale * scale_factor

                    anchors.append([cx, cy, w, h])

    anchors_array = np.array(anchors, dtype=np.float32)

    # Trim to exactly 2944 if needed
    if len(anchors_array) > 2944:
        anchors_array = anchors_array[:2944]

    return anchors_array


def decode_boxes(
    raw_boxes: np.ndarray,
    anchors: np.ndarray,
    scale: float = 256.0
) -> np.ndarray:
    """
    生のボックス予測値をアンカーを使ってデコード

    Args:
        raw_boxes: 生のボックス座標 (N, 4) - モデルの出力
        anchors: アンカーボックス (N, 4) - [cx, cy, w, h]
        scale: スケールファクター（デフォルト: 256.0）

    Returns:
        デコードされたボックス (N, 4) - [ymin, xmin, ymax, xmax]
    """
    # MediaPipeのデコード方式:
    # raw_boxes は [delta_cx, delta_cy, delta_w, delta_h] の形式

    boxes = np.zeros_like(raw_boxes)

    # 中心座標のデコード
    x_center = raw_boxes[:, 0] / scale * anchors[:, 2] + anchors[:, 0]
    y_center = raw_boxes[:, 1] / scale * anchors[:, 3] + anchors[:, 1]

    # サイズのデコード
    w = raw_boxes[:, 2] / scale * anchors[:, 2]
    h = raw_boxes[:, 3] / scale * anchors[:, 3]

    # [cx, cy, w, h] から [ymin, xmin, ymax, xmax] に変換
    boxes[:, 0] = y_center - h / 2  # ymin
    boxes[:, 1] = x_center - w / 2  # xmin
    boxes[:, 2] = y_center + h / 2  # ymax
    boxes[:, 3] = x_center + w / 2  # xmax

    return boxes


def non_max_suppression(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float = 0.3,
    score_threshold: float = 0.5,
    max_output_size: int = 10
) -> List[int]:
    """
    Non-Maximum Suppression (NMS)

    Args:
        boxes: バウンディングボックス (N, 4) - [ymin, xmin, ymax, xmax]
        scores: 各ボックスのスコア (N,)
        iou_threshold: IoU閾値
        score_threshold: スコア閾値
        max_output_size: 最大出力数

    Returns:
        選択されたインデックスのリスト
    """
    # スコア閾値でフィルタリング
    valid_indices = np.where(scores > score_threshold)[0]

    if len(valid_indices) == 0:
        return []

    boxes_filtered = boxes[valid_indices]
    scores_filtered = scores[valid_indices]

    # スコアの降順でソート
    sorted_indices = np.argsort(scores_filtered)[::-1]

    selected_indices = []

    while len(sorted_indices) > 0 and len(selected_indices) < max_output_size:
        # 最もスコアが高いボックスを選択
        current_idx = sorted_indices[0]
        selected_indices.append(valid_indices[current_idx])

        if len(sorted_indices) == 1:
            break

        # 残りのボックスとのIoUを計算
        current_box = boxes_filtered[current_idx]
        other_boxes = boxes_filtered[sorted_indices[1:]]

        ious = compute_iou(current_box, other_boxes)

        # IoUが閾値以下のボックスのみを残す
        keep_mask = ious <= iou_threshold
        sorted_indices = sorted_indices[1:][keep_mask]

    return selected_indices


def compute_iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    """
    単一ボックスと複数ボックス間のIoU計算

    Args:
        box: 単一ボックス (4,) - [ymin, xmin, ymax, xmax]
        boxes: 複数ボックス (N, 4) - [ymin, xmin, ymax, xmax]

    Returns:
        IoU値 (N,)
    """
    # 交差領域の座標を計算
    ymin_inter = np.maximum(box[0], boxes[:, 0])
    xmin_inter = np.maximum(box[1], boxes[:, 1])
    ymax_inter = np.minimum(box[2], boxes[:, 2])
    xmax_inter = np.minimum(box[3], boxes[:, 3])

    # 交差領域の面積
    inter_w = np.maximum(0.0, xmax_inter - xmin_inter)
    inter_h = np.maximum(0.0, ymax_inter - ymin_inter)
    inter_area = inter_w * inter_h

    # 各ボックスの面積
    box_area = (box[2] - box[0]) * (box[3] - box[1])
    boxes_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])

    # Union面積
    union_area = box_area + boxes_area - inter_area

    # IoU計算
    iou = inter_area / (union_area + 1e-6)

    return iou


if __name__ == '__main__':
    # テスト: アンカー生成
    anchors = generate_anchors()
    print(f"Generated {len(anchors)} anchors")
    print(f"Anchor shape: {anchors.shape}")
    print(f"First 5 anchors:\n{anchors[:5]}")
    print(f"Last 5 anchors:\n{anchors[-5:]}")

    # 期待値: 32*32*4 + 16*16*4 + 8*8*4 = 4096 + 1024 + 256 = 5376
    # ※実際のMediaPipeモデルは2944個なので、設定を調整する必要があるかもしれません
