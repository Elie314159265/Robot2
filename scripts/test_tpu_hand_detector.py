#!/usr/bin/env python3
"""
HandDetectorTPU クイックテスト

Google Coral TPUとhand_landmarkモデルの初期化と基本動作を確認します。
"""

import sys
import os
import cv2
import numpy as np
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.hand_control import HandDetectorTPU

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    print("=" * 70)
    print("🖐️  HandDetectorTPU クイックテスト")
    print("=" * 70)

    # HandDetectorTPU初期化
    logger.info("⚡ Google Coral TPU初期化中...")
    try:
        detector = HandDetectorTPU(
            model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
            palm_model_path='models/palm_detection_builtin_256_integer_quant.tflite',
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_palm_confidence=0.5
        )
        logger.info("✅ TPU初期化完了")
    except Exception as e:
        logger.error(f"❌ TPU初期化失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ダミー画像でテスト
    logger.info("📷 ダミー画像で推論テスト中...")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    try:
        result = detector.detect(dummy_frame)
        logger.info(f"✅ 推論成功: left_hand={result['left_hand'] is not None}, "
                   f"right_hand={result['right_hand'] is not None}")
    except Exception as e:
        logger.error(f"❌ 推論失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # クリーンアップ
    detector.cleanup()
    logger.info("✅ クリーンアップ完了")

    print("=" * 70)
    print("✅ HandDetectorTPU クイックテスト成功！")
    print("=" * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
