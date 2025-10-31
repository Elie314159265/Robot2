"""
Camera Controller for RaspberryPi Camera Module 3
Uses picamera2 library for image capture and processing.

Target: 30 FPS @ 640x480 resolution
"""

import numpy as np
import logging
from typing import Optional, Tuple
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Picamera2 with graceful fallback for missing GUI dependencies
try:
    from picamera2 import Picamera2
    try:
        from picamera2 import Preview
        PREVIEW_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        PREVIEW_AVAILABLE = False
        logger.warning("Preview module not available (pykms not installed)")
except ImportError as e:
    logger.error(f"Failed to import Picamera2: {e}")
    raise

try:
    from picamera2.encoders import JpegEncoder
    from picamera2.outputs import FileOutput
except ImportError:
    pass

import io


class CameraController:
    """
    Manages RaspberryPi Camera Module 3 operations.

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
        debug: bool = False
    ):
        """
        Initialize camera controller.

        Args:
            resolution: (width, height) tuple. Default: (640, 480)
            framerate: Target FPS. Default: 30
            sensor_mode: libcamera sensor mode (0=auto). Default: 0
            debug: Enable debug logging. Default: False
        """
        self.resolution = resolution
        self.framerate = framerate
        self.sensor_mode = sensor_mode
        self.debug = debug

        self.picam2: Optional[Picamera2] = None
        self.is_running = False
        self.frame_count = 0
        self.last_fps_check = datetime.now()

        if debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(f"CameraController initialized with resolution={resolution}, fps={framerate}")

    def initialize(self) -> bool:
        """
        Initialize and configure the camera.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Initializing camera...")
            self.picam2 = Picamera2()

            # Configure main stream
            config = self.picam2.create_preview_configuration(
                main={
                    "format": "RGB888",
                    "size": self.resolution
                },
                controls={
                    "FrameRate": self.framerate
                }
            )

            self.picam2.configure(config)
            logger.info(f"Camera configured: {self.resolution} @ {self.framerate} FPS")

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
            if self.picam2 is None:
                logger.error("Camera not initialized. Call initialize() first.")
                return False

            self.picam2.start()
            self.is_running = True
            self.frame_count = 0
            self.last_fps_check = datetime.now()

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
            if self.picam2 is None:
                return False

            if self.is_running:
                self.picam2.stop()
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

            request = self.picam2.capture_request()
            frame = request.make_array("main")
            request.release()

            self.frame_count += 1

            # Log FPS every 30 frames
            if self.frame_count % 30 == 0:
                current_time = datetime.now()
                elapsed = (current_time - self.last_fps_check).total_seconds()
                actual_fps = 30 / elapsed if elapsed > 0 else 0

                if self.debug:
                    logger.debug(f"FPS: {actual_fps:.1f} (frame #{self.frame_count})")

                self.last_fps_check = current_time

            return frame

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
            if not self.is_running:
                logger.warning("Camera not running")
                return False

            request = self.picam2.capture_request()
            request.save("main", filepath)
            request.release()

            logger.info(f"JPEG saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save JPEG: {e}")
            return False

    def get_camera_info(self) -> dict:
        """
        Get camera information and capabilities.

        Returns:
            Dictionary with camera properties
        """
        if self.picam2 is None:
            return {"error": "Camera not initialized"}

        try:
            properties = self.picam2.camera_properties
            return {
                "resolution": self.resolution,
                "framerate": self.framerate,
                "frame_count": self.frame_count,
                "is_running": self.is_running,
                "camera_properties": str(properties),
                "sensor_modes": self.picam2.sensor_modes if hasattr(self.picam2, 'sensor_modes') else "N/A"
            }

        except Exception as e:
            logger.error(f"Failed to get camera info: {e}")
            return {"error": str(e)}

    def cleanup(self) -> None:
        """Clean up camera resources"""
        self.stop()
        if self.picam2 is not None:
            try:
                self.picam2.close()
                logger.info("Camera closed")
            except Exception as e:
                logger.error(f"Error closing camera: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
