"""
Ball Blocker - Ball Blocking Controller
Monitors ultrasonic sensors and triggers servo blocking on ball crossing detection

Algorithm:
1. Camera detects ball on left or right side
2. Send high-speed monitoring command to Arduino (4 seconds, ~50Hz)
3. Arduino detects ball crossing via distance change and raises servo
4. Python monitors serial output for confirmation

Hardware mapping:
- Left ultrasonic sensor: pins 8,9 (monitors for left-side balls)
- Right ultrasonic sensor: pins 10,11 (monitors for right-side balls)
- Left side ball -> Arduino raises servo 7 (right back leg)
- Right side ball -> Arduino raises servo 5 (left back leg)

Features:
- Camera-based ball detection and position tracking
- Arduino-based high-speed ultrasonic monitoring (eliminates Python overhead)
- Real-time ball crossing detection with moving average filter
- Automatic servo blocking on detection
"""

import time
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class BallSide(Enum):
    """Ball detection side"""
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    NONE = "none"


class BallBlocker:
    """
    Ball blocking controller

    Workflow:
    1. Camera detects ball position (left/right)
    2. Send Arduino command to start high-speed monitoring
    3. Arduino monitors ultrasonic sensor for 4 seconds at ~50Hz
    4. Arduino detects ball crossing and raises servo automatically
    5. Python monitors serial output for confirmation
    """

    def __init__(
        self,
        serial_controller,
        left_threshold: float = 0.3,
        right_threshold: float = 0.7,
        monitoring_duration: float = 4.0
    ):
        """
        Initialize ball blocker.

        Args:
            serial_controller: SerialController instance for Arduino communication
            left_threshold: X-position threshold for left detection (0.0-1.0)
            right_threshold: X-position threshold for right detection (0.0-1.0)
            monitoring_duration: Ultrasonic monitoring duration (seconds)
        """
        self.serial = serial_controller
        self.left_threshold = left_threshold
        self.right_threshold = right_threshold
        self.monitoring_duration = monitoring_duration

        # State tracking
        self.is_monitoring = False
        self.blocking_active = False
        self.last_ball_side = BallSide.NONE

        # Statistics
        self.total_detections = 0
        self.successful_blocks = 0
        self.failed_blocks = 0

    def determine_ball_side(
        self,
        ball_x: float,
        frame_width: int
    ) -> BallSide:
        """
        Determine which side the ball is on based on X position.

        Args:
            ball_x: Ball X position in pixels
            frame_width: Frame width in pixels

        Returns:
            BallSide enum value
        """
        # Normalize to 0.0-1.0
        normalized_x = ball_x / frame_width

        if normalized_x < self.left_threshold:
            return BallSide.LEFT
        elif normalized_x > self.right_threshold:
            return BallSide.RIGHT
        else:
            return BallSide.CENTER

    def process_ball_detection(
        self,
        ball_x: float,
        ball_y: float,
        frame_width: int,
        frame_height: int,
        confidence: float
    ) -> bool:
        """
        Process ball detection from camera and trigger blocking if needed.

        Args:
            ball_x: Ball X position in pixels
            ball_y: Ball Y position in pixels
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            confidence: Detection confidence (0.0-1.0)

        Returns:
            True if blocking was triggered, False otherwise
        """
        if self.is_monitoring or self.blocking_active:
            logger.debug("Already monitoring or blocking, skipping")
            return False

        # Determine ball side
        ball_side = self.determine_ball_side(ball_x, frame_width)

        if ball_side == BallSide.CENTER or ball_side == BallSide.NONE:
            logger.debug(f"Ball in center or not detected, no action")
            return False

        # Ball detected on left or right side - trigger monitoring
        logger.info(f"Ball detected on {ball_side.value} side at ({ball_x:.0f}, {ball_y:.0f}), conf: {confidence:.2f}")
        self.total_detections += 1

        # Trigger high-speed monitoring on Arduino
        success = self.trigger_blocking(ball_side)

        if success:
            self.successful_blocks += 1
            logger.info(f"Blocking successful! Total: {self.successful_blocks}/{self.total_detections}")
        else:
            self.failed_blocks += 1
            logger.warning(f"Blocking failed or no ball crossing detected")

        return success

    def trigger_blocking(self, side: BallSide) -> bool:
        """
        Trigger high-speed ultrasonic monitoring and blocking on Arduino.

        This sends a command to Arduino which will:
        1. Monitor ultrasonic sensor for 4 seconds at ~50Hz
        2. Detect ball crossing via distance change
        3. Raise servo immediately on detection

        Args:
            side: Which side to monitor (LEFT or RIGHT)

        Returns:
            True if blocking was triggered successfully
        """
        if side not in [BallSide.LEFT, BallSide.RIGHT]:
            logger.error(f"Invalid side: {side}")
            return False

        self.is_monitoring = True
        self.last_ball_side = side

        try:
            # Send high-speed monitoring command to Arduino
            # Format: HL (left) or HR (right)
            command = f"H{side.value[0].upper()}\n"

            logger.info(f"Sending high-speed monitoring command: {command.strip()}")
            self.serial.serial.write(command.encode())

            # Arduino will now monitor for 4 seconds and stream data
            # Monitor the serial output for ball detection
            start_time = time.time()
            timeout = self.monitoring_duration + 1.0  # Add 1 second buffer

            ball_detected = False
            distance_readings = []

            while time.time() - start_time < timeout:
                if self.serial.serial.in_waiting > 0:
                    try:
                        line = self.serial.serial.readline().decode('utf-8', errors='ignore').strip()

                        # Check for ball detection message
                        if "BALL_DETECTED" in line:
                            ball_detected = True
                            logger.info(f"Ball crossing detected by Arduino! {line}")
                            break

                        # Parse distance data for logging
                        if line.startswith("D:"):
                            try:
                                parts = line.split(',')
                                distance_str = parts[0].split(':')[1]
                                distance = float(distance_str)
                                distance_readings.append(distance)
                                logger.debug(f"Distance: {distance:.2f} cm")
                            except (ValueError, IndexError):
                                pass

                        # Check for completion (OK response)
                        if line == "OK":
                            logger.info("Monitoring completed without ball detection")
                            break

                    except UnicodeDecodeError:
                        pass

                time.sleep(0.01)  # Small delay to avoid busy-waiting

            # Log statistics
            if distance_readings:
                avg_distance = sum(distance_readings) / len(distance_readings)
                min_distance = min(distance_readings)
                max_distance = max(distance_readings)
                logger.info(
                    f"Monitoring stats: {len(distance_readings)} readings, "
                    f"avg: {avg_distance:.2f} cm, "
                    f"range: {min_distance:.2f}-{max_distance:.2f} cm"
                )

            self.blocking_active = ball_detected

            # Wait for servo to complete blocking motion if detected
            if ball_detected:
                time.sleep(2.5)  # Servo holds for 2 seconds, add buffer
                self.blocking_active = False

            return ball_detected

        except Exception as e:
            logger.error(f"Failed to trigger blocking: {e}")
            return False

        finally:
            self.is_monitoring = False

    def get_statistics(self) -> dict:
        """
        Get blocking statistics.

        Returns:
            Dictionary with statistics
        """
        success_rate = 0.0
        if self.total_detections > 0:
            success_rate = (self.successful_blocks / self.total_detections) * 100

        return {
            "total_detections": self.total_detections,
            "successful_blocks": self.successful_blocks,
            "failed_blocks": self.failed_blocks,
            "success_rate": success_rate,
            "is_monitoring": self.is_monitoring,
            "blocking_active": self.blocking_active,
            "last_side": self.last_ball_side.value
        }

    def reset_statistics(self):
        """Reset statistics counters."""
        self.total_detections = 0
        self.successful_blocks = 0
        self.failed_blocks = 0
        logger.info("Statistics reset")

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Ball blocker cleanup")
        # Reset any active states
        self.is_monitoring = False
        self.blocking_active = False
