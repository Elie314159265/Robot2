"""
Camera Controller for RaspberryPi Camera Module 3 (v4l2/OpenCV version)
Uses OpenCV VideoCapture with v4l2 backend for Python 3.9 compatibility.

This version is compatible with Python 3.9 and does not require libcamera Python bindings.
Target: 30 FPS @ 640x480 resolution
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class CameraControllerV4L2:
    """
    Manages RaspberryPi Camera Module 3 operations using v4l2/OpenCV.

    This controller uses OpenCV's VideoCapture with v4l2 backend, making it
    compatible with Python 3.9 without requiring libcamera Python bindings.

    Features:
    - Video streaming at 30 FPS
    - Frame capture and processing
    - Resolution and framerate configuration
    - Performance monitoring
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (640, 480),
        framerate: int = 30,
        sensor_mode: int = 0,
        debug: bool = False,
        device: str = "/dev/video0"
    ):
        """
        Initialize camera controller.

        Args:
            resolution: (width, height) tuple. Default: (640, 480)
            framerate: Target FPS. Default: 30
            sensor_mode: Unused for v4l2 (kept for API compatibility)
            debug: Enable debug logging. Default: False
            device: v4l2 device path. Default: /dev/video0
        """
        self.resolution = resolution
        self.framerate = framerate
        self.sensor_mode = sensor_mode
        self.debug = debug
        self.device = device

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_count = 0
        self.last_fps_check = datetime.now()

        if debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(
                f"CameraControllerV4L2 initialized: resolution={resolution}, "
                f"fps={framerate}, device={device}"
            )

    def initialize(self) -> bool:
        """
        Initialize and configure the camera.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Initializing camera on {self.device}...")

            # Check if device exists
            if not os.path.exists(self.device):
                logger.error(f"Camera device {self.device} not found")
                return False

            # Open video capture with v4l2 backend
            self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                logger.error(f"Failed to open {self.device}")
                return False

            # Configure camera properties
            width, height = self.resolution

            # Set FOURCC format to MJPEG for better performance
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

            # Set framerate
            self.cap.set(cv2.CAP_PROP_FPS, self.framerate)

            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))

            logger.info(
                f"Camera configured: {actual_width}x{actual_height} @ {actual_fps} FPS"
            )

            if (actual_width, actual_height) != self.resolution:
                logger.warning(
                    f"Requested {self.resolution} but got "
                    f"{actual_width}x{actual_height}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def start(self) -> bool:
        """
        Start camera streaming.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.cap is None or not self.cap.isOpened():
                logger.error("Camera not initialized. Call initialize() first.")
                return False

            # v4l2 camera is already "started" when opened
            self.is_running = True
            self.frame_count = 0
            self.last_fps_check = datetime.now()

            # Warm-up: capture and discard a few frames
            for _ in range(5):
                self.cap.read()

            logger.info("Camera started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop camera streaming.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.is_running:
                self.is_running = False
                logger.info("Camera stopped")

            return True

        except Exception as e:
            logger.error(f"Failed to stop camera: {e}")
            return False

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from the camera.

        Returns:
            numpy array (RGB888, shape: height x width x 3) or None on error
        """
        try:
            if not self.is_running:
                logger.warning("Camera not running. Call start() first.")
                return None

            ret, frame = self.cap.read()

            if not ret or frame is None:
                logger.warning("Failed to read frame")
                return None

            # Convert BGR (OpenCV default) to RGB (picamera2 format)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            self.frame_count += 1

            # Log FPS every 30 frames
            if self.frame_count % 30 == 0:
                current_time = datetime.now()
                elapsed = (current_time - self.last_fps_check).total_seconds()
                actual_fps = 30 / elapsed if elapsed > 0 else 0

                if self.debug:
                    logger.debug(f"FPS: {actual_fps:.1f} (frame #{self.frame_count})")

                self.last_fps_check = current_time

            return frame_rgb

        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return None

    def capture_jpeg(self, filepath: str) -> bool:
        """
        Capture a frame and save as JPEG.

        Args:
            filepath: Path to save JPEG file

        Returns:
            True if successful, False otherwise
        """
        try:
            frame = self.capture_frame()
            if frame is None:
                return False

            # Convert RGB back to BGR for OpenCV imwrite
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            success = cv2.imwrite(filepath, frame_bgr)

            if success:
                logger.info(f"JPEG saved to {filepath}")
            else:
                logger.error(f"Failed to write JPEG to {filepath}")

            return success

        except Exception as e:
            logger.error(f"Failed to save JPEG: {e}")
            return False

    def get_camera_info(self) -> dict:
        """
        Get camera information and capabilities.

        Returns:
            Dictionary with camera properties
        """
        if self.cap is None:
            return {"error": "Camera not initialized"}

        try:
            return {
                "resolution": self.resolution,
                "framerate": self.framerate,
                "frame_count": self.frame_count,
                "is_running": self.is_running,
                "device": self.device,
                "backend": "v4l2 (OpenCV)",
                "actual_width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "actual_height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "actual_fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
            }

        except Exception as e:
            logger.error(f"Failed to get camera info: {e}")
            return {"error": str(e)}

    def cleanup(self) -> None:
        """Clean up camera resources"""
        self.stop()
        if self.cap is not None:
            try:
                self.cap.release()
                logger.info("Camera released")
            except Exception as e:
                logger.error(f"Error releasing camera: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


# Alias for compatibility
CameraController = CameraControllerV4L2
