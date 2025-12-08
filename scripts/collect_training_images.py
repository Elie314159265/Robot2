#!/usr/bin/env python3
"""
トレーニング用画像収集スクリプト
サッカーボールの画像を自動的に撮影
"""

import sys
import os
import time
import cv2
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.camera import CameraController

# 保存先ディレクトリ
DATASET_DIR = "training_data/soccer_ball"
os.makedirs(DATASET_DIR, exist_ok=True)

print("=" * 70)
print("サッカーボール トレーニングデータ収集")
print("=" * 70)
print(f"\n保存先: {DATASET_DIR}")
print("\n📋 撮影のコツ:")
print("  1. 様々な角度からボールを撮影")
print("  2. 様々な距離（近距離・中距離・遠距離）")
print("  3. 様々な照明条件（明るい・暗い）")
print("  4. 様々な背景（無地・複雑）")
print("  5. ボールの位置を変える（中央・端・斜め）")
print("\n目標: 300-500枚")
print("=" * 70)

# 既存の画像数を確認
existing_images = len([f for f in os.listdir(DATASET_DIR) if f.endswith('.jpg')])
print(f"\n既存の画像: {existing_images}枚")

# カメラ初期化
print("\nカメラを初期化中...")
camera = CameraController(resolution=(640, 480), framerate=30, debug=False)

if not camera.initialize():
    print("❌ カメラ初期化失敗")
    sys.exit(1)

if not camera.start():
    print("❌ カメラ起動失敗")
    camera.cleanup()
    sys.exit(1)

print("✅ カメラ起動成功")
time.sleep(2)

print("\n" + "=" * 70)
print("撮影モード")
print("=" * 70)
print("操作方法:")
print("  - Enterキー: 画像を撮影")
print("  - 'q' + Enter: 終了")
print("=" * 70)

image_count = existing_images

try:
    while True:
        # プレビュー表示（コンソールに状態表示）
        print(f"\r現在の撮影枚数: {image_count}/500  [Enter: 撮影, q: 終了]", end="", flush=True)

        # ユーザー入力待ち
        user_input = input("\n")

        if user_input.lower() == 'q':
            print("\n撮影を終了します")
            break

        # フレームキャプチャ
        frame = camera.capture_frame()
        if frame is None:
            print("❌ フレームキャプチャ失敗")
            continue

        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"ball_{timestamp}_{image_count:04d}.jpg"
        filepath = os.path.join(DATASET_DIR, filename)

        # BGRに変換して保存
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imwrite(filepath, frame_bgr)

        image_count += 1
        print(f"✅ 保存: {filename}")

        # 進捗表示
        if image_count % 50 == 0:
            print(f"\n🎯 {image_count}枚撮影完了！")

        if image_count >= 500:
            print(f"\n🎉 目標の500枚に到達しました！")
            break

except KeyboardInterrupt:
    print("\n\n中断されました")

finally:
    camera.cleanup()
    print(f"\n✅ カメラ停止")
    print(f"\n📊 撮影結果:")
    print(f"  総撮影枚数: {image_count}枚")
    print(f"  保存先: {DATASET_DIR}")

    if image_count >= 300:
        print(f"\n✅ 十分なデータが集まりました！")
        print(f"   次のステップ: アノテーション（バウンディングボックスの付与）")
    elif image_count >= 100:
        print(f"\n⚠️  データが少し足りません（推奨: 300枚以上）")
        print(f"   あと{300 - image_count}枚撮影することをお勧めします")
    else:
        print(f"\n❌ データが不足しています")
        print(f"   あと{300 - image_count}枚必要です")
