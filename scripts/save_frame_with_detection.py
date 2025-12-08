#!/usr/bin/env python3
"""
フレームを保存して検出結果を確認
"""

import sys
import os
import time
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect
import numpy as np

# モデル読み込み
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
labels_path = "models/coco_labels.txt"

interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()

with open(labels_path, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# カメラ初期化
camera = CameraController(resolution=(640, 480), framerate=30, debug=False)
camera.initialize()
camera.start()
time.sleep(2)

print("3秒後にフレームをキャプチャします...")
print("サッカーボールをカメラの前に持ってきてください！")
time.sleep(3)

# フレーム取得
frame = camera.capture_frame()

# 推論
input_size = common.input_size(interpreter)
resized = np.array(np.resize(frame, (input_size[0], input_size[1], 3)), dtype=np.uint8)
common.set_input(interpreter, resized)
interpreter.invoke()
detections = detect.get_objects(interpreter, score_threshold=0.3)

# 検出結果を描画
h, w = frame.shape[:2]
for det in detections:
    bbox = det.bbox
    score = det.score
    class_id = det.id

    xmin = int(bbox.xmin * w)
    ymin = int(bbox.ymin * h)
    xmax = int(bbox.xmax * w)
    ymax = int(bbox.ymax * h)

    # ボール（class 36）は赤、その他は緑
    if class_id == 36:
        color = (255, 0, 0)  # 赤 (RGB)
        label = f"BALL {score:.2%}"
        thickness = 5
    else:
        color = (0, 255, 0)  # 緑
        label_name = labels[class_id] if class_id < len(labels) else f"ID:{class_id}"
        label = f"{label_name} {score:.2%}"
        thickness = 2

    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, thickness)
    cv2.putText(frame, label, (xmin, ymin - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

# BGR変換して保存
frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
output_path = "/tmp/detection_result.jpg"
cv2.imwrite(output_path, frame_bgr)

print(f"\n保存完了: {output_path}")
print(f"検出数: {len(detections)}")

for i, det in enumerate(detections):
    class_id = det.id
    label_name = labels[class_id] if class_id < len(labels) else f"ID:{class_id}"
    is_ball = "⚽ BALL!" if class_id == 36 else ""
    print(f"  [{i+1}] {label_name} ({det.score:.2%}) {is_ball}")

camera.cleanup()
print("\n画像をRaspberryPiから確認するか、scpでダウンロードしてください")
print(f"  scp worker1@192.168.0.11:{output_path} .")
