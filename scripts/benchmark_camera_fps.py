#!/usr/bin/env python3
"""
カメラ + 推論のFPSベンチマーク
CPU版とTPU版を比較
"""

import sys
import os
import time
import numpy as np

# Add libcamera path for RaspberryPi
sys.path.insert(0, '/usr/lib/aarch64-linux-gnu/python3.12/site-packages')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController

print("=" * 70)
print("カメラ + 推論 FPS ベンチマーク")
print("=" * 70)
print(f"Python version: {sys.version}")
print("=" * 70)

# カメラ初期化
print("\n[1/4] カメラを初期化中...")
camera = CameraController(resolution=(640, 480), framerate=30, debug=True)

if not camera.initialize():
    print("❌ カメラの初期化に失敗しました")
    sys.exit(1)

if not camera.start():
    print("❌ カメラの起動に失敗しました")
    camera.cleanup()
    sys.exit(1)

print("✅ カメラ初期化完了")
time.sleep(2)  # カメラのウォームアップ

# CPU版テスト
print("\n[2/4] CPU版推論テスト開始...")
print("-" * 70)

try:
    try:
        import tensorflow as tf
        interpreter_module = tf.lite
    except ImportError:
        import tflite_runtime.interpreter as tflite
        interpreter_module = tflite

    model_path = 'models/ssd_mobilenet_v2_coco_quant_postprocess.tflite'
    print(f"モデル: {model_path}")

    interpreter = interpreter_module.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    input_shape = input_details[0]['shape']

    print(f"入力サイズ: {input_shape}")
    print("測定中（10秒）...")

    frame_count = 0
    inference_times = []
    start_time = time.time()

    while (time.time() - start_time) < 10:
        frame = camera.capture_frame()
        if frame is None:
            continue

        inference_start = time.time()

        # リサイズと推論
        resized = np.array(
            np.resize(frame, (input_shape[1], input_shape[2], 3)),
            dtype=np.uint8
        )
        resized = np.expand_dims(resized, axis=0)

        interpreter.set_tensor(input_details[0]['index'], resized)
        interpreter.invoke()

        inference_time = (time.time() - inference_start) * 1000
        inference_times.append(inference_time)

        frame_count += 1

    elapsed = time.time() - start_time
    cpu_fps = frame_count / elapsed
    cpu_inference = np.mean(inference_times)

    print(f"\n✅ CPU版結果:")
    print(f"   フレーム数:     {frame_count}")
    print(f"   経過時間:       {elapsed:.2f}秒")
    print(f"   FPS:            {cpu_fps:.2f}")
    print(f"   平均推論時間:   {cpu_inference:.2f}ms")

except Exception as e:
    print(f"❌ CPU版テスト失敗: {e}")
    cpu_fps = 0
    cpu_inference = 0

# TPU版テスト
print("\n[3/4] TPU版推論テスト開始...")
print("-" * 70)

try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    from pycoral.adapters import detect

    model_path = 'models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'
    print(f"モデル: {model_path}")

    interpreter = edgetpu.make_interpreter(model_path)
    interpreter.allocate_tensors()

    input_size = common.input_size(interpreter)

    print(f"入力サイズ: {input_size}")
    print("測定中（10秒）...")

    frame_count = 0
    inference_times = []
    start_time = time.time()

    while (time.time() - start_time) < 10:
        frame = camera.capture_frame()
        if frame is None:
            continue

        inference_start = time.time()

        # リサイズと推論
        resized = np.array(
            np.resize(frame, (input_size[0], input_size[1], 3)),
            dtype=np.uint8
        )

        common.set_input(interpreter, resized)
        interpreter.invoke()

        inference_time = (time.time() - inference_start) * 1000
        inference_times.append(inference_time)

        frame_count += 1

    elapsed = time.time() - start_time
    tpu_fps = frame_count / elapsed
    tpu_inference = np.mean(inference_times)

    print(f"\n✅ TPU版結果:")
    print(f"   フレーム数:     {frame_count}")
    print(f"   経過時間:       {elapsed:.2f}秒")
    print(f"   FPS:            {tpu_fps:.2f}")
    print(f"   平均推論時間:   {tpu_inference:.2f}ms")

except Exception as e:
    print(f"❌ TPU版テスト失敗: {e}")
    import traceback
    traceback.print_exc()
    tpu_fps = 0
    tpu_inference = 0

# クリーンアップ
camera.stop()
camera.cleanup()

# 比較結果
print("\n[4/4] パフォーマンス比較")
print("=" * 70)

if cpu_fps > 0 and tpu_fps > 0:
    print(f"\n{'指標':<20} {'CPU版':<15} {'TPU版':<15} {'改善率':<15}")
    print("-" * 70)

    fps_improvement = (tpu_fps / cpu_fps) * 100
    print(f"{'FPS':<20} {cpu_fps:<15.2f} {tpu_fps:<15.2f} {fps_improvement:<15.1f}%")

    inference_speedup = cpu_inference / tpu_inference
    print(f"{'平均推論時間 (ms)':<20} {cpu_inference:<15.2f} {tpu_inference:<15.2f} {inference_speedup:<15.1f}x高速")

    print("\n" + "=" * 70)
    print("目標達成状況:")
    print("=" * 70)

    if tpu_fps >= 30:
        print(f"  ✅ FPS目標 (30 FPS): 達成 ({tpu_fps:.1f} FPS)")
    else:
        print(f"  ⚠️ FPS目標 (30 FPS): 未達成 ({tpu_fps:.1f} FPS)")

    if tpu_inference < 20:
        print(f"  ✅ 推論時間目標 (< 20ms): 達成 ({tpu_inference:.1f} ms)")
    else:
        print(f"  ⚠️ 推論時間目標 (< 20ms): 未達成 ({tpu_inference:.1f} ms)")

    print("=" * 70)
else:
    print("⚠️ 比較結果を表示できません")

print("\n✅ ベンチマーク完了")
