#!/usr/bin/env python3
"""
PIL + LANCZOSリサイズのデバッグスクリプト
実際に何が起きているか確認
"""

import sys
import os
import numpy as np
from PIL import Image
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

def resize_with_pil(image_rgb, target_size):
    """PIL + LANCZOS補間"""
    pil_image = Image.fromarray(image_rgb)
    pil_image = pil_image.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(pil_image)

print("=" * 70)
print("🔍 PIL + LANCZOS リサイズ デバッグ")
print("=" * 70)

# TPUモデル初期化
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
print(f"\n📦 TPUモデル読み込み: {model_path}")

interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()
print("✅ Edge TPU モデル読み込み完了")

# 入力サイズ確認
input_size = common.input_size(interpreter)
print(f"\n📐 入力サイズ: {input_size}")
print(f"   input_size[0] (height): {input_size[0]}")
print(f"   input_size[1] (width): {input_size[1]}")

# カメラ初期化
print("\n📷 カメラを初期化中...")
camera = CameraController(resolution=(640, 480), framerate=30, debug=False)
camera.initialize()
camera.start()

import time
time.sleep(2)
print("✅ カメラ初期化完了")

# 10フレームテスト
print("\n" + "=" * 70)
print("🧪 10フレームで検出テスト")
print("=" * 70)

for i in range(10):
    frame = camera.capture_frame()
    if frame is None:
        continue

    print(f"\n--- フレーム {i+1} ---")
    print(f"  元フレーム形状: {frame.shape}")
    print(f"  元フレーム dtype: {frame.dtype}")
    print(f"  元フレーム 値範囲: [{frame.min()}, {frame.max()}]")

    # PIL + LANCZOSでリサイズ
    resized = resize_with_pil(frame, (input_size[1], input_size[0]))

    print(f"  リサイズ後形状: {resized.shape}")
    print(f"  リサイズ後 dtype: {resized.dtype}")
    print(f"  リサイズ後 値範囲: [{resized.min()}, {resized.max()}]")

    # uint8確認
    if resized.dtype != np.uint8:
        resized = resized.astype(np.uint8)
        print(f"  uint8変換後 dtype: {resized.dtype}")

    # TPU推論
    common.set_input(interpreter, resized)
    interpreter.invoke()

    # 検出結果取得
    detections = detect.get_objects(interpreter, score_threshold=0.5)

    print(f"  検出数: {len(detections)}")
    if detections:
        for det in detections:
            print(f"    - Class {det.id}: {det.score:.2f} at {det.bbox}")

camera.stop()
camera.cleanup()

print("\n" + "=" * 70)
print("✅ テスト完了")
print("=" * 70)
