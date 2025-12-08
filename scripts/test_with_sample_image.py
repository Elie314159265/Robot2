#!/usr/bin/env python3
"""
サンプル画像でボール検出をテスト
モデルが正常に動作しているか確認
"""

import sys
import os
import numpy as np
import cv2

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

print("=" * 70)
print("サンプル画像でボール検出テスト")
print("=" * 70)

# テスト用の画像URL（サッカーボールの画像）
import urllib.request

test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Soccerball.svg/400px-Soccerball.svg.png"

print(f"\nサンプル画像ダウンロード中...")
print(f"URL: {test_image_url}")

try:
    urllib.request.urlretrieve(test_image_url, "/tmp/test_ball.png")
    print("✅ ダウンロード完了")
except Exception as e:
    print(f"❌ ダウンロード失敗: {e}")
    print("代わりに既存の画像を使います")

# 画像読み込み
img = cv2.imread("/tmp/test_ball.png")
if img is None:
    print("❌ 画像読み込み失敗")
    sys.exit(1)

# BGRからRGBに変換
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
print(f"画像サイズ: {img_rgb.shape}")

# リサイズして推論
input_size = common.input_size(interpreter)
resized = cv2.resize(img_rgb, (input_size[0], input_size[1]))
resized = np.array(resized, dtype=np.uint8)

# 推論
common.set_input(interpreter, resized)
interpreter.invoke()

# 検出結果
detections = detect.get_objects(interpreter, score_threshold=0.3)

print(f"\n検出数: {len(detections)}")
print("\n検出結果:")

if len(detections) > 0:
    for i, det in enumerate(detections):
        class_id = det.id
        score = det.score
        label_name = labels[class_id] if class_id < len(labels) else f"ID:{class_id}"
        is_ball = "⚽ ← これがボール！" if class_id == 36 else ""

        print(f"  [{i+1}] {label_name} ({score:.2%}) {is_ball}")
        print(f"      BBox: [{det.bbox.xmin:.3f}, {det.bbox.ymin:.3f}, {det.bbox.xmax:.3f}, {det.bbox.ymax:.3f}]")
else:
    print("  検出なし")

print("\n" + "=" * 70)
print("結論:")
if any(det.id == 36 for det in detections):
    print("✅ モデルは正常に動作しています！")
    print("   サンプル画像でボールを検出できました。")
    print("   実際のカメラ映像の問題（照明、距離、ボールの種類など）を確認してください。")
else:
    print("⚠️  サンプル画像でもボールが検出されませんでした")
    print("   ボール検出の閾値や条件を調整する必要があります")
print("=" * 70)
