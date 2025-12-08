#!/usr/bin/env python3
"""
リサイズ方法の比較テスト
LANCZOS vs LINEAR の検出精度を同一条件で比較
"""

import sys
import os
import time
import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

print("=" * 70)
print("リサイズ方法比較テスト")
print("=" * 70)

# TPUモデル初期化
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()
input_size = common.input_size(interpreter)

# カメラ初期化
camera = CameraController(resolution=(640, 480), framerate=30, debug=False)
camera.initialize()
camera.start()
time.sleep(2)

print(f"\nモデル入力サイズ: {input_size}")
print(f"カメラ解像度: 640x480")
print(f"\n30秒間のテストを2回実施します...")

def test_resize_method(method_name, resize_func, duration=30):
    """指定されたリサイズ方法でテスト"""
    print(f"\n{'='*70}")
    print(f"テスト: {method_name}")
    print(f"{'='*70}")

    start_time = time.time()
    frame_count = 0
    ball_detections = 0
    total_detections = 0
    inference_times = []

    while time.time() - start_time < duration:
        # フレーム取得
        frame = camera.capture_frame()
        if frame is None:
            continue

        frame_count += 1

        # リサイズ
        inference_start = time.time()
        resized = resize_func(frame, (input_size[1], input_size[0]))

        # TPU推論
        common.set_input(interpreter, resized)
        interpreter.invoke()

        # 検出結果取得
        detections = detect.get_objects(interpreter, score_threshold=0.5)

        inference_time = (time.time() - inference_start) * 1000
        inference_times.append(inference_time)

        # 統計
        total_detections += len(detections)
        for det in detections:
            if det.id == 36:  # sports ball
                ball_detections += 1

        # 進捗表示（5秒ごと）
        elapsed = time.time() - start_time
        if frame_count % 150 == 0:
            print(f"  {elapsed:.1f}秒経過 - フレーム: {frame_count}, "
                  f"ボール検出: {ball_detections}/{total_detections}")

    # 結果
    actual_duration = time.time() - start_time
    fps = frame_count / actual_duration
    avg_inference = np.mean(inference_times)
    detection_rate = (ball_detections / total_detections * 100) if total_detections > 0 else 0

    print(f"\n結果:")
    print(f"  実行時間: {actual_duration:.1f}秒")
    print(f"  総フレーム数: {frame_count}")
    print(f"  平均FPS: {fps:.2f}")
    print(f"  平均推論時間: {avg_inference:.2f}ms")
    print(f"  総検出数: {total_detections}")
    print(f"  ボール検出数: {ball_detections}")
    print(f"  ボール検出率: {detection_rate:.2f}%")

    return {
        'method': method_name,
        'fps': fps,
        'inference_time': avg_inference,
        'total_detections': total_detections,
        'ball_detections': ball_detections,
        'detection_rate': detection_rate,
        'frame_count': frame_count
    }

# リサイズ関数定義
def resize_pil_lanczos(image_rgb, target_size):
    pil_image = Image.fromarray(image_rgb)
    pil_image = pil_image.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(pil_image)

def resize_cv2_linear(image_rgb, target_size):
    return cv2.resize(image_rgb, target_size, interpolation=cv2.INTER_LINEAR)

def resize_cv2_lanczos(image_rgb, target_size):
    return cv2.resize(image_rgb, target_size, interpolation=cv2.INTER_LANCZOS4)

# テスト実施
results = []

print("\n\n🎬 カメラにサッカーボールを映してください！")
print("5秒後にテスト開始...")
time.sleep(5)

# テスト1: PIL + LANCZOS
results.append(test_resize_method("PIL + LANCZOS", resize_pil_lanczos, duration=30))

print("\n\n次のテストまで5秒待機...")
time.sleep(5)

# テスト2: cv2 + LINEAR
results.append(test_resize_method("cv2 + LINEAR", resize_cv2_linear, duration=30))

print("\n\n次のテストまで5秒待機...")
time.sleep(5)

# テスト3: cv2 + LANCZOS4
results.append(test_resize_method("cv2 + LANCZOS4", resize_cv2_lanczos, duration=30))

# 比較結果
print("\n" + "=" * 70)
print("比較結果サマリー")
print("=" * 70)

print(f"\n{'方法':<20} {'FPS':<10} {'推論時間':<12} {'検出率':<10} {'ボール検出'}")
print("-" * 70)
for r in results:
    print(f"{r['method']:<20} {r['fps']:<10.2f} {r['inference_time']:<12.2f} "
          f"{r['detection_rate']:<10.2f} {r['ball_detections']}/{r['total_detections']}")

# 推奨
print("\n📊 分析:")
best_fps = max(results, key=lambda x: x['fps'])
best_accuracy = max(results, key=lambda x: x['detection_rate'])

print(f"  最速: {best_fps['method']} ({best_fps['fps']:.2f} FPS)")
print(f"  最高精度: {best_accuracy['method']} ({best_accuracy['detection_rate']:.2f}%)")

# クリーンアップ
camera.stop()
camera.cleanup()

print("\n✅ テスト完了")
