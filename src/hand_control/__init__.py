"""
手指検出・サーボ制御モジュール

MediaPipe Hands（CPU版）またはGoogle Coral TPU（TPU版）を使用して
人の手と指の角度を検出し、サーボモータの角度にマッピングする機能を提供します。
"""

from .hand_detector import HandDetector
from .hand_detector_tpu import HandDetectorTPU
from .finger_mapper import FingerMapper

__all__ = ['HandDetector', 'HandDetectorTPU', 'FingerMapper']
