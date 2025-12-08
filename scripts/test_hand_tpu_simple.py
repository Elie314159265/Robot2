#!/usr/bin/env python3
"""
手指検出TPU版の簡易テスト

Google Coral TPUとhand_landmark_newモデルの動作を確認するシンプルなスクリプト。
カメラなしでサンプル画像を使ってテストすることも可能です。
"""

import sys
import os
import cv2
import numpy as np
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.hand_control.hand_detector_tpu import HandDetectorTPU


def test_with_blank_image():
    """白紙画像でTPUモデルのロード・推論をテスト"""
    print("=" * 70)
    print("🧪 TPU Hand Detector - 白紙画像テスト")
    print("=" * 70)

    # HandDetectorTPU初期化
    print("\n⚡ Google Coral TPU初期化中...")
    try:
        detector = HandDetectorTPU(
            model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
            max_num_hands=1,
            min_detection_confidence=0.5
        )
        print("✅ TPU初期化完了")
    except Exception as e:
        print(f"❌ TPU初期化失敗: {e}")
        return False

    # 白紙画像を作成（RGB）
    print("\n📋 白紙画像（640x480）を作成...")
    blank_image = np.ones((480, 640, 3), dtype=np.uint8) * 255

    # 検出実行
    print("🔍 手検出を実行中...")
    start_time = time.time()
    result = detector.detect(blank_image)
    detection_time = (time.time() - start_time) * 1000

    print(f"⏱️  検出時間: {detection_time:.2f}ms")
    print(f"📊 検出結果:")
    print(f"  - 左手: {result['left_hand'] is not None}")
    print(f"  - 右手: {result['right_hand'] is not None}")

    if result['left_hand']:
        print(f"  - 左手のランドマーク数: {len(result['left_hand']['landmarks'])}")
        print(f"  - 左手の指角度: {result['left_hand']['finger_angles']}")
    if result['right_hand']:
        print(f"  - 右手のランドマーク数: {len(result['right_hand']['landmarks'])}")
        print(f"  - 右手の指角度: {result['right_hand']['finger_angles']}")

    # クリーンアップ
    detector.cleanup()
    print("\n✅ テスト完了")
    return True


def test_with_sample_image(image_path: str):
    """サンプル画像でテスト"""
    print("=" * 70)
    print(f"🧪 TPU Hand Detector - サンプル画像テスト")
    print("=" * 70)
    print(f"📸 画像: {image_path}")

    # 画像を読み込み
    if not os.path.exists(image_path):
        print(f"❌ 画像が見つかりません: {image_path}")
        return False

    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 画像の読み込みに失敗しました")
        return False

    # BGRからRGBに変換
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    print(f"✅ 画像読み込み完了: shape={image_rgb.shape}")

    # HandDetectorTPU初期化
    print("\n⚡ Google Coral TPU初期化中...")
    try:
        detector = HandDetectorTPU(
            model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
            max_num_hands=1,
            min_detection_confidence=0.5
        )
        print("✅ TPU初期化完了")
    except Exception as e:
        print(f"❌ TPU初期化失敗: {e}")
        return False

    # 検出実行
    print("\n🔍 手検出を実行中...")
    start_time = time.time()
    result = detector.detect(image_rgb)
    detection_time = (time.time() - start_time) * 1000

    print(f"⏱️  検出時間: {detection_time:.2f}ms")
    print(f"📊 検出結果:")
    print(f"  - 左手: {result['left_hand'] is not None}")
    print(f"  - 右手: {result['right_hand'] is not None}")

    hands_detected = 0
    if result['left_hand']:
        hands_detected += 1
        print(f"\n👈 左手:")
        print(f"  - ランドマーク数: {len(result['left_hand']['landmarks'])}")
        print(f"  - 指角度:")
        for finger, angle in result['left_hand']['finger_angles'].items():
            print(f"    - {finger}: {angle:.1f}°")

    if result['right_hand']:
        hands_detected += 1
        print(f"\n👉 右手:")
        print(f"  - ランドマーク数: {len(result['right_hand']['landmarks'])}")
        print(f"  - 指角度:")
        for finger, angle in result['right_hand']['finger_angles'].items():
            print(f"    - {finger}: {angle:.1f}°")

    if hands_detected > 0:
        # ランドマークを描画
        print("\n🎨 ランドマークを描画中...")
        annotated_image = detector.draw_landmarks(image_rgb)
        annotated_bgr = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)

        # 結果を保存
        output_path = image_path.replace('.', '_tpu_result.')
        cv2.imwrite(output_path, annotated_bgr)
        print(f"💾 結果を保存: {output_path}")

    # クリーンアップ
    detector.cleanup()
    print("\n✅ テスト完了")
    return True


def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        # コマンドライン引数で画像パスが指定された場合
        image_path = sys.argv[1]
        test_with_sample_image(image_path)
    else:
        # 白紙画像でテスト
        test_with_blank_image()

    print("\n" + "=" * 70)
    print("使い方:")
    print("  白紙画像テスト: python3 scripts/test_hand_tpu_simple.py")
    print("  サンプル画像テスト: python3 scripts/test_hand_tpu_simple.py <画像パス>")
    print("=" * 70)


if __name__ == '__main__':
    main()
