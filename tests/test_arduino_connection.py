#!/usr/bin/env python3
"""
Arduino接続テスト
シリアル通信、サーボ制御、距離センサーの動作確認
"""

import sys
import os
import time
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.arduino import SerialController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection(port="/dev/ttyACM0"):
    """Arduino接続テスト"""
    print("=" * 70)
    print("Arduino接続テスト")
    print("=" * 70)

    # 接続
    print(f"\n1. シリアルポート接続テスト ({port})")
    controller = SerialController(port=port)

    if not controller.connect():
        print("❌ 接続失敗")
        print("\n確認事項:")
        print(f"  - Arduinoが {port} に接続されているか")
        print("  - ポート名が正しいか (ls /dev/ttyACM* で確認)")
        print("  - ユーザーがdialoutグループに所属しているか")
        return False

    print("✅ 接続成功")
    time.sleep(2)  # Arduino起動待ち

    # サーボテスト
    print("\n2. サーボ制御テスト")
    print("   サーボ0 (Pan): 90度に移動...")
    if controller.send_servo_command(0, 90):
        print("   ✅ サーボ0 成功")
    else:
        print("   ❌ サーボ0 失敗")

    time.sleep(1)

    print("   サーボ1 (Tilt): 90度に移動...")
    if controller.send_servo_command(1, 90):
        print("   ✅ サーボ1 成功")
    else:
        print("   ❌ サーボ1 失敗")

    time.sleep(1)

    # Pan/Tiltテスト
    print("\n3. Pan/Tilt統合テスト")
    test_positions = [
        (90, 90, "中央"),
        (45, 90, "左"),
        (135, 90, "右"),
        (90, 45, "上"),
        (90, 135, "下"),
        (90, 90, "中央に戻す")
    ]

    for pan, tilt, desc in test_positions:
        print(f"   {desc} (Pan:{pan}°, Tilt:{tilt}°)...")
        controller.set_pan_tilt(pan, tilt)
        time.sleep(1)

    print("   ✅ Pan/Tilt テスト完了")

    # 距離センサーテスト
    print("\n4. 距離センサーテスト")
    print("   10回測定します...")

    for i in range(10):
        distance = controller.read_distance()
        if distance is not None:
            if distance > 0:
                print(f"   測定{i+1}: {distance:.1f} cm")
            else:
                print(f"   測定{i+1}: 範囲外 (検出なし)")
        else:
            print(f"   測定{i+1}: エラー")
        time.sleep(0.5)

    print("   ✅ 距離センサーテスト完了")

    # クリーンアップ
    print("\n5. クリーンアップ")
    controller.cleanup()
    print("   ✅ 接続を切断しました")

    print("\n" + "=" * 70)
    print("✅ すべてのテストが完了しました")
    print("=" * 70)

    return True


if __name__ == '__main__':
    # ポート指定（デフォルト: /dev/ttyACM0）
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"

    try:
        success = test_connection(port)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n中断されました")
        sys.exit(1)
