#!/usr/bin/env python3
"""
TPU検出デバッグスクリプト
何が検出されているかを詳細に表示
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect
import numpy as np

print("=" * 70)
print("TPU検出デバッグモード")
print("=" * 70)

# モデル読み込み
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
labels_path = "models/coco_labels.txt"

print(f"\n📦 モデル読み込み: {model_path}")
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()
print("✅ TPUモデル読み込み完了")

# ラベル読み込み
print(f"\n📝 ラベル読み込み: {labels_path}")
with open(labels_path, 'r') as f:
    labels = [line.strip() for line in f.readlines()]
print(f"✅ {len(labels)} ラベル読み込み完了")
print(f"   Class 36 (sports ball): {labels[36]}")
print(f"   Class 37 (kite): {labels[37]}")

# カメラ初期化
print("\n📷 カメラ初期化...")
camera = CameraController(resolution=(640, 480), framerate=30, debug=False)

if not camera.initialize():
    print("❌ カメラ初期化失敗")
    sys.exit(1)

if not camera.start():
    print("❌ カメラ起動失敗")
    camera.cleanup()
    sys.exit(1)

print("✅ カメラ起動完了")
time.sleep(2)

print("\n" + "=" * 70)
print("検出開始（10フレーム分）")
print("スコア閾値: 0.3（30%以上の確信度）")
print("=" * 70)

try:
    for frame_num in range(10):
        # フレーム取得
        frame = camera.capture_frame()
        if frame is None:
            print(f"Frame {frame_num + 1}: キャプチャ失敗")
            continue

        # リサイズと推論
        input_size = common.input_size(interpreter)
        resized = np.array(
            np.resize(frame, (input_size[0], input_size[1], 3)),
            dtype=np.uint8
        )

        # TPU推論
        inference_start = time.time()
        common.set_input(interpreter, resized)
        interpreter.invoke()
        inference_time = (time.time() - inference_start) * 1000

        # 検出結果取得（スコア閾値0.3に下げる）
        detections = detect.get_objects(interpreter, score_threshold=0.3)

        print(f"\nFrame {frame_num + 1}:")
        print(f"  推論時間: {inference_time:.2f} ms")
        print(f"  検出数: {len(detections)}")

        if len(detections) > 0:
            for i, det in enumerate(detections):
                class_id = det.id
                score = det.score
                bbox = det.bbox
                label = labels[class_id] if class_id < len(labels) else f"Unknown({class_id})"

                is_ball = (class_id == 36)  # COCO class 36 = sports ball
                marker = "⚽" if is_ball else "  "

                print(f"    {marker} [{i+1}] {label} ({score:.2%}) - BBox: [{bbox.xmin:.3f}, {bbox.ymin:.3f}, {bbox.xmax:.3f}, {bbox.ymax:.3f}]")
        else:
            print("    検出なし")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n\n中断されました")

finally:
    camera.cleanup()
    print("\n✅ カメラ停止")

print("\n" + "=" * 70)
print("デバッグ終了")
print("=" * 70)
