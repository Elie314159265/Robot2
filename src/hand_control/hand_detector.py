#!/usr/bin/env python3
"""
HandDetector - MediaPipe Handsを使用した手指検出

人の左手と右手を検出し、各指の21キーポイントから
指の曲がり角度を計算します。
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, List, Optional, Tuple


class HandDetector:
    """
    MediaPipe Handsを使用して手と指を検出するクラス

    21キーポイント構成:
    - 0: 手首 (WRIST)
    - 1-4: 親指 (THUMB_CMC, MCP, IP, TIP)
    - 5-8: 人差し指 (INDEX_FINGER_MCP, PIP, DIP, TIP)
    - 9-12: 中指 (MIDDLE_FINGER_MCP, PIP, DIP, TIP)
    - 13-16: 薬指 (RING_FINGER_MCP, PIP, DIP, TIP)
    - 17-20: 小指 (PINKY_MCP, PIP, DIP, TIP)
    """

    # 指のインデックス定義
    FINGER_LANDMARKS = {
        'thumb': [1, 2, 3, 4],      # 親指
        'index': [5, 6, 7, 8],       # 人差し指
        'middle': [9, 10, 11, 12],   # 中指
        'ring': [13, 14, 15, 16],    # 薬指
        'pinky': [17, 18, 19, 20]    # 小指
    }

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1
    ):
        """
        Args:
            max_num_hands: 検出する手の最大数（デフォルト: 2）
            min_detection_confidence: 検出信頼度の閾値（デフォルト: 0.7）
            min_tracking_confidence: 追跡信頼度の閾値（デフォルト: 0.5）
            model_complexity: モデルの複雑さ（0=軽量・高速, 1=標準, デフォルト: 1）
        """
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.results = None

    def detect(self, frame: np.ndarray) -> Dict[str, any]:
        """
        フレームから手を検出

        Args:
            frame: RGB画像フレーム (H x W x 3)

        Returns:
            検出結果の辞書:
            {
                'left_hand': {
                    'landmarks': [...],  # 21キーポイント
                    'finger_angles': {'thumb': 45.0, 'index': 30.0, ...}
                },
                'right_hand': {
                    'landmarks': [...],
                    'finger_angles': {'thumb': 45.0, 'index': 30.0, ...}
                }
            }
        """
        # MediaPipeはRGB画像を想定
        self.results = self.hands.process(frame)

        detection_result = {
            'left_hand': None,
            'right_hand': None
        }

        if not self.results.multi_hand_landmarks:
            return detection_result

        # 各検出された手を処理
        for hand_landmarks, handedness in zip(
            self.results.multi_hand_landmarks,
            self.results.multi_handedness
        ):
            # 左右の判定
            hand_label = handedness.classification[0].label  # 'Left' or 'Right'
            hand_key = 'left_hand' if hand_label == 'Left' else 'right_hand'

            # ランドマークを配列に変換
            landmarks = []
            for lm in hand_landmarks.landmark:
                landmarks.append({
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z
                })

            # 各指の角度を計算
            finger_angles = self._calculate_finger_angles(landmarks)

            detection_result[hand_key] = {
                'landmarks': landmarks,
                'finger_angles': finger_angles
            }

        return detection_result

    def _calculate_finger_angles(self, landmarks: List[Dict]) -> Dict[str, float]:
        """
        各指の曲がり角度を計算

        Args:
            landmarks: 21キーポイントのリスト

        Returns:
            各指の角度の辞書 {'thumb': 45.0, 'index': 30.0, ...}
            角度は0-180度（0度=完全に伸びた状態、180度=完全に曲がった状態）
        """
        finger_angles = {}

        # 手首の位置
        wrist = np.array([landmarks[0]['x'], landmarks[0]['y'], landmarks[0]['z']])

        for finger_name, indices in self.FINGER_LANDMARKS.items():
            # 各指の関節位置を取得
            joint_positions = []
            for idx in indices:
                lm = landmarks[idx]
                joint_positions.append(np.array([lm['x'], lm['y'], lm['z']]))

            # 指の曲がり角度を計算（簡易版: 手首からTIPまでの直線距離と関節間距離の比）
            if finger_name == 'thumb':
                # 親指は特別処理（CMC-TIPの角度）
                angle = self._calculate_thumb_angle(wrist, joint_positions)
            else:
                # その他の指: MCP-TIPの曲がり具合
                angle = self._calculate_finger_angle(joint_positions)

            finger_angles[finger_name] = angle

        return finger_angles

    def _calculate_thumb_angle(
        self,
        wrist: np.ndarray,
        joint_positions: List[np.ndarray]
    ) -> float:
        """
        親指の開閉角度を計算

        Args:
            wrist: 手首の3D座標
            joint_positions: 親指の4つの関節位置

        Returns:
            角度（0-180度）
        """
        # CMC (親指の付け根) から TIP (親指先) へのベクトル
        cmc = joint_positions[0]
        tip = joint_positions[3]

        # 手首からCMCへのベクトル
        v1 = cmc - wrist
        # CMCからTIPへのベクトル
        v2 = tip - cmc

        # 2つのベクトルのなす角度を計算
        angle = self._angle_between_vectors(v1, v2)

        return angle

    def _calculate_finger_angle(self, joint_positions: List[np.ndarray]) -> float:
        """
        指の曲がり角度を計算（人差し指、中指、薬指、小指）

        Args:
            joint_positions: 指の4つの関節位置 [MCP, PIP, DIP, TIP]

        Returns:
            角度（0-180度）
        """
        # MCP-PIP-DIPの角度を計算
        mcp = joint_positions[0]
        pip = joint_positions[1]
        dip = joint_positions[2]

        # MCP→PIPベクトル
        v1 = pip - mcp
        # PIP→DIPベクトル
        v2 = dip - pip

        # 角度を計算
        angle = self._angle_between_vectors(v1, v2)

        return angle

    def _angle_between_vectors(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """
        2つのベクトル間の角度を計算（度数法）

        Args:
            v1: ベクトル1
            v2: ベクトル2

        Returns:
            角度（0-180度）
        """
        # ベクトルを正規化
        v1_normalized = v1 / np.linalg.norm(v1)
        v2_normalized = v2 / np.linalg.norm(v2)

        # 内積から角度を計算
        dot_product = np.dot(v1_normalized, v2_normalized)
        # 数値誤差対策
        dot_product = np.clip(dot_product, -1.0, 1.0)

        angle_rad = np.arccos(dot_product)
        angle_deg = np.degrees(angle_rad)

        return angle_deg

    def draw_landmarks(self, frame: np.ndarray) -> np.ndarray:
        """
        検出結果をフレームに描画

        Args:
            frame: RGB画像フレーム

        Returns:
            描画済みフレーム
        """
        if not self.results or not self.results.multi_hand_landmarks:
            return frame

        annotated_frame = frame.copy()

        for hand_landmarks, handedness in zip(
            self.results.multi_hand_landmarks,
            self.results.multi_handedness
        ):
            # 手のランドマークを描画
            self.mp_drawing.draw_landmarks(
                annotated_frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )

            # 左右のラベルを表示
            hand_label = handedness.classification[0].label
            h, w, _ = frame.shape
            wrist_landmark = hand_landmarks.landmark[0]
            x = int(wrist_landmark.x * w)
            y = int(wrist_landmark.y * h)

            cv2.putText(
                annotated_frame,
                hand_label,
                (x - 30, y - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

        return annotated_frame

    def cleanup(self):
        """リソースを解放"""
        if self.hands:
            self.hands.close()
