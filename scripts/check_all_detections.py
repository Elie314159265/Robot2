#!/usr/bin/env python3
"""
すべての検出結果を表示（スコア閾値を下げる）
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

print("=" * 70)
print("全検出結果表示モード")
print("スコア閾値: 0.1（10%以上）")
print("=" * 70)
print("\nサッカーボールをカメラの前に持ってきてください")
print("5秒後にキャプチャします...\n")
time.sleep(5)

# 5フレーム取得
for frame_num in range(5):
    frame = camera.capture_frame()

    if frame is None:
        continue

    # 推論
    input_size = common.input_size(interpreter)
    resized = np.array(np.resize(frame, (input_size[0], input_size[1], 3)), dtype=np.uint8)
    common.set_input(interpreter, resized)
    interpreter.invoke()

    # スコア閾値を0.1に下げる（10%以上）
    detections = detect.get_objects(interpreter, score_threshold=0.1)

    print(f"\n{'='*70}")
    print(f"Frame {frame_num + 1}")
    print(f"{'='*70}")
    print(f"検出数: {len(detections)}")

    if len(detections) > 0:
        # スコアでソート（高い順）
        sorted_detections = sorted(detections, key=lambda x: x.score, reverse=True)

        for i, det in enumerate(sorted_detections):
            class_id = det.id
            score = det.score
            bbox = det.bbox
            label_name = labels[class_id] if class_id < len(labels) else f"ID:{class_id}"

            is_ball = "⚽ ← これがボール！" if class_id == 36 else ""

            # バウンディングボックスのサイズ
            box_width = bbox.xmax - bbox.xmin
            box_height = bbox.ymax - bbox.ymin
            box_area = box_width * box_height

            print(f"  [{i+1:2d}] {label_name:20s} {score:6.2%}  "
                  f"BBox:[{bbox.xmin:5.1f},{bbox.ymin:5.1f},{bbox.xmax:5.1f},{bbox.ymax:5.1f}]  "
                  f"Size:{box_width*640:.0f}x{box_height*480:.0f}px ({box_area*100:.1f}%)  "
                  f"{is_ball}")
    else:
        print("  検出なし")

    time.sleep(1)

camera.cleanup()

print("\n" + "=" * 70)
print("完了")
print("=" * 70)
print("\n💡 解説:")
print("  - ボールが検出されていない場合:")
print("    1. ボールが小さすぎる（画面の5%以上推奨）")
print("    2. ボールがカメラに写っていない")
print("    3. 照明が不十分")
print("    4. COCOモデルが認識できない種類のボール")
print("\n  - ボールが検出されている場合:")
print("    ⚽マークが付いているエントリーを確認してください")
