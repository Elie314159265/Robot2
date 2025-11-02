"""
PID Controller for servo tracking
Controls servo position to keep ball centered in frame
"""

from typing import Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PIDController:
    """
    PID controller for ball tracking servo control

    Features:
    - Proportional, Integral, Derivative control
    - Servo angle limits
    - Performance monitoring
    """

    def __init__(
        self,
        kp: float = 0.5,
        ki: float = 0.1,
        kd: float = 0.2,
        servo_min: float = -90,
        servo_max: float = 90,
        setpoint: float = 0.0
    ):
        """
        Initialize PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            servo_min: Minimum servo angle
            servo_max: Maximum servo angle
            setpoint: Target error (0 = center)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.servo_min = servo_min
        self.servo_max = servo_max
        self.setpoint = setpoint

        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = datetime.now()

    def update(self, error: float) -> float:
        """
        Update PID controller.

        Args:
            error: Current error (ball_position - center)

        Returns:
            Control output (servo angle adjustment)
        """
        # Calculate time delta
        now = datetime.now()
        dt = (now - self.last_time).total_seconds()

        if dt <= 0:
            dt = 0.01  # Prevent division by zero

        # Proportional term
        p_term = self.kp * error

        # Integral term (with anti-windup)
        self.integral += error * dt
        # Limit integral to prevent windup
        integral_limit = 100.0
        self.integral = max(-integral_limit, min(integral_limit, self.integral))
        i_term = self.ki * self.integral

        # Derivative term
        d_term = self.kd * (error - self.last_error) / dt

        # Calculate output
        output = p_term + i_term + d_term

        # Clamp output to servo limits
        output = max(self.servo_min, min(self.servo_max, output))

        # Update state
        self.last_error = error
        self.last_time = now

        logger.debug(f"PID: error={error:.2f}, P={p_term:.2f}, I={i_term:.2f}, D={d_term:.2f}, output={output:.2f}")

        return output

    def reset(self) -> None:
        """Reset PID state"""
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = datetime.now()

    def set_gains(self, kp: float, ki: float, kd: float) -> None:
        """Update PID gains"""
        self.kp = kp
        self.ki = ki
        self.kd = kd
