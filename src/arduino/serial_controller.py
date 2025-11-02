"""
Arduino Serial Controller
Communication with Arduino for servo and sensor control
"""

from typing import Optional
import serial
import logging
import time

logger = logging.getLogger(__name__)


class SerialController:
    """
    Serial communication controller for Arduino

    Features:
    - Send servo commands
    - Receive sensor readings
    - Protocol serialization/deserialization
    """

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 9600,
        timeout: float = 1.0
    ):
        """
        Initialize serial controller.

        Args:
            port: Serial port (e.g., "/dev/ttyACM0", "COM3")
            baudrate: Baud rate
            timeout: Serial timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Connect to Arduino.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for Arduino reset

            # Clear serial buffer (Arduino sends "Arduino initialized" on startup)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # Read and discard startup message
            if self.serial.in_waiting > 0:
                startup_msg = self.serial.readline().decode().strip()
                logger.debug(f"Arduino startup message: {startup_msg}")

            self.is_connected = True
            logger.info(f"Connected to Arduino on {self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Arduino: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Arduino"""
        if self.serial:
            self.serial.close()
            self.is_connected = False
            logger.info("Disconnected from Arduino")

    def send_servo_command(
        self,
        servo_id: int,
        angle: float
    ) -> bool:
        """
        Send servo position command.

        Args:
            servo_id: Servo ID (0-15)
            angle: Target angle in degrees (0-180)

        Returns:
            True if successful
        """
        if not self.is_connected:
            logger.error("Not connected to Arduino")
            return False

        try:
            # Clamp angle to valid range
            angle = max(0, min(180, angle))
            angle_int = int(angle)

            # Format command: S[ID:2][ANGLE:3]
            command = f"S{servo_id:02d}{angle_int:03d}\n"

            self.serial.write(command.encode())

            # Read response
            response = self.serial.readline().decode().strip()

            if response == "OK":
                logger.debug(f"Servo {servo_id} set to {angle_int}°")
                return True
            else:
                logger.error(f"Servo command failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Failed to send servo command: {e}")
            return False

    def read_distance(self) -> Optional[float]:
        """
        Read ultrasonic distance sensor.

        Returns:
            Distance in cm or None on error
        """
        if not self.is_connected:
            logger.error("Not connected to Arduino")
            return None

        try:
            # Send distance read command
            self.serial.write(b"D\n")

            # Read response: D[VALUE:5] (in mm)
            response = self.serial.readline().decode().strip()

            if response.startswith("D") and len(response) == 6:
                distance_mm = int(response[1:])
                distance_cm = distance_mm / 10.0
                logger.debug(f"Distance: {distance_cm:.1f} cm")
                return distance_cm
            else:
                logger.error(f"Invalid distance response: {response}")
                return None

        except Exception as e:
            logger.error(f"Failed to read distance: {e}")
            return None

    def set_pan_tilt(self, pan_angle: float, tilt_angle: float) -> bool:
        """
        Set pan/tilt servos (convenience method for camera tracking).

        Args:
            pan_angle: Pan angle in degrees (0-180)
            tilt_angle: Tilt angle in degrees (0-180)

        Returns:
            True if both servos set successfully
        """
        # Servo 0: Pan, Servo 1: Tilt
        pan_ok = self.send_servo_command(0, pan_angle)
        tilt_ok = self.send_servo_command(1, tilt_angle)
        return pan_ok and tilt_ok

    def cleanup(self) -> None:
        """Clean up serial connection"""
        self.disconnect()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
