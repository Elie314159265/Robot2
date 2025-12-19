#!/usr/bin/env python3
"""
FingerMapper - 指の角度からサーボ角度へのマッピング

人の指の角度を検出し、PCA9685サーボドライバの各チャンネルに
割り当てられたサーボモータの角度にマッピングします。

walk_program.inoベースの実装：
- 指が開いている（angle=0） → ヒップ前、足上げ
- 指が閉じている（angle=180） → ヒップ後ろ、足下ろす

サーボ割り当て（walk_program.ino準拠）:
- 左手（ヒップ制御）: 親指(ch0/FL), 人差し指(ch2/FR), 中指(ch8/BL), 薬指(ch6/BR)
- 右手（膝制御）: 親指(ch1/FL), 人差し指(ch3/FR), 中指(ch5/BL), 薬指(ch7/BR)

FL=Front Left, FR=Front Right, BL=Back Left, BR=Back Right
"""

import numpy as np
from typing import Dict, Optional


class FingerMapper:
    """
    指の角度をサーボ角度にマッピングするクラス
    walk_program.inoのパラメータに基づく実装
    """

    # サーボチャンネル割り当て（walk_program.ino準拠）
    # FL: Front Left, FR: Front Right, BL: Back Left, BR: Back Right
    SERVO_MAPPING = {
        'left_hand': {
            'thumb': 0,      # FL hip
            'index': 2,      # FR hip
            'middle': 8,     # BL hip (walk_program.inoでch 8使用)
            'ring': 6        # BR hip
        },
        'right_hand': {
            'thumb': 1,      # FL knee
            'index': 3,      # FR knee
            'middle': 5,     # BL knee
            'ring': 7        # BR knee
        }
    }

    # walk_program.inoベースのサーボ設定（PWM値から角度に逆変換済み）
    # PWM値: 150-600 → 角度: 0-180度
    # 変換式: angle = (pwm - 150) / 450 * 180
    SERVO_CONFIG = {
        # 左ヒップ（ch 0, 8）
        # walk_program.inoではBL hipはch 4ではなくch 8を使用
        0: {'type': 'left_hip', 'open': 0, 'close': 90},      # FL hip
        8: {'type': 'left_hip', 'open': 0, 'close': 90},      # BL hip
        # 右ヒップ（ch 2, 6）
        2: {'type': 'right_hip', 'open': 90, 'close': 0},     # FR hip
        6: {'type': 'right_hip', 'open': 90, 'close': 0},     # BR hip
        # 左膝（ch 1, 5）
        1: {'type': 'left_knee', 'open': 0, 'close': 80},     # FL knee
        5: {'type': 'left_knee', 'open': 0, 'close': 80},     # BL knee
        # 右膝（ch 3, 7）
        3: {'type': 'right_knee', 'open': 80, 'close': 0},    # FR knee
        7: {'type': 'right_knee', 'open': 80, 'close': 0},    # BR knee
    }

    def __init__(
        self,
        servo_min: int = 0,
        servo_max: int = 180,
        angle_min: float = 0.0,
        angle_max: float = 180.0,
        invert_mapping: bool = False
    ):
        """
        Args:
            servo_min: サーボの最小角度（度）- 廃止予定、SERVO_CONFIGを使用
            servo_max: サーボの最大角度（度）- 廃止予定、SERVO_CONFIGを使用
            angle_min: 指の角度の最小値（度）
            angle_max: 指の角度の最大値（度）
            invert_mapping: 廃止予定、SERVO_CONFIGを使用
        """
        # 後方互換性のため残すが、SERVO_CONFIGを優先
        self.servo_min = servo_min
        self.servo_max = servo_max
        self.angle_min = angle_min
        self.angle_max = angle_max
        self.invert_mapping = invert_mapping

    def map_finger_to_servo(self, finger_angle: float, channel: int = None) -> int:
        """
        指の角度をサーボ角度にマッピング（walk_program.ino準拠）

        Args:
            finger_angle: 指の角度（0-180度）
                         0度=完全に伸びた状態（開いている）
                         180度=完全に曲がった状態（閉じている）
            channel: サーボチャンネル番号（0-15）
                    指定された場合、SERVO_CONFIGを使用

        Returns:
            サーボ角度（0-180度、Arduino側でPWM値に変換される）
        """
        if channel is not None and channel in self.SERVO_CONFIG:
            # walk_program.inoベースの新しいマッピング
            config = self.SERVO_CONFIG[channel]
            open_angle = config['open']    # 指が開いている時のサーボ角度
            close_angle = config['close']  # 指が閉じている時のサーボ角度

            # 指の角度を正規化（0.0 ~ 1.0）
            # 0度（開）→ 0.0、180度（閉）→ 1.0
            normalized = (finger_angle - self.angle_min) / (self.angle_max - self.angle_min)
            normalized = np.clip(normalized, 0.0, 1.0)

            # サーボ角度を線形補間
            # normalized=0 → open_angle, normalized=1 → close_angle
            servo_angle = open_angle + normalized * (close_angle - open_angle)

            return int(servo_angle)

        else:
            # 後方互換性：古いマッピング方式
            normalized = (finger_angle - self.angle_min) / (self.angle_max - self.angle_min)
            normalized = np.clip(normalized, 0.0, 1.0)

            if self.invert_mapping:
                normalized = 1.0 - normalized

            servo_angle = self.servo_min + normalized * (self.servo_max - self.servo_min)
            return int(servo_angle)

    def map_hand_to_servos(self, hand_data: Dict) -> Dict[int, int]:
        """
        手全体の指角度をサーボ角度にマッピング

        Args:
            hand_data: 手検出データ
                {
                    'left_hand': {
                        'finger_angles': {'thumb': 45.0, 'index': 30.0, ...}
                    },
                    'right_hand': {
                        'finger_angles': {'thumb': 45.0, 'index': 30.0, ...}
                    }
                }

        Returns:
            サーボチャンネルと角度の辞書 {channel: angle}
            例: {0: 90, 1: 120, 2: 45, ...}
        """
        servo_commands = {}

        # 左手を処理（ヒップ制御）
        if hand_data.get('left_hand'):
            finger_angles = hand_data['left_hand'].get('finger_angles', {})
            for finger_name, channel in self.SERVO_MAPPING['left_hand'].items():
                if finger_name in finger_angles:
                    angle = finger_angles[finger_name]
                    # SERVO_CONFIGを使用するためにchannelを渡す
                    servo_angle = self.map_finger_to_servo(angle, channel=channel)
                    servo_commands[channel] = servo_angle

        # 右手を処理（膝制御）
        if hand_data.get('right_hand'):
            finger_angles = hand_data['right_hand'].get('finger_angles', {})
            for finger_name, channel in self.SERVO_MAPPING['right_hand'].items():
                if finger_name in finger_angles:
                    angle = finger_angles[finger_name]
                    # SERVO_CONFIGを使用するためにchannelを渡す
                    servo_angle = self.map_finger_to_servo(angle, channel=channel)
                    servo_commands[channel] = servo_angle

        return servo_commands

    def get_servo_channel(self, hand: str, finger: str) -> Optional[int]:
        """
        指定された手と指のサーボチャンネル番号を取得

        Args:
            hand: 'left_hand' or 'right_hand'
            finger: 'thumb', 'index', 'middle', 'ring'

        Returns:
            サーボチャンネル番号、存在しない場合はNone
        """
        if hand in self.SERVO_MAPPING and finger in self.SERVO_MAPPING[hand]:
            return self.SERVO_MAPPING[hand][finger]
        return None

    def format_servo_commands(self, servo_commands: Dict[int, int]) -> str:
        """
        サーボコマンドを文字列形式にフォーマット

        Args:
            servo_commands: {channel: angle} 辞書

        Returns:
            フォーマットされた文字列
        """
        lines = []
        for channel in sorted(servo_commands.keys()):
            angle = servo_commands[channel]
            lines.append(f"Channel {channel}: {angle}°")
        return "\n".join(lines)
