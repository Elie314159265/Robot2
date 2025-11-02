#!/usr/bin/env python3
"""
カメラ 300x300 解像度テスト
リサイズなしでTPU推論を試す
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import detect

print("=" * 70)
print("カメラ 300x300 解像度テスト")
print("=" * 70)

# カメラを640x480で初期化（300x300は非標準解像度で画像が壊れるため）
print("\nカメラを640x480で初期化中...")
camera = CameraController(resolution=(640, 480), framerate=30, debug=True)

if not camera.initialize():
    print("❌ カメラの初期化に失敗しました")
    sys.exit(1)

if not camera.start():
    print("❌ カメラの起動に失敗しました")
    camera.cleanup()
    sys.exit(1)

time.sleep(2)
print("✅ カメラ初期化完了")

# フレーム取得テスト
print("\nフレームを取得中...")
for i in range(5):
    frame = camera.capture_frame()
    if frame is not None:
        print(f"  フレーム {i+1}: shape={frame.shape}, dtype={frame.dtype}")
    else:
        print(f"  フレーム {i+1}: None")
    time.sleep(0.1)

# TPUモデル読み込み
print("\nTPUモデル読み込み中...")
model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite"
interpreter = edgetpu.make_interpreter(model_path)
interpreter.allocate_tensors()
input_size = common.input_size(interpreter)

print(f"✅ モデル読み込み完了")
print(f"   モデル入力サイズ: {input_size}")

# フレームを640x480でキャプチャし、300x300にリサイズしてTPUに入力
print("\n640x480フレームをキャプチャして300x300にリサイズしてTPUに入力テスト...")
frame = camera.capture_frame()

if frame is not None:
    import cv2
    print(f"✅ フレームサイズ: {frame.shape}")
    print("   300x300にリサイズして推論を実行...")

    # 300x300にリサイズ
    resized = cv2.resize(frame, (300, 300), interpolation=cv2.INTER_LINEAR)

    # 推論実行
    start_time = time.time()
    common.set_input(interpreter, resized)
    interpreter.invoke()
    detections = detect.get_objects(interpreter, score_threshold=0.5)
    inference_time = (time.time() - start_time) * 1000

    print(f"✅ 推論成功！")
    print(f"   推論時間: {inference_time:.2f}ms")
    print(f"   検出数: {len(detections)}")

    if detections:
        for det in detections:
            print(f"     - Class {det.id}, Score: {det.score:.2f}")

    # 30秒間のパフォーマンステスト
    print("\n30秒間のパフォーマンステスト...")
    start_time = time.time()
    frame_count = 0
    total_inference_time = 0
    ball_detections = 0

    while time.time() - start_time < 30:
        frame = camera.capture_frame()
        if frame is None:
            continue

        # 300x300にリサイズして推論
        resized = cv2.resize(frame, (300, 300), interpolation=cv2.INTER_LINEAR)

        inf_start = time.time()
        common.set_input(interpreter, resized)
        interpreter.invoke()
        detections = detect.get_objects(interpreter, score_threshold=0.5)
        inf_time = (time.time() - inf_start) * 1000

        total_inference_time += inf_time
        frame_count += 1

        # ボール検出カウント
        for det in detections:
            if det.id == 36:
                ball_detections += 1

        # 進捗表示
        if frame_count % 150 == 0:
            elapsed = time.time() - start_time
            current_fps = frame_count / elapsed
            print(f"  {elapsed:.1f}秒 - フレーム: {frame_count}, "
                  f"FPS: {current_fps:.2f}, ボール検出: {ball_detections}")

    # 結果
    actual_duration = time.time() - start_time
    avg_fps = frame_count / actual_duration
    avg_inference = total_inference_time / frame_count

    print(f"\n📊 結果:")
    print(f"   総フレーム数: {frame_count}")
    print(f"   実行時間: {actual_duration:.1f}秒")
    print(f"   平均FPS: {avg_fps:.2f}")
    print(f"   平均推論時間: {avg_inference:.2f}ms")
    print(f"   ボール検出数: {ball_detections}")

else:
    print(f"❌ フレームサイズ不一致: {frame.shape if frame is not None else 'None'}")

# クリーンアップ
camera.stop()
camera.cleanup()

print("\n✅ テスト完了")
