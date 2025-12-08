#!/usr/bin/env python3
"""
FingerMapper - 指の角度からサーボ角度へのマッピング

人の指の角度を検出し、PCA9685サーボドライバの各チャンネルに
割り当てられたサーボモータの角度にマッピングします。

サーボ割り当て:
- 左手: 親指(0番), 人差し指(2番), 中指(4番), 薬指(6番)
- 右手: 親指(1番), 人差し指(3番), 中指(5番), 薬指(7番)
"""

import numpy as np
from typing import Dict, Optional


class FingerMapper:
    """
    指の角度をサーボ角度にマッピングするクラス
    """

    # サーボチャンネル割り当て
    SERVO_MAPPING = {
        'left_hand': {
            'thumb': 0,
            'index': 2,
            'middle': 4,
            'ring': 6
        },
        'right_hand': {
            'thumb': 1,
            'index': 3,
            'middle': 5,
            'ring': 7
        }
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
            servo_min: サーボの最小角度（度）
            servo_max: サーボの最大角度（度）
            angle_min: 指の角度の最小値（度）
            angle_max: 指の角度の最大値（度）
            invert_mapping: True の場合、マッピングを反転
                           （指が開く→サーボが閉じる）
        """
        self.servo_min = servo_min
        self.servo_max = servo_max
        self.angle_min = angle_min
        self.angle_max = angle_max
        self.invert_mapping = invert_mapping

    def map_finger_to_servo(self, finger_angle: float) -> int:
        """
        指の角度をサーボ角度にマッピング

        Args:
            finger_angle: 指の角度（0-180度）
                         0度=完全に伸びた状態
                         180度=完全に曲がった状態

        Returns:
            サーボ角度（servo_min ~ servo_max）
        """
        # 入力角度を正規化（0.0 ~ 1.0）
        normalized = (finger_angle - self.angle_min) / (self.angle_max - self.angle_min)
        normalized = np.clip(normalized, 0.0, 1.0)

        # 反転が必要な場合
        if self.invert_mapping:
            normalized = 1.0 - normalized

        # サーボ角度にマッピング
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

        # 左手を処理
        if hand_data.get('left_hand'):
            finger_angles = hand_data['left_hand'].get('finger_angles', {})
            for finger_name, channel in self.SERVO_MAPPING['left_hand'].items():
                if finger_name in finger_angles:
                    angle = finger_angles[finger_name]
                    servo_angle = self.map_finger_to_servo(angle)
                    servo_commands[channel] = servo_angle

        # 右手を処理
        if hand_data.get('right_hand'):
            finger_angles = hand_data['right_hand'].get('finger_angles', {})
            for finger_name, channel in self.SERVO_MAPPING['right_hand'].items():
                if finger_name in finger_angles:
                    angle = finger_angles[finger_name]
                    servo_angle = self.map_finger_to_servo(angle)
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
