#!/usr/bin/env python3
"""
finger_mapper.pyの検証スクリプト
walk_program.inoのPWM値との整合性を確認
"""

import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, '/home/user/Robot2/src')

# FingerMapperを直接インポート（__init__.pyを経由しない）
# これによりcv2などの依存関係を回避
import importlib.util
spec = importlib.util.spec_from_file_location(
    "finger_mapper",
    "/home/user/Robot2/src/hand_control/finger_mapper.py"
)
finger_mapper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finger_mapper_module)
FingerMapper = finger_mapper_module.FingerMapper


def pwm_to_angle(pwm):
    """PWM値を角度に変換（walk_program.inoの変換式）"""
    return (pwm - 150) / 450 * 180


def verify_pwm_mapping():
    """walk_program.inoのPWM値と角度の対応を検証"""
    print("=" * 60)
    print("walk_program.ino PWM値と角度の対応")
    print("=" * 60)

    # walk_program.inoのPWM値（line 13-24）
    pwm_values = {
        "左ヒップ": {
            "FORWARD": 150,
            "NEUTRAL": 263,
            "BACKWARD": 375
        },
        "右ヒップ": {
            "FORWARD": 375,
            "NEUTRAL": 263,
            "BACKWARD": 150
        },
        "左膝": {
            "UP": 150,
            "DOWN": 350
        },
        "右膝": {
            "UP": 350,
            "DOWN": 150
        }
    }

    for part, values in pwm_values.items():
        print(f"\n{part}:")
        for state, pwm in values.items():
            angle = pwm_to_angle(pwm)
            print(f"  {state:10s}: PWM={pwm:3d} → {angle:5.1f}°")


def verify_servo_config():
    """SERVO_CONFIGがwalk_program.inoと一致するか検証"""
    print("\n" + "=" * 60)
    print("SERVO_CONFIGの検証")
    print("=" * 60)

    mapper = FingerMapper()

    # 期待される値（walk_program.inoから計算）
    expected = {
        # 左ヒップ: FORWARD=0°, BACKWARD=90°
        0: {"open": 0, "close": 90, "name": "FL hip (左ヒップ)"},
        8: {"open": 0, "close": 90, "name": "BL hip (左ヒップ)"},
        # 右ヒップ: FORWARD=90°, BACKWARD=0°
        2: {"open": 90, "close": 0, "name": "FR hip (右ヒップ)"},
        6: {"open": 90, "close": 0, "name": "BR hip (右ヒップ)"},
        # 左膝: UP=0°, DOWN=80°
        1: {"open": 0, "close": 80, "name": "FL knee (左膝)"},
        5: {"open": 0, "close": 80, "name": "BL knee (左膝)"},
        # 右膝: UP=80°, DOWN=0°
        3: {"open": 80, "close": 0, "name": "FR knee (右膝)"},
        7: {"open": 80, "close": 0, "name": "BR knee (右膝)"},
    }

    all_match = True
    for channel, exp in expected.items():
        actual = mapper.SERVO_CONFIG.get(channel)

        if actual is None:
            print(f"\n✗ ch {channel} ({exp['name']}): 設定なし")
            all_match = False
            continue

        match = (actual['open'] == exp['open'] and
                 actual['close'] == exp['close'])

        status = "✓" if match else "✗"
        print(f"\n{status} ch {channel} ({exp['name']}):")
        print(f"  期待値: open={exp['open']:2d}°, close={exp['close']:2d}°")
        print(f"  実際値: open={actual['open']:2d}°, close={actual['close']:2d}°")

        if not match:
            all_match = False

    return all_match


def test_finger_mapping():
    """指の角度からサーボ角度へのマッピングをテスト"""
    print("\n" + "=" * 60)
    print("指の角度マッピングテスト")
    print("=" * 60)

    mapper = FingerMapper()

    # テストケース: 各チャンネルで指の角度0°, 90°, 180°をテスト
    test_channels = [0, 1, 2, 3, 5, 6, 7, 8]
    test_angles = [0, 90, 180]  # 開く、中間、閉じる

    for channel in test_channels:
        config = mapper.SERVO_CONFIG[channel]
        print(f"\nch {channel} ({config['type']}):")

        for finger_angle in test_angles:
            servo_angle = mapper.map_finger_to_servo(finger_angle, channel=channel)

            # 期待値を計算
            normalized = finger_angle / 180.0
            expected = int(config['open'] + normalized * (config['close'] - config['open']))

            match = "✓" if servo_angle == expected else "✗"
            print(f"  {match} 指{finger_angle:3d}° → サーボ{servo_angle:3d}° (期待値: {expected:3d}°)")


def test_hand_to_servos():
    """map_hand_to_servos関数のテスト"""
    print("\n" + "=" * 60)
    print("map_hand_to_servos関数のテスト")
    print("=" * 60)

    mapper = FingerMapper()

    # テストデータ: 全ての指が開いている状態（0°）
    test_data_open = {
        'left_hand': {
            'finger_angles': {
                'thumb': 0,    # FL hip (ch 0)
                'index': 0,    # FR hip (ch 2)
                'middle': 0,   # BL hip (ch 8)
                'ring': 0      # BR hip (ch 6)
            }
        },
        'right_hand': {
            'finger_angles': {
                'thumb': 0,    # FL knee (ch 1)
                'index': 0,    # FR knee (ch 3)
                'middle': 0,   # BL knee (ch 5)
                'ring': 0      # BR knee (ch 7)
            }
        }
    }

    # テストデータ: 全ての指が閉じている状態（180°）
    test_data_closed = {
        'left_hand': {
            'finger_angles': {
                'thumb': 180,
                'index': 180,
                'middle': 180,
                'ring': 180
            }
        },
        'right_hand': {
            'finger_angles': {
                'thumb': 180,
                'index': 180,
                'middle': 180,
                'ring': 180
            }
        }
    }

    print("\n【全ての指が開いている状態（0°）】")
    print("期待される動作: ヒップは前、膝は上げる")
    servo_commands = mapper.map_hand_to_servos(test_data_open)
    for channel in sorted(servo_commands.keys()):
        angle = servo_commands[channel]
        config = mapper.SERVO_CONFIG[channel]
        expected = config['open']
        match = "✓" if angle == expected else "✗"
        print(f"  {match} ch {channel:2d}: {angle:3d}° (期待値: {expected:3d}° = open)")

    print("\n【全ての指が閉じている状態（180°）】")
    print("期待される動作: ヒップは後ろ、膝は下ろす")
    servo_commands = mapper.map_hand_to_servos(test_data_closed)
    for channel in sorted(servo_commands.keys()):
        angle = servo_commands[channel]
        config = mapper.SERVO_CONFIG[channel]
        expected = config['close']
        match = "✓" if angle == expected else "✗"
        print(f"  {match} ch {channel:2d}: {angle:3d}° (期待値: {expected:3d}° = close)")


def main():
    """メイン関数"""
    print("\n" + "=" * 60)
    print("finger_mapper.py 検証テスト")
    print("=" * 60)

    # 1. PWM値と角度の対応を表示
    verify_pwm_mapping()

    # 2. SERVO_CONFIGの検証
    config_ok = verify_servo_config()

    # 3. 指の角度マッピングテスト
    test_finger_mapping()

    # 4. map_hand_to_servos関数のテスト
    test_hand_to_servos()

    # 総合判定
    print("\n" + "=" * 60)
    print("総合判定")
    print("=" * 60)
    if config_ok:
        print("✓ SERVO_CONFIGはwalk_program.inoと一致しています")
        print("✓ 実装は正しく動作する見込みです")
    else:
        print("✗ SERVO_CONFIGに不一致があります")
        print("✗ 修正が必要です")
    print("=" * 60)


if __name__ == "__main__":
    main()
