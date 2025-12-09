#!/usr/bin/env python3
"""
CPU版ハンドコントロールのプロファイリング

各処理ステップの時間を計測してボトルネックを特定します。
"""

import sys
import os
import time
import logging
import numpy as np
import cv2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.hand_control.hand_detector import HandDetector
from src.camera import CameraController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def profile_hand_detection():
    """CPU版手指検出のプロファイリング"""

    print("=" * 70)
    print("🔍 CPU版ハンドコントロール プロファイリング")
    print("=" * 70)

    # HandDetector初期化
    logger.info("📋 HandDetector初期化中...")
    detector = HandDetector(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    logger.info("✅ HandDetector初期化完了")

    # カメラ初期化
    logger.info("📷 カメラを初期化中...")
    camera = CameraController(resolution=(640, 480), framerate=30, debug=False)

    if not camera.initialize():
        logger.error("❌ カメラの初期化に失敗しました")
        return False

    if not camera.start():
        logger.error("❌ カメラの起動に失敗しました")
        camera.cleanup()
        return False

    time.sleep(2)  # カメラウォームアップ
    logger.info("✅ カメラ初期化完了")

    # プロファイリング開始
    print("\n" + "=" * 70)
    print("📊 プロファイリング開始（30フレーム測定）")
    print("=" * 70)

    frame_count = 0
    max_frames = 30

    # 時間計測用
    times = {
        'capture': [],
        'detect': [],
        'draw': [],
        'total': []
    }

    try:
        while frame_count < max_frames:
            t_start = time.time()

            # フレーム取得
            t0 = time.time()
            frame = camera.capture_frame()
            if frame is None:
                continue
            t1 = time.time()
            times['capture'].append((t1 - t0) * 1000)

            frame_count += 1

            # 手検出実行
            t2 = time.time()
            hand_data = detector.detect(frame)
            t3 = time.time()
            times['detect'].append((t3 - t2) * 1000)

            # 描画
            t4 = time.time()
            annotated = detector.draw_landmarks(frame)
            t5 = time.time()
            times['draw'].append((t5 - t4) * 1000)

            t_end = time.time()
            times['total'].append((t_end - t_start) * 1000)

            # 進捗表示
            if frame_count % 10 == 0:
                print(f"  処理中... {frame_count}/{max_frames} フレーム")

    except KeyboardInterrupt:
        print("\n🛑 中断されました")

    finally:
        camera.stop()
        camera.cleanup()
        detector.cleanup()

    # 統計表示
    print("\n" + "=" * 70)
    print("📊 プロファイリング結果")
    print("=" * 70)
    print(f"測定フレーム数: {frame_count}")
    print()

    # 各処理ステップの統計
    for step, values in times.items():
        if values:
            avg = np.mean(values)
            min_val = np.min(values)
            max_val = np.max(values)
            std = np.std(values)

            print(f"{step.upper():12s}: 平均 {avg:6.1f} ms  (最小 {min_val:6.1f} ms, 最大 {max_val:6.1f} ms, 標準偏差 {std:5.1f} ms)")

    # FPS計算
    if times['total']:
        avg_total = np.mean(times['total'])
        fps = 1000.0 / avg_total
        print()
        print(f"推定FPS: {fps:.1f}")
        print(f"目標10FPSまで: {10 - fps:.1f} FPS不足" if fps < 10 else f"目標達成！ (+{fps - 10:.1f} FPS)")

    # ボトルネック分析
    print()
    print("=" * 70)
    print("🔍 ボトルネック分析")
    print("=" * 70)

    if times['detect']:
        detect_avg = np.mean(times['detect'])
        total_avg = np.mean(times['total'])
        detect_ratio = (detect_avg / total_avg) * 100

        print(f"検出処理が全体の {detect_ratio:.1f}% を占めています")

        if detect_ratio > 70:
            print("\n💡 最適化の提案:")
            print("  1. 解像度を下げる (640x480 → 320x240)")
            print("  2. max_num_handsを1に減らす")
            print("  3. min_detection_confidenceを上げる (0.7 → 0.8)")
            print("  4. static_image_mode=Falseの確認（追跡モード）")

    print("=" * 70)

    return True


if __name__ == '__main__':
    try:
        success = profile_hand_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
