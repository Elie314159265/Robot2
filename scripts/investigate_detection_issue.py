#!/usr/bin/env python3
"""
ボール検出問題の徹底調査スクリプト
すべての検出結果を詳細に表示
"""

import sys
import os
import time
import numpy as np
from PIL import Image
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

print("=" * 80)
print("🔍 ボール検出問題の徹底調査")
print("=" * 80)

# ラベル読み込み
labels_path = "models/coco_labels.txt"
with open(labels_path, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

print(f"\n📝 COCOラベル一覧（関連するもの）:")
print(f"  Class 32: sports ball (index 32)")
print(f"  Class 37: {labels[37] if 37 < len(labels) else 'N/A'}")
print(f"  Class 40: {labels[40] if 40 < len(labels) else 'N/A'}")
print(f"  Class 41: {labels[41] if 41 < len(labels) else 'N/A'}")

# TPUモデル初期化
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
print(f"\n📦 TPUモデル読み込み: {model_path}")

interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()
print("✅ Edge TPU モデル読み込み完了")

# カメラ初期化
print("\n📷 カメラを初期化中...")
camera = CameraController(resolution=(640, 480), framerate=30, debug=False)
camera.initialize()
camera.start()
time.sleep(2)
print("✅ カメラ初期化完了")

print("\n" + "=" * 80)
print("🎬 サッカーボールをカメラに映してください")
print("=" * 80)
print("\n10秒後に撮影を開始します...")
time.sleep(10)

def resize_with_pil(image_rgb, target_size):
    """PIL + LANCZOS補間"""
    pil_image = Image.fromarray(image_rgb)
    pil_image = pil_image.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(pil_image)

# 5フレーム撮影して詳細分析
print("\n" + "=" * 80)
print("📸 5フレームを撮影して詳細分析")
print("=" * 80)

for frame_num in range(5):
    print(f"\n{'='*80}")
    print(f"フレーム #{frame_num + 1}")
    print(f"{'='*80}")

    frame = camera.capture_frame()
    if frame is None:
        continue

    # PIL + LANCZOSでリサイズ
    input_size = common.input_size(interpreter)
    resized = resize_with_pil(frame, (input_size[1], input_size[0]))

    # TPU推論
    common.set_input(interpreter, resized)
    interpreter.invoke()

    # 検出結果取得（複数の閾値で）
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

    for threshold in thresholds:
        detections = detect.get_objects(interpreter, score_threshold=threshold)

        if len(detections) > 0:
            print(f"\n📊 閾値 {threshold:.1f} での検出結果: {len(detections)}件")

            for i, det in enumerate(detections):
                class_name = labels[det.id] if det.id < len(labels) else f"Unknown({det.id})"
                bbox = det.bbox

                print(f"\n  [{i+1}] Class {det.id}: {class_name}")
                print(f"      Score: {det.score:.4f}")
                print(f"      BBox: xmin={bbox.xmin}, ymin={bbox.ymin}, xmax={bbox.xmax}, ymax={bbox.ymax}")
                print(f"      Size: width={bbox.xmax-bbox.xmin}, height={bbox.ymax-bbox.ymin}")

                # ボール関連クラスかチェック
                if det.id == 32 or det.id == 37:
                    print(f"      ⚽ **これはボール関連のクラスです！**")
        else:
            if threshold == 0.1:
                print(f"\n❌ 閾値 {threshold:.1f} でも何も検出されませんでした")

    time.sleep(1)

# フレームを保存して後で確認できるようにする
print("\n" + "=" * 80)
print("💾 最後のフレームを保存中...")
print("=" * 80)

frame = camera.capture_frame()
if frame is not None:
    # 元フレーム保存
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    cv2.imwrite("debug_frame_original.jpg", frame_bgr)
    print("✅ 元フレーム保存: debug_frame_original.jpg")

    # リサイズ後のフレーム保存
    input_size = common.input_size(interpreter)
    resized = resize_with_pil(frame, (input_size[1], input_size[0]))
    resized_bgr = cv2.cvtColor(resized, cv2.COLOR_RGB2BGR)
    cv2.imwrite("debug_frame_resized.jpg", resized_bgr)
    print("✅ リサイズ後フレーム保存: debug_frame_resized.jpg")

    # 検出結果を画像に描画
    common.set_input(interpreter, resized)
    interpreter.invoke()
    detections = detect.get_objects(interpreter, score_threshold=0.1)

    if detections:
        # 元画像に検出結果を描画
        frame_with_boxes = frame.copy()
        h, w = frame.shape[:2]

        for det in detections:
            bbox = det.bbox
            xmin = int(bbox.xmin * w)
            ymin = int(bbox.ymin * h)
            xmax = int(bbox.xmax * w)
            ymax = int(bbox.ymax * h)

            color = (255, 0, 0) if det.id in [32, 37] else (0, 255, 0)
            cv2.rectangle(frame_with_boxes, (xmin, ymin), (xmax, ymax), color, 2)

            label = f"{labels[det.id] if det.id < len(labels) else det.id}: {det.score:.2f}"
            cv2.putText(frame_with_boxes, label, (xmin, ymin-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        result_bgr = cv2.cvtColor(frame_with_boxes, cv2.COLOR_RGB2BGR)
        cv2.imwrite("debug_frame_with_detections.jpg", result_bgr)
        print("✅ 検出結果付きフレーム保存: debug_frame_with_detections.jpg")

camera.stop()
camera.cleanup()

print("\n" + "=" * 80)
print("✅ 調査完了")
print("=" * 80)
print("\n📝 調査結果のまとめ:")
print("  1. 保存された画像ファイルを確認してください")
print("  2. Class 32 または Class 37 が検出されていますか？")
print("  3. 検出スコアはどのくらいですか？")
print("  4. サッカーボール以外に何が検出されましたか？")
print("\n🔍 次のステップ:")
print("  - Class 37 (sports ball) が検出されない場合:")
print("    → COCOモデルはサッカーボールを認識できない可能性")
print("    → ファインチューニング済みYOLOモデルの使用を推奨")
print("  - 検出スコアが低い場合:")
print("    → 閾値を下げる、または照明条件を改善")
