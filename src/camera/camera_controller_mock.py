"""
Mock Camera Controller for testing without actual hardware
Provides the same interface as CameraController but returns synthetic frames
"""

import numpy as np
import logging
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MockCameraController:
    """
    Mock camera controller that simulates camera operation without hardware

    Useful for:
    - Testing on non-RaspberryPi systems
    - Development without camera attached
    - CI/CD pipelines
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (640, 480),
        framerate: int = 30,
        debug: bool = False
    ):
        """
        Initialize mock camera controller.

        Args:
            resolution: (width, height) tuple
            framerate: Target FPS
            debug: Enable debug logging
        """
        self.resolution = resolution
        self.framerate = framerate
        self.debug = debug
        self.is_running = False
        self.frame_count = 0
        self.last_fps_check = datetime.now()

    def initialize(self) -> bool:
        """Initialize mock camera"""
        logger.info("Mock camera initialized")
        return True

    def start(self) -> bool:
        """Start mock camera"""
        self.is_running = True
        self.frame_count = 0
        self.last_fps_check = datetime.now()
        logger.info("Mock camera started")
        return True

    def stop(self) -> bool:
        """Stop mock camera"""
        self.is_running = False
        logger.info("Mock camera stopped")
        return True

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture synthetic frame

        Returns:
            Fake frame with some noise pattern
        """
        if not self.is_running:
            return None

        # Generate synthetic frame
        height, width = self.resolution[1], self.resolution[0]
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Add some pattern/noise
        frame[:, :, 0] = np.random.randint(50, 100, (height, width))  # R channel
        frame[:, :, 1] = np.random.randint(100, 150, (height, width))  # G channel
        frame[:, :, 2] = np.random.randint(150, 200, (height, width))  # B channel

        self.frame_count += 1

        if self.frame_count % 30 == 0 and self.debug:
            current_time = datetime.now()
            elapsed = (current_time - self.last_fps_check).total_seconds()
            actual_fps = 30 / elapsed if elapsed > 0 else 0
            logger.debug(f"Mock FPS: {actual_fps:.1f}")
            self.last_fps_check = current_time

        return frame

    def get_camera_info(self) -> dict:
        """Get mock camera info"""
        return {
            "resolution": self.resolution,
            "framerate": self.framerate,
            "frame_count": self.frame_count,
            "is_running": self.is_running,
            "type": "Mock",
        }

    def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop()

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
