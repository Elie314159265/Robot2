#!/usr/bin/env python3
"""
YOLO TPU パフォーマンスデバッグスクリプト
各処理ステップの時間を計測してボトルネックを特定
"""

import sys
import os
import time
import numpy as np
import cv2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common

def postprocess_yolo_output(output_data, input_shape, conf_threshold=0.5, iou_threshold=0.45):
    """YOLO形式の出力を後処理"""
    predictions = output_data[0].transpose()

    boxes = []
    scores = []
    class_ids = []

    h, w = input_shape

    for pred in predictions:
        x_center, y_center, width, height, confidence = pred

        if confidence < conf_threshold:
            continue

        xmin = (x_center - width / 2) / w
        ymin = (y_center - height / 2) / h
        xmax = (x_center + width / 2) / w
        ymax = (y_center + height / 2) / h

        xmin = max(0, min(1, xmin))
        ymin = max(0, min(1, ymin))
        xmax = max(0, min(1, xmax))
        ymax = max(0, min(1, ymax))

        boxes.append([xmin, ymin, xmax, ymax])
        scores.append(float(confidence))
        class_ids.append(0)

    if len(boxes) == 0:
        return []

    boxes_np = np.array(boxes)
    scores_np = np.array(scores)

    boxes_for_nms = boxes_np.copy()
    boxes_for_nms[:, [0, 2]] *= w
    boxes_for_nms[:, [1, 3]] *= h

    indices = cv2.dnn.NMSBoxes(
        boxes_for_nms.tolist(),
        scores_np.tolist(),
        conf_threshold,
        iou_threshold
    )

    detections = []
    if len(indices) > 0:
        for i in indices.flatten():
            detections.append({
                'class': class_ids[i],
                'score': scores[i],
                'bbox': boxes[i]
            })

    return detections


if __name__ == '__main__':
    print("=" * 70)
    print("🔍 YOLO TPU パフォーマンスデバッグ")
    print("=" * 70)

    # TPUモデル初期化
    model_path = "models/best_full_integer_quant_edgetpu.tflite"
    print(f"\n📦 TPUモデル読み込み: {model_path}")

    interpreter = edgetpu.make_interpreter(model_path)
    interpreter.allocate_tensors()
    print("✅ Edge TPU モデル読み込み完了")

    # カメラ初期化
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

    # 入力情報取得
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]
    input_shape = input_details['shape'][1:3]

    input_scale = input_details['quantization'][0]
    input_zero_point = input_details['quantization'][1]
    output_scale = output_details['quantization'][0]
    output_zero_point = output_details['quantization'][1]

    print(f"入力サイズ: {input_shape}")
    print(f"入力量子化: scale={input_scale}, zero_point={input_zero_point}")
    print(f"出力量子化: scale={output_scale}, zero_point={output_zero_point}\n")

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

        # 1. フレーム取得
        t1 = time.time()
        frame = camera.capture_frame()
        if frame is None:
            continue
        capture_time = (time.time() - t1) * 1000

        # 2. リサイズ
        t2 = time.time()
        resized = cv2.resize(frame, (input_shape[1], input_shape[0]))
        resize_time = (time.time() - t2) * 1000

        # 3. 量子化
        t3 = time.time()
        input_data = (resized.astype(np.float32) / input_scale + input_zero_point).astype(np.int8)
        input_data = np.expand_dims(input_data, axis=0)
        quantize_time = (time.time() - t3) * 1000

        # 4. TPU推論
        t4 = time.time()
        interpreter.set_tensor(input_details['index'], input_data)
        interpreter.invoke()
        inference_time = (time.time() - t4) * 1000

        # 5. 結果取得と逆量子化
        t5 = time.time()
        output_data = interpreter.get_tensor(output_details['index'])
        output_data = (output_data.astype(np.float32) - output_zero_point) * output_scale
        dequantize_time = (time.time() - t5) * 1000

        # 6. YOLO後処理
        t6 = time.time()
        detections = postprocess_yolo_output(
            output_data,
            input_shape=(input_shape[0], input_shape[1]),
            conf_threshold=0.5,
            iou_threshold=0.45
        )
        postprocess_time = (time.time() - t6) * 1000

        total_time = (time.time() - frame_start) * 1000

        # 記録
        total_times['capture'].append(capture_time)
        total_times['resize'].append(resize_time)
        total_times['quantize'].append(quantize_time)
        total_times['inference'].append(inference_time)
        total_times['dequantize'].append(dequantize_time)
        total_times['postprocess'].append(postprocess_time)
        total_times['total'].append(total_time)

        if (i + 1) % 20 == 0:
            print(f"  進捗: {i+1}/{num_frames} フレーム処理完了")

    # 統計計算
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
            'postprocess': '6. YOLO後処理',
            'total': '【合計】'
        }[key]

        print(f"\n{label}:")
        print(f"  平均: {avg:6.2f} ms")
        print(f"  標準偏差: {std:6.2f} ms")
        print(f"  最小: {min_t:6.2f} ms")
        print(f"  最大: {max_t:6.2f} ms")

    # FPS計算
    avg_total = np.mean(total_times['total'])
    theoretical_fps = 1000.0 / avg_total

    print("\n" + "=" * 70)
    print(f"🎯 理論上のFPS: {theoretical_fps:.1f}")
    print("=" * 70)

    # ボトルネック分析
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

    # クリーンアップ
    camera.stop()
    camera.cleanup()
    print("\n✅ テスト完了")
