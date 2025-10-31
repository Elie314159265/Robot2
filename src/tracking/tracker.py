"""
Ball Tracker
Maintains ball tracking state and control loop
"""

from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class BallTracker:
    """
    Ball tracking state machine

    Features:
    - Maintain tracking state
    - Handle lost detection
    - Coordinate servo control
    """

    STATE_IDLE = "idle"
    STATE_TRACKING = "tracking"
    STATE_LOST = "lost"

    def __init__(self, pid_controller):
        """
        Initialize tracker.

        Args:
            pid_controller: PIDController instance
        """
        self.pid_controller = pid_controller
        self.state = self.STATE_IDLE
        self.last_detection = None
        self.frames_since_detection = 0
        self.max_frames_lost = 30  # 1 second at 30 FPS

    def update(self, detection: Optional[Dict]) -> float:
        """
        Update tracking state and return servo command.

        Args:
            detection: Detection result or None

        Returns:
            Servo angle command
        """
        # Placeholder - implementation pending
        return 0.0

    def set_state(self, new_state: str) -> None:
        """Update tracking state"""
        if new_state in [self.STATE_IDLE, self.STATE_TRACKING, self.STATE_LOST]:
            self.state = new_state
            logger.info(f"Tracker state changed to: {new_state}")
