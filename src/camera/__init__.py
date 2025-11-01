"""Camera module for RaspberryPi Camera Module 3 control"""

import os
import logging

logger = logging.getLogger(__name__)

# Use mock camera for testing/development if MOCK_CAMERA environment variable is set
if os.environ.get('MOCK_CAMERA', '').lower() in ('1', 'true', 'yes'):
    from .camera_controller_mock import MockCameraController as CameraController
    logger.info("Using MockCameraController (MOCK_CAMERA enabled)")
else:
    # Try controllers in order of preference:
    # 1. libcamera-vid CLI (compatible with Python 3.9, works with Camera Module 3)
    # 2. picamera2 (requires libcamera Python bindings, Python 3.13+)
    # 3. Mock controller (fallback)
    try:
        from .camera_controller_libcamera_cli import CameraControllerLibcameraCLI as CameraController
        logger.info("Using CameraControllerLibcameraCLI (libcamera-vid subprocess)")
    except ImportError as e1:
        try:
            from .camera_controller import CameraController
            logger.info("Using CameraController (picamera2)")
        except ImportError as e2:
            # Fallback to mock if real camera unavailable
            from .camera_controller_mock import MockCameraController as CameraController
            logger.warning("Using MockCameraController (fallback)")

__all__ = ["CameraController"]
