"""
Ball Tracker
Maintains ball tracking state and control loop
"""

from typing import Optional, Dict, Tuple
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

    def __init__(self, pid_pan, pid_tilt=None, frame_width: int = 640, frame_height: int = 480):
        """
        Initialize tracker.

        Args:
            pid_pan: PIDController instance for pan (horizontal)
            pid_tilt: PIDController instance for tilt (vertical) - currently unused
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
        """
        self.pid_pan = pid_pan
        self.pid_tilt = pid_tilt  # Keep for backward compatibility, but not used
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.state = self.STATE_IDLE
        self.last_detection = None
        self.frames_since_detection = 0
        self.max_frames_lost = 30  # 1 second at 30 FPS

        # Current servo positions (start at center: 90 degrees)
        self.current_pan = 90.0
        self.current_tilt = 90.0  # Fixed at center (not used in 1-axis setup)

    def update(self, detection: Optional[Dict]) -> Tuple[float, float]:
        """
        Update tracking state and return servo commands.

        Args:
            detection: Detection result dict with 'center_x' and 'center_y', or None

        Returns:
            Tuple of (pan_angle, tilt_angle) in degrees
        """
        if detection is not None:
            # Ball detected
            self.last_detection = detection
            self.frames_since_detection = 0
            self.set_state(self.STATE_TRACKING)

            # Extract ball center position
            ball_x = detection.get('center_x', self.frame_width / 2)
            ball_y = detection.get('center_y', self.frame_height / 2)

            # Calculate error from frame center (horizontal only)
            center_x = self.frame_width / 2

            error_x = ball_x - center_x  # Positive = ball is right of center

            # Normalize error to range [-1, 1]
            normalized_error_x = error_x / center_x

            # Update PID controller (pan only)
            # Note: Negative sign compensates for servo mounting direction
            # When ball is right of center (error_x > 0), move servo left (decrease angle)
            # When ball is left of center (error_x < 0), move servo right (increase angle)
            pan_adjustment = self.pid_pan.update(-normalized_error_x)

            # Apply adjustment to current position
            self.current_pan += pan_adjustment

            # Clamp to valid servo range (0-180 degrees)
            self.current_pan = max(0, min(180, self.current_pan))
            # Tilt remains fixed at center (90 degrees) for 1-axis setup

            logger.debug(f"Ball at ({ball_x:.0f}, {ball_y:.0f}), error_x={error_x:.1f}, pan={self.current_pan:.1f}°")

        else:
            # Ball not detected
            self.frames_since_detection += 1

            if self.frames_since_detection > self.max_frames_lost:
                self.set_state(self.STATE_LOST)
                # Reset PID controller (pan only)
                self.pid_pan.reset()
                if self.pid_tilt:
                    self.pid_tilt.reset()

            logger.debug(f"Ball lost for {self.frames_since_detection} frames")

        return (self.current_pan, self.current_tilt)

    def set_state(self, new_state: str) -> None:
        """Update tracking state"""
        if new_state != self.state:
            if new_state in [self.STATE_IDLE, self.STATE_TRACKING, self.STATE_LOST]:
                self.state = new_state
                logger.info(f"Tracker state changed to: {new_state}")

    def reset(self) -> None:
        """Reset tracker to initial state"""
        self.state = self.STATE_IDLE
        self.last_detection = None
        self.frames_since_detection = 0
        self.current_pan = 90.0
        self.current_tilt = 90.0
        self.pid_pan.reset()
        if self.pid_tilt:
            self.pid_tilt.reset()
        logger.info("Tracker reset to initial state")
