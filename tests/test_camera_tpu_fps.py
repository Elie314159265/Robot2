#!/usr/bin/env python3
"""
カメラ + Edge TPU統合FPS性能測定テスト
CPU版とTPU版を比較
"""

import sys
import os
import time
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

def test_camera_setup():
    """カメラのセットアップ"""
    print("=" * 60)
    print("Setting up camera...")
    print("=" * 60)

    try:
        camera = CameraController(resolution=(640, 480), framerate=30, debug=True)

        if not camera.initialize():
            print("❌ Camera initialization failed")
            return None

        if not camera.start():
            print("❌ Camera start failed")
            camera.cleanup()
            return None

        time.sleep(2)  # カメラの安定化待ち

        print("✅ Camera initialized successfully")
        return camera
    except Exception as e:
        print(f"❌ Camera initialization failed: {e}")
        return None

def test_tpu_fps(camera, duration=10):
    """TPU版のFPS測定"""
    print("\n" + "=" * 60)
    print("Test: TPU-Accelerated Detection FPS")
    print("=" * 60)

    model_path = 'models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite'
    labels_path = 'models/coco_labels.txt'

    try:
        # TPUモデルのロード
        print(f"Loading TPU model: {model_path}")
        interpreter = edgetpu.make_interpreter(model_path)
        interpreter.allocate_tensors()

        # ラベルの読み込み
        with open(labels_path, 'r') as f:
            labels = [line.strip() for line in f.readlines()]

        print(f"Model loaded. Starting FPS test for {duration} seconds...")

        frame_count = 0
        ball_detections = 0
        inference_times = []
        start_time = time.time()

        while (time.time() - start_time) < duration:
            # フレーム取得
            frame = camera.capture_frame()
            if frame is None:
                continue

            # 推論開始
            inference_start = time.time()

            # 入力画像のリサイズと前処理
            input_size = common.input_size(interpreter)
            resized = np.array(
                np.resize(frame, (input_size[0], input_size[1], 3)),
                dtype=np.uint8
            )

            # 推論実行
            common.set_input(interpreter, resized)
            interpreter.invoke()

            # 結果取得
            objs = detect.get_objects(interpreter, score_threshold=0.6)

            inference_time = (time.time() - inference_start) * 1000
            inference_times.append(inference_time)

            # sports ball (class 37) の検出をカウント
            for obj in objs:
                if labels[obj.id] == 'sports ball':
                    ball_detections += 1
                    break

            frame_count += 1

        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        avg_inference = np.mean(inference_times)

        print(f"\n✅ TPU Test Results:")
        print(f"   Total frames:      {frame_count}")
        print(f"   Elapsed time:      {elapsed_time:.2f}s")
        print(f"   FPS:               {fps:.2f}")
        print(f"   Avg inference:     {avg_inference:.2f}ms")
        print(f"   Ball detections:   {ball_detections}")

        return {
            'fps': fps,
            'frames': frame_count,
            'inference_time': avg_inference,
            'ball_detections': ball_detections
        }
    except Exception as e:
        print(f"❌ TPU test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_cpu_fps(camera, duration=10):
    """CPU版のFPS測定（参考用）"""
    print("\n" + "=" * 60)
    print("Test: CPU-Only Detection FPS (Reference)")
    print("=" * 60)

    model_path = 'models/ssd_mobilenet_v2_coco_quant_postprocess.tflite'

    try:
        # TensorFlow Liteのインポート（CPU版）
        import tflite_runtime.interpreter as tflite

        print(f"Loading CPU model: {model_path}")
        interpreter = tflite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()

        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        print(f"Model loaded. Starting FPS test for {duration} seconds...")

        frame_count = 0
        inference_times = []
        start_time = time.time()

        while (time.time() - start_time) < duration:
            # フレーム取得
            frame = camera.capture_frame()
            if frame is None:
                continue

            # 推論開始
            inference_start = time.time()

            # 入力画像のリサイズ
            input_shape = input_details[0]['shape']
            resized = np.array(
                np.resize(frame, (input_shape[1], input_shape[2], 3)),
                dtype=np.uint8
            )
            resized = np.expand_dims(resized, axis=0)

            # 推論実行
            interpreter.set_tensor(input_details[0]['index'], resized)
            interpreter.invoke()

            inference_time = (time.time() - inference_start) * 1000
            inference_times.append(inference_time)

            frame_count += 1

        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        avg_inference = np.mean(inference_times)

        print(f"\n✅ CPU Test Results:")
        print(f"   Total frames:      {frame_count}")
        print(f"   Elapsed time:      {elapsed_time:.2f}s")
        print(f"   FPS:               {fps:.2f}")
        print(f"   Avg inference:     {avg_inference:.2f}ms")

        return {
            'fps': fps,
            'frames': frame_count,
            'inference_time': avg_inference
        }
    except Exception as e:
        print(f"❌ CPU test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print("Camera + Edge TPU FPS Performance Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print("=" * 60)

    # カメラ初期化
    camera = test_camera_setup()
    if not camera:
        print("❌ Camera setup failed. Exiting.")
        return 1

    # TPU版テスト
    tpu_results = test_tpu_fps(camera, duration=10)

    # CPU版テスト（参考用）
    cpu_results = test_cpu_fps(camera, duration=10)

    # カメラクリーンアップ
    camera.stop()
    camera.cleanup()

    # 比較結果
    print("\n" + "=" * 60)
    print("Performance Comparison")
    print("=" * 60)

    if tpu_results and cpu_results:
        print(f"\n{'Metric':<20} {'CPU':<15} {'TPU':<15} {'Improvement':<15}")
        print("-" * 65)

        fps_improvement = (tpu_results['fps'] / cpu_results['fps']) * 100
        print(f"{'FPS':<20} {cpu_results['fps']:<15.2f} {tpu_results['fps']:<15.2f} {fps_improvement:<15.1f}%")

        inference_improvement = (cpu_results['inference_time'] / tpu_results['inference_time'])
        print(f"{'Avg Inference (ms)':<20} {cpu_results['inference_time']:<15.2f} {tpu_results['inference_time']:<15.2f} {inference_improvement:<15.1f}x faster")

        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)

        # 目標達成確認
        print("\nTarget Achievement:")
        if tpu_results['fps'] >= 30:
            print("  ✅ FPS target (30 FPS): ACHIEVED")
        else:
            print(f"  ⚠️ FPS target (30 FPS): NOT MET (got {tpu_results['fps']:.1f})")

        if tpu_results['inference_time'] < 20:
            print("  ✅ Inference time target (< 20ms): ACHIEVED")
        else:
            print(f"  ⚠️ Inference time target (< 20ms): NOT MET (got {tpu_results['inference_time']:.1f}ms)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
