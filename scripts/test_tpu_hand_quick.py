#!/usr/bin/env python3
"""
TPU版ハンドコントロールの簡易テスト

Palm DetectionとHand Landmarkの動作を確認します。
"""

import sys
import os
import time
import logging
import numpy as np
import cv2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.hand_control.hand_detector_tpu import HandDetectorTPU
from src.camera import CameraController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_tpu_hand_detection():
    """TPU版手指検出のテスト"""

    print("=" * 70)
    print("🖐️  TPU版ハンドコントロール 簡易テスト")
    print("=" * 70)

    # HandDetectorTPU初期化
    logger.info("⚡ Google Coral TPU初期化中...")
    try:
        detector = HandDetectorTPU(
            model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
            palm_model_path='models/palm_detection_builtin_256_integer_quant.tflite',
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_palm_confidence=0.3  # Palm detectionの閾値を下げる
        )
        logger.info("✅ TPU初期化完了")
    except Exception as e:
        logger.error(f"❌ TPU初期化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

    # カメラ初期化
    logger.info("📷 カメラを初期化中...")
    camera = CameraController(resolution=(640, 480), framerate=15, debug=False)

    if not camera.initialize():
        logger.error("❌ カメラの初期化に失敗しました")
        return False

    if not camera.start():
        logger.error("❌ カメラの起動に失敗しました")
        camera.cleanup()
        return False

    time.sleep(2)  # カメラウォームアップ
    logger.info("✅ カメラ初期化完了")

    # テスト開始
    print("\n" + "=" * 70)
    print("🎬 テスト開始（10フレーム処理）")
    print("=" * 70)

    frame_count = 0
    max_frames = 10
    detection_times = []
    detection_success = 0

    try:
        while frame_count < max_frames:
            # フレーム取得
            frame = camera.capture_frame()
            if frame is None:
                logger.warning("⚠️  フレーム取得失敗")
                continue

            frame_count += 1

            # 手検出実行
            start_time = time.time()
            try:
                hand_data = detector.detect(frame)
                detection_time = (time.time() - start_time) * 1000
                detection_times.append(detection_time)

                # 結果を表示
                left_detected = hand_data['left_hand'] is not None
                right_detected = hand_data['right_hand'] is not None

                if left_detected or right_detected:
                    detection_success += 1

                print(f"\nFrame {frame_count}/{max_frames}:")
                print(f"  検出時間: {detection_time:.1f} ms")
                print(f"  左手: {'✅ 検出' if left_detected else '❌ 未検出'}")
                print(f"  右手: {'✅ 検出' if right_detected else '❌ 未検出'}")

                # 指の角度を表示
                if left_detected:
                    angles = hand_data['left_hand']['finger_angles']
                    print(f"    左手の指角度: {angles}")

                if right_detected:
                    angles = hand_data['right_hand']['finger_angles']
                    print(f"    右手の指角度: {angles}")

            except Exception as e:
                logger.error(f"❌ 検出処理でエラー: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(0.5)  # 0.5秒待機

    except KeyboardInterrupt:
        print("\n🛑 中断されました")

    finally:
        camera.stop()
        camera.cleanup()
        detector.cleanup()

    # 統計表示
    print("\n" + "=" * 70)
    print("📊 テスト結果")
    print("=" * 70)
    print(f"処理フレーム数: {frame_count}")
    print(f"手検出成功: {detection_success} / {frame_count}")
    print(f"成功率: {detection_success / frame_count * 100:.1f}%")

    if detection_times:
        print(f"\n検出時間統計:")
        print(f"  平均: {np.mean(detection_times):.1f} ms")
        print(f"  最小: {np.min(detection_times):.1f} ms")
        print(f"  最大: {np.max(detection_times):.1f} ms")

    print("=" * 70)

    return True


if __name__ == '__main__':
    try:
        success = test_tpu_hand_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
