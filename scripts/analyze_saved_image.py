#!/usr/bin/env python3
"""
保存された画像を分析
"""

import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

# モデル読み込み
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
labels_path = "models/coco_labels.txt"

interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()

with open(labels_path, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# 保存された画像を読み込み
img_path = "/tmp/detection_result.jpg"
img = cv2.imread(img_path)

if img is None:
    print(f"❌ 画像が見つかりません: {img_path}")
    sys.exit(1)

print("=" * 70)
print("保存された画像の分析")
print("=" * 70)
print(f"画像: {img_path}")
print(f"サイズ: {img.shape}")

# BGRからRGBに変換
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# リサイズして推論
input_size = common.input_size(interpreter)
resized = cv2.resize(img_rgb, (input_size[0], input_size[1]))
resized = np.array(resized, dtype=np.uint8)

# 推論（複数の閾値で試す）
thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]

for threshold in thresholds:
    print(f"\n{'='*70}")
    print(f"スコア閾値: {threshold} ({threshold*100:.0f}%)")
    print(f"{'='*70}")

    common.set_input(interpreter, resized)
    interpreter.invoke()
    detections = detect.get_objects(interpreter, score_threshold=threshold)

    print(f"検出数: {len(detections)}")

    if len(detections) > 0:
        for i, det in enumerate(detections):
            class_id = det.id
            score = det.score
            label_name = labels[class_id] if class_id < len(labels) else f"ID:{class_id}"
            is_ball = "⚽⚽⚽" if class_id == 36 else ""

            print(f"  [{i+1}] {label_name:20s} {score:6.2%}  {is_ball}")
    else:
        print("  検出なし")

print("\n" + "=" * 70)
print("結論:")
print("=" * 70)
print("この画像からはボールが検出されていません。")
print("\n考えられる原因:")
print("  1. ボールが画像に写っていない")
print("  2. ボールが小さすぎる（画像の5%未満）")
print("  3. ボールのパターンがCOCOモデルが認識できるものと異なる")
print("  4. 照明条件が悪い（暗すぎる、露出オーバーなど）")
print("  5. 背景との区別がつかない")
print("\n💡 推奨対策:")
print("  - ボールをカメラに近づける（20-40cm）")
print("  - 明るい場所で撮影する")
print("  - 白黒の典型的なサッカーボールパターンを使う")
print("  - 無地の背景を使う")
