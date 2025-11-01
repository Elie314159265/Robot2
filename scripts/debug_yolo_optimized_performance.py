#!/usr/bin/env python3
"""
最適化版YOLO TPU パフォーマンスデバッグスクリプト
"""

import sys
import os
import time
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu

def postprocess_yolo_output_optimized(output_data, input_shape, conf_threshold=0.5, iou_threshold=0.45):
    """最適化版YOLO後処理（NumPy vectorization）"""
    predictions = output_data[0].transpose()
    h, w = input_shape

    # ベクトル化: 信頼度フィルタリング
    confidences = predictions[:, 4]
    mask = confidences >= conf_threshold

    if not mask.any():
        return []

    filtered_preds = predictions[mask]

    # ベクトル化: バウンディングボックス変換
    x_centers = filtered_preds[:, 0]
    y_centers = filtered_preds[:, 1]
    widths = filtered_preds[:, 2]
    heights = filtered_preds[:, 3]
    scores = filtered_preds[:, 4]

    # 正規化座標に変換
    xmins = np.clip((x_centers - widths / 2) / w, 0, 1)
    ymins = np.clip((y_centers - heights / 2) / h, 0, 1)
    xmaxs = np.clip((x_centers + widths / 2) / w, 0, 1)
    ymaxs = np.clip((y_centers + heights / 2) / h, 0, 1)

    # NMS用に実座標に変換
    boxes_for_nms = np.stack([xmins * w, ymins * h, xmaxs * w, ymaxs * h], axis=1)

    # NMS
    indices = cv2.dnn.NMSBoxes(
        boxes_for_nms.tolist(),
        scores.tolist(),
        conf_threshold,
        iou_threshold
    )

    detections = []
    if len(indices) > 0:
        for i in indices.flatten():
            detections.append({
                'class': 0,
                'score': float(scores[i]),
                'bbox': [float(xmins[i]), float(ymins[i]), float(xmaxs[i]), float(ymaxs[i])]
            })

    return detections


if __name__ == '__main__':
    print("=" * 70)
    print("🚀 最適化版YOLO TPU パフォーマンステスト")
    print("=" * 70)

    model_path = "models/best_full_integer_quant_edgetpu.tflite"
    print(f"\n📦 TPUモデル読み込み: {model_path}")

    interpreter = edgetpu.make_interpreter(model_path)
    interpreter.allocate_tensors()
    print("✅ Edge TPU モデル読み込み完了")

    print("\n📷 カメラを初期化中...")
    camera = CameraController(resolution=(640, 480), framerate=30, debug=False)

    if not camera.initialize():
        print("❌ カメラの初期化に失敗")
        sys.exit(1)

    if not camera.start():
        print("❌ カメラの起動に失敗")
        camera.cleanup()
        sys.exit(1)

    time.sleep(2)
    print("✅ カメラ初期化完了\n")

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]
    input_shape = input_details['shape'][1:3]

    input_scale = input_details['quantization'][0]
    input_zero_point = input_details['quantization'][1]
    output_scale = output_details['quantization'][0]
    output_zero_point = output_details['quantization'][1]

    print(f"入力サイズ: {input_shape}\n")

    print("=" * 70)
    print("⏱️  100フレームの処理時間を計測中...")
    print("=" * 70)

    total_times = {
        'capture': [],
        'resize': [],
        'quantize': [],
        'inference': [],
        'dequantize': [],
        'postprocess': [],
        'total': []
    }

    num_frames = 100

    for i in range(num_frames):
        frame_start = time.time()

        t1 = time.time()
        frame = camera.capture_frame()
        if frame is None:
            continue
        capture_time = (time.time() - t1) * 1000

        t2 = time.time()
        resized = cv2.resize(frame, (input_shape[1], input_shape[0]))
        resize_time = (time.time() - t2) * 1000

        t3 = time.time()
        input_data = (resized.astype(np.float32) / input_scale + input_zero_point).astype(np.int8)
        input_data = np.expand_dims(input_data, axis=0)
        quantize_time = (time.time() - t3) * 1000

        t4 = time.time()
        interpreter.set_tensor(input_details['index'], input_data)
        interpreter.invoke()
        inference_time = (time.time() - t4) * 1000

        t5 = time.time()
        output_data = interpreter.get_tensor(output_details['index'])
        output_data = (output_data.astype(np.float32) - output_zero_point) * output_scale
        dequantize_time = (time.time() - t5) * 1000

        t6 = time.time()
        detections = postprocess_yolo_output_optimized(
            output_data,
            input_shape=(input_shape[0], input_shape[1]),
            conf_threshold=0.5,
            iou_threshold=0.45
        )
        postprocess_time = (time.time() - t6) * 1000

        total_time = (time.time() - frame_start) * 1000

        total_times['capture'].append(capture_time)
        total_times['resize'].append(resize_time)
        total_times['quantize'].append(quantize_time)
        total_times['inference'].append(inference_time)
        total_times['dequantize'].append(dequantize_time)
        total_times['postprocess'].append(postprocess_time)
        total_times['total'].append(total_time)

        if (i + 1) % 20 == 0:
            print(f"  進捗: {i+1}/{num_frames} フレーム処理完了")

    print("\n" + "=" * 70)
    print("📊 パフォーマンス統計（単位: ms）")
    print("=" * 70)

    for key, times in total_times.items():
        avg = np.mean(times)
        std = np.std(times)
        min_t = np.min(times)
        max_t = np.max(times)

        label = {
            'capture': '1. フレーム取得',
            'resize': '2. リサイズ',
            'quantize': '3. 量子化',
            'inference': '4. TPU推論',
            'dequantize': '5. 逆量子化',
            'postprocess': '6. YOLO後処理(最適化)',
            'total': '【合計】'
        }[key]

        print(f"\n{label}:")
        print(f"  平均: {avg:6.2f} ms")
        print(f"  標準偏差: {std:6.2f} ms")
        print(f"  最小: {min_t:6.2f} ms")
        print(f"  最大: {max_t:6.2f} ms")

    avg_total = np.mean(total_times['total'])
    theoretical_fps = 1000.0 / avg_total

    print("\n" + "=" * 70)
    print(f"🎯 理論上のFPS: {theoretical_fps:.1f}")
    print("=" * 70)

    print("\n📈 処理時間の内訳:")
    total_avg = np.mean(total_times['total'])
    for key in ['capture', 'resize', 'quantize', 'inference', 'dequantize', 'postprocess']:
        avg = np.mean(total_times[key])
        percentage = (avg / total_avg) * 100
        label = {
            'capture': 'フレーム取得',
            'resize': 'リサイズ',
            'quantize': '量子化',
            'inference': 'TPU推論',
            'dequantize': '逆量子化',
            'postprocess': 'YOLO後処理'
        }[key]
        print(f"  {label:15s}: {avg:6.2f} ms ({percentage:5.1f}%)")

    print("\n" + "=" * 70)
    print("🔥 最適化結果の比較:")
    print(f"  元の後処理時間: 104.60 ms")
    print(f"  最適化後処理時間: {np.mean(total_times['postprocess']):.2f} ms")
    improvement = ((104.60 - np.mean(total_times['postprocess'])) / 104.60) * 100
    print(f"  改善率: {improvement:.1f}%")
    print("=" * 70)

    camera.stop()
    camera.cleanup()
    print("\n✅ テスト完了")
