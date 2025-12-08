#!/usr/bin/env python3
"""
HandDetectorTPU - Edge TPUを使用した手指検出

Google Coral TPUとhand_landmarkモデルを使用して手と指を検出します。
MediaPipe版HandDetectorと同じインターフェースを提供します。
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from pycoral.utils import edgetpu
from pycoral.adapters import common
import tflite_runtime.interpreter as tflite
import logging

logger = logging.getLogger(__name__)


class HandDetectorTPU:
    """
    Edge TPUを使用して手と指を検出するクラス

    MediaPipe HandDetectorと同じインターフェースを提供します。
    21キーポイント構成:
    - 0: 手首 (WRIST)
    - 1-4: 親指 (THUMB_CMC, MCP, IP, TIP)
    - 5-8: 人差し指 (INDEX_FINGER_MCP, PIP, DIP, TIP)
    - 9-12: 中指 (MIDDLE_FINGER_MCP, PIP, DIP, TIP)
    - 13-16: 薬指 (RING_FINGER_MCP, PIP, DIP, TIP)
    - 17-20: 小指 (PINKY_MCP, PIP, DIP, TIP)
    """

    # 指のインデックス定義（MediaPipe Handsと同じ）
    FINGER_LANDMARKS = {
        'thumb': [1, 2, 3, 4],      # 親指
        'index': [5, 6, 7, 8],       # 人差し指
        'middle': [9, 10, 11, 12],   # 中指
        'ring': [13, 14, 15, 16],    # 薬指
        'pinky': [17, 18, 19, 20]    # 小指
    }

    def __init__(
        self,
        model_path: str = 'models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
        palm_model_path: str = 'models/palm_detection_builtin_256_integer_quant.tflite',
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_palm_confidence: float = 0.5
    ):
        """
        Args:
            model_path: Hand landmark TPUモデルのパス
            palm_model_path: Palm detection モデルのパス
            max_num_hands: 検出する手の最大数
            min_detection_confidence: Hand landmark検出信頼度の閾値
            min_palm_confidence: Palm detection信頼度の閾値
        """
        self.model_path = model_path
        self.palm_model_path = palm_model_path
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_palm_confidence = min_palm_confidence

        # Palm Detectorの初期化（TFLite通常版）
        logger.info(f"Loading Palm Detection model from {palm_model_path}")
        self.palm_interpreter = tflite.Interpreter(model_path=palm_model_path)
        self.palm_interpreter.allocate_tensors()

        self.palm_input_details = self.palm_interpreter.get_input_details()[0]
        self.palm_output_details = self.palm_interpreter.get_output_details()
        self.palm_input_size = tuple(self.palm_input_details['shape'][1:3])
        logger.info(f"Palm model input size: {self.palm_input_size}")

        # Hand Landmark TPUインタープリタの初期化
        logger.info(f"Loading Hand Landmark TPU model from {model_path}")
        self.interpreter = edgetpu.make_interpreter(model_path)
        self.interpreter.allocate_tensors()

        # 入力・出力テンソル情報取得
        self.input_details = self.interpreter.get_input_details()[0]
        self.output_details = self.interpreter.get_output_details()

        # 入力サイズ取得（通常は256x256）
        self.input_size = common.input_size(self.interpreter)
        logger.info(f"Hand landmark model input size: {self.input_size}")
        logger.info(f"Number of output tensors: {len(self.output_details)}")

        # 出力テンソルのインデックスを特定
        for i, detail in enumerate(self.output_details):
            logger.info(f"Output {i}: shape={detail['shape']}, dtype={detail['dtype']}")

        self.results = None

    def detect(self, frame: np.ndarray) -> Dict[str, any]:
        """
        フレームから手を検出

        Args:
            frame: RGB画像フレーム (H x W x 3)

        Returns:
            検出結果の辞書（MediaPipe HandDetectorと互換）:
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
        detection_result = {
            'left_hand': None,
            'right_hand': None
        }

        # Step 1: Palm detection - 手のひらの位置を検出
        palm_regions = self._detect_palms(frame)

        if not palm_regions:
            logger.info("No palms detected")
            self.results = detection_result
            return detection_result

        logger.info(f"Detected {len(palm_regions)} palm(s)")

        # Step 2: Hand landmark detection - 各手の領域でランドマークを検出
        for i, palm_region in enumerate(palm_regions):
            if i >= self.max_num_hands:
                break

            # 手の領域を切り抜く
            hand_roi = self._extract_hand_roi(frame, palm_region)

            if hand_roi is None:
                continue

            # Hand landmarkモデルで指の位置を検出
            landmarks, confidence = self._detect_hand_landmarks(hand_roi, palm_region, frame.shape)

            if landmarks is None:
                continue

            # 手の左右を判定
            hand_key = self._determine_hand_side(landmarks, frame.shape)

            # 既に同じ側の手が検出されている場合はスキップ
            if detection_result[hand_key] is not None:
                continue

            # 各指の角度を計算
            finger_angles = self._calculate_finger_angles(landmarks)

            detection_result[hand_key] = {
                'landmarks': landmarks,
                'finger_angles': finger_angles
            }

        self.results = detection_result
        return detection_result

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        フレームを前処理してTPU入力形式に変換

        Args:
            frame: RGB画像 (H x W x 3)

        Returns:
            前処理済みテンソル
        """
        # モデル入力サイズにリサイズ
        resized = cv2.resize(frame, self.input_size)

        # uint8のまま（量子化モデル）
        input_tensor = resized.astype(np.uint8)

        return input_tensor

    def _detect_palms(self, frame: np.ndarray) -> List[Dict]:
        """
        Palm detectorで手のひらの位置を検出

        Args:
            frame: RGB画像フレーム (H x W x 3)

        Returns:
            検出された手のひら領域のリスト
            各要素: {'bbox': [x, y, w, h], 'confidence': float, 'keypoints': [...]}
        """
        # Palm detection用に前処理
        input_tensor = cv2.resize(frame, self.palm_input_size)
        input_tensor = input_tensor.astype(np.uint8)
        input_tensor = np.expand_dims(input_tensor, axis=0)

        # Palm detection推論
        self.palm_interpreter.set_tensor(self.palm_input_details['index'], input_tensor)
        self.palm_interpreter.invoke()

        # 出力取得（モデルによって異なる可能性があるため、柔軟に対応）
        palm_regions = []

        # TODO: Palm detectionモデルの出力形式を確認して、適切にパース
        # 暫定的に、フレーム全体を手の領域として返す（簡易実装）
        h, w = frame.shape[:2]
        palm_regions.append({
            'bbox': [0, 0, w, h],
            'confidence': 1.0,
            'keypoints': []
        })

        return palm_regions

    def _extract_hand_roi(self, frame: np.ndarray, palm_region: Dict) -> Optional[np.ndarray]:
        """
        Palm regionから手の領域を切り抜く

        Args:
            frame: 元画像フレーム
            palm_region: Palm detectorの検出結果

        Returns:
            切り抜かれた手の画像（256x256にリサイズ済み）
        """
        x, y, w, h = palm_region['bbox']

        # 境界チェック
        frame_h, frame_w = frame.shape[:2]
        x = max(0, min(x, frame_w - 1))
        y = max(0, min(y, frame_h - 1))
        w = min(w, frame_w - x)
        h = min(h, frame_h - y)

        if w <= 0 or h <= 0:
            return None

        # ROI切り抜き
        roi = frame[y:y+h, x:x+w]

        # Hand landmarkモデルの入力サイズにリサイズ
        roi_resized = cv2.resize(roi, self.input_size)

        return roi_resized

    def _detect_hand_landmarks(
        self,
        hand_roi: np.ndarray,
        palm_region: Dict,
        original_shape: Tuple[int, int, int]
    ) -> Tuple[Optional[List[Dict]], float]:
        """
        Hand landmarkモデルで指の位置を検出

        Args:
            hand_roi: 手の領域画像（256x256）
            palm_region: Palm detectorの検出結果
            original_shape: 元画像のshape

        Returns:
            (landmarks, confidence)
        """
        # TPU推論実行
        common.set_input(self.interpreter, hand_roi.astype(np.uint8))
        self.interpreter.invoke()

        # 出力テンソルから結果を取得
        landmarks, confidence = self._parse_landmark_output(palm_region, original_shape)

        return landmarks, confidence

    def _parse_landmark_output(
        self,
        palm_region: Dict,
        original_shape: Tuple[int, int, int]
    ) -> Tuple[Optional[List[Dict]], float]:
        """
        TPU出力テンソルからランドマークを抽出

        Args:
            original_shape: 元画像のshape (H, W, C)

        Returns:
            (landmarks, confidence_score)
            landmarks: 21キーポイントのリスト [{x, y, z}, ...]
            confidence_score: 検出信頼度
        """
        # 出力テンソルを取得
        # hand_landmark_newモデルは以下の出力を持つ:
        # - output 0: hand flag (1, 1, 1, 1) - 手の検出スコア
        # - output 1: handedness (1, 1, 1, 1) - 左右の判定スコア
        # - output 2: landmarks (1, 63) - 21 landmarks x 3 coordinates (x, y, z)

        # 手の検出スコア（インデックス0と1）
        hand_flag = self.interpreter.get_tensor(self.output_details[0]['index'])
        handedness = None
        if len(self.output_details) > 1:
            handedness = self.interpreter.get_tensor(self.output_details[1]['index'])

        # ランドマーク取得（インデックス2が座標）
        landmarks_tensor = self.interpreter.get_tensor(self.output_details[2]['index'])

        # デバッグ: 出力テンソルの詳細情報をログ
        logger.info(f"hand_flag: {hand_flag.flatten()[0]:.3f}")
        if handedness is not None:
            logger.info(f"handedness: {handedness.flatten()[0]:.3f}")
        logger.info(f"landmarks shape: {landmarks_tensor.shape}, size: {landmarks_tensor.size}")

        # 信頼度チェック
        confidence = 1.0  # デフォルト
        if hand_flag is not None:
            confidence = float(hand_flag.flatten()[0])

        if confidence < self.min_detection_confidence:
            logger.info(f"❌ Confidence {confidence:.3f} below threshold {self.min_detection_confidence}")
            return None, confidence

        logger.info(f"✅ Hand detected with confidence {confidence:.3f}")

        # ランドマークを正規化座標に変換（0-1の範囲）
        # モデル出力は通常、正規化された座標または画素座標
        landmarks_flat = landmarks_tensor.flatten()

        # デバッグ: flatten後のサイズを確認
        logger.debug(f"landmarks_flat size: {landmarks_flat.size} (expected: 63 for 21 landmarks × 3)")

        # サイズが期待値と異なる場合のエラーハンドリング
        if landmarks_flat.size < 63:
            logger.error(f"Insufficient landmark data: got {landmarks_flat.size} values, expected 63")
            return None, 0.0

        landmarks = []
        palm_x, palm_y, palm_w, palm_h = palm_region['bbox']
        orig_h, orig_w = original_shape[:2]

        for i in range(21):
            idx = i * 3
            x = float(landmarks_flat[idx])
            y = float(landmarks_flat[idx + 1])
            z = float(landmarks_flat[idx + 2])

            # 座標が整数値（画素座標）の場合、正規化
            if x > 1.0 or y > 1.0:
                x = x / self.input_size[0]
                y = y / self.input_size[1]

            # ROI座標から元のフレーム座標に変換
            # x, yはROI内の正規化座標（0-1）なので、元のフレーム座標に変換
            x_global = (x * palm_w + palm_x) / orig_w
            y_global = (y * palm_h + palm_y) / orig_h

            landmarks.append({
                'x': x_global,
                'y': y_global,
                'z': z
            })

        return landmarks, confidence

    def _determine_hand_side(self, landmarks: List[Dict], frame_shape: Tuple) -> str:
        """
        ランドマークから手の左右を判定（簡易版）

        Args:
            landmarks: 21キーポイント
            frame_shape: フレームのshape

        Returns:
            'left_hand' or 'right_hand'
        """
        # 手首のx座標を使用して判定
        # フレームの左半分なら左手、右半分なら右手とする
        wrist_x = landmarks[0]['x']

        if wrist_x < 0.5:
            return 'left_hand'
        else:
            return 'right_hand'

    def _calculate_finger_angles(self, landmarks: List[Dict]) -> Dict[str, float]:
        """
        各指の曲がり角度を計算（MediaPipe版と同じロジック）

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

            # 指の曲がり角度を計算
            if finger_name == 'thumb':
                # 親指は特別処理
                angle = self._calculate_thumb_angle(wrist, joint_positions)
            else:
                # その他の指
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
        cmc = joint_positions[0]
        tip = joint_positions[3]

        v1 = cmc - wrist
        v2 = tip - cmc

        angle = self._angle_between_vectors(v1, v2)

        return angle

    def _calculate_finger_angle(self, joint_positions: List[np.ndarray]) -> float:
        """
        指の曲がり角度を計算

        Args:
            joint_positions: 指の4つの関節位置 [MCP, PIP, DIP, TIP]

        Returns:
            角度（0-180度）
        """
        mcp = joint_positions[0]
        pip = joint_positions[1]
        dip = joint_positions[2]

        v1 = pip - mcp
        v2 = dip - pip

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
        v1_norm = np.linalg.norm(v1)
        v2_norm = np.linalg.norm(v2)

        if v1_norm == 0 or v2_norm == 0:
            return 0.0

        v1_normalized = v1 / v1_norm
        v2_normalized = v2 / v2_norm

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
        if not self.results:
            return frame

        annotated_frame = frame.copy()
        h, w, _ = frame.shape

        # 手のランドマークを描画
        for hand_key in ['left_hand', 'right_hand']:
            hand_data = self.results.get(hand_key)
            if hand_data is None:
                continue

            landmarks = hand_data['landmarks']

            # ランドマークの点を描画
            for i, lm in enumerate(landmarks):
                x = int(lm['x'] * w)
                y = int(lm['y'] * h)

                # キーポイントを円で描画
                if i == 0:  # 手首は赤
                    cv2.circle(annotated_frame, (x, y), 5, (0, 0, 255), -1)
                elif i in [4, 8, 12, 16, 20]:  # 指先は緑
                    cv2.circle(annotated_frame, (x, y), 5, (0, 255, 0), -1)
                else:  # その他は青
                    cv2.circle(annotated_frame, (x, y), 3, (255, 0, 0), -1)

            # 接続線を描画
            # 手のひら
            connections = [
                (0, 1), (0, 5), (0, 9), (0, 13), (0, 17),  # 手首から各指の付け根
                (5, 9), (9, 13), (13, 17),  # 手のひらの横線
                # 親指
                (1, 2), (2, 3), (3, 4),
                # 人差し指
                (5, 6), (6, 7), (7, 8),
                # 中指
                (9, 10), (10, 11), (11, 12),
                # 薬指
                (13, 14), (14, 15), (15, 16),
                # 小指
                (17, 18), (18, 19), (19, 20)
            ]

            for start_idx, end_idx in connections:
                start_lm = landmarks[start_idx]
                end_lm = landmarks[end_idx]

                start_point = (int(start_lm['x'] * w), int(start_lm['y'] * h))
                end_point = (int(end_lm['x'] * w), int(end_lm['y'] * h))

                cv2.line(annotated_frame, start_point, end_point, (255, 255, 255), 2)

            # 左右のラベルを表示
            wrist_x = int(landmarks[0]['x'] * w)
            wrist_y = int(landmarks[0]['y'] * h)

            label = "Left" if hand_key == 'left_hand' else "Right"
            cv2.putText(
                annotated_frame,
                label,
                (wrist_x - 30, wrist_y - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

        return annotated_frame

    def cleanup(self):
        """リソースを解放"""
        # TPUインタープリタのクリーンアップは自動的に行われる
        logger.info("HandDetectorTPU cleanup completed")
