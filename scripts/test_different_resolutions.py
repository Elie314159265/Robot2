#!/usr/bin/env python3
"""
異なる解像度・FPSでボール検出をテスト
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera.camera_controller_libcamera_cli import CameraControllerLibcameraCLI
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect
import numpy as np
import cv2

# モデル読み込み
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
labels_path = "models/coco_labels.txt"

print("モデル読み込み中...")
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()

with open(labels_path, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# テストする設定
test_configs = [
    # (width, height, fps, description)
    (320, 240, 30, "低解像度・標準FPS"),
    (640, 480, 30, "標準解像度・標準FPS"),
    (640, 480, 15, "標準解像度・低FPS"),
    (800, 600, 20, "高解像度・中FPS"),
    (1280, 720, 15, "HD解像度・低FPS"),
]

print("\n" + "=" * 70)
print("異なる解像度・FPSでボール検出テスト")
print("=" * 70)
print("\nサッカーボールをカメラの前（30-50cm）に持ってきてください")
print("各設定で5秒間テストします\n")

for width, height, fps, desc in test_configs:
    print("\n" + "=" * 70)
    print(f"設定: {desc}")
    print(f"解像度: {width}x{height}, FPS: {fps}")
    print("=" * 70)

    # カメラ初期化
    camera = CameraControllerLibcameraCLI(
        resolution=(width, height),
        framerate=fps,
        debug=False
    )

    if not camera.initialize():
        print("❌ カメラ初期化失敗")
        continue

    if not camera.start():
        print("❌ カメラ起動失敗")
        camera.cleanup()
        continue

    print("✅ カメラ起動成功")
    time.sleep(2)  # カメラ安定化待ち

    # 5フレームテスト
    ball_detected_count = 0
    total_detections_list = []
    inference_times = []

    for i in range(5):
        frame = camera.capture_frame()
        if frame is None:
            continue

        # TPU推論
        input_size = common.input_size(interpreter)
        resized = np.array(np.resize(frame, (input_size[0], input_size[1], 3)), dtype=np.uint8)

        inference_start = time.time()
        common.set_input(interpreter, resized)
        interpreter.invoke()
        inference_time = (time.time() - inference_start) * 1000
        inference_times.append(inference_time)

        # 検出（スコア閾値0.3）
        detections = detect.get_objects(interpreter, score_threshold=0.3)
        total_detections_list.append(len(detections))

        # ボール検出確認
        ball_found = False
        for det in detections:
            if det.id == 36:  # sports ball
                ball_found = True
                ball_detected_count += 1
                print(f"  Frame {i+1}: ⚽ BALL検出！ スコア={det.score:.2%}, "
                      f"BBox=[{det.bbox.xmin:.2f},{det.bbox.ymin:.2f},{det.bbox.xmax:.2f},{det.bbox.ymax:.2f}]")

                # 最初の検出時に画像保存
                if ball_detected_count == 1:
                    # 描画
                    h, w = frame.shape[:2]
                    xmin = int(det.bbox.xmin * w)
                    ymin = int(det.bbox.ymin * h)
                    xmax = int(det.bbox.xmax * w)
                    ymax = int(det.bbox.ymax * h)

                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (255, 0, 0), 5)
                    cv2.putText(frame, f"BALL {det.score:.2%}", (xmin, ymin - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)

                    # 保存
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    output_path = f"/tmp/ball_detected_{width}x{height}_{fps}fps.jpg"
                    cv2.imwrite(output_path, frame_bgr)
                    print(f"    💾 画像保存: {output_path}")
                break

        if not ball_found:
            other_objects = [labels[det.id] for det in detections]
            if other_objects:
                print(f"  Frame {i+1}: 検出={len(detections)} [{', '.join(other_objects[:3])}...]")
            else:
                print(f"  Frame {i+1}: 検出なし")

        time.sleep(0.5)

    # 結果サマリー
    avg_inference = sum(inference_times) / len(inference_times) if inference_times else 0
    avg_detections = sum(total_detections_list) / len(total_detections_list) if total_detections_list else 0

    print(f"\n📊 結果:")
    print(f"  ボール検出回数: {ball_detected_count}/5 フレーム")
    print(f"  平均推論時間: {avg_inference:.1f} ms")
    print(f"  平均検出数: {avg_detections:.1f} オブジェクト")

    if ball_detected_count > 0:
        print(f"  ✅ この設定でボール検出成功！")
    else:
        print(f"  ❌ この設定ではボール未検出")

    # カメラクリーンアップ
    camera.cleanup()
    time.sleep(1)

print("\n" + "=" * 70)
print("テスト完了")
print("=" * 70)
print("\n📋 推奨設定:")
print("  ボール検出に最も成功した設定を使用してください")
print("  保存された画像は /tmp/ball_detected_*.jpg で確認できます")
