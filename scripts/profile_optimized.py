#!/usr/bin/env python3
"""
最適化版CPU手指検出のプロファイリング
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.hand_control.hand_detector import HandDetector
from src.camera import CameraController

print("=" * 70)
print("⚡ 最適化版プロファイリング")
print("=" * 70)

# 最適化版HandDetector
detector = HandDetector(
    max_num_hands=2,
    model_complexity=0,          # 軽量モデル
    min_detection_confidence=0.8,
    min_tracking_confidence=0.5
)
print("✅ HandDetector初期化（model_complexity=0）")

# カメラ（低解像度）
camera = CameraController(resolution=(320, 240), framerate=15, debug=False)
camera.initialize()
camera.start()
time.sleep(2)
print("✅ カメラ初期化（320x240 @ 15fps）")

print("\n測定中（30フレーム）...")

times = []
frame_count = 0

while frame_count < 30:
    t0 = time.time()

    frame = camera.capture_frame()
    if frame is None:
        continue

    hand_data = detector.detect(frame)

    t1 = time.time()
    times.append((t1 - t0) * 1000)
    frame_count += 1

    if frame_count % 10 == 0:
        print(f"  {frame_count}/30 完了")

camera.stop()
camera.cleanup()
detector.cleanup()

# 結果表示
avg_ms = np.mean(times)
fps = 1000.0 / avg_ms

print("\n" + "=" * 70)
print("📊 結果")
print("=" * 70)
print(f"平均処理時間: {avg_ms:.1f} ms")
print(f"推定FPS: {fps:.1f}")
print(f"最小/最大: {np.min(times):.1f} / {np.max(times):.1f} ms")
print()

if fps >= 10:
    print(f"✅ 目標達成！ ({fps:.1f} FPS >= 10 FPS)")
else:
    print(f"❌ 目標未達成 ({fps:.1f} FPS < 10 FPS)")
    print(f"   不足: {10 - fps:.1f} FPS")

print("=" * 70)
