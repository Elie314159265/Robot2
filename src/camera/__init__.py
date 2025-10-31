"""Camera module for RaspberryPi Camera Module 3 control"""

import os

# Use mock camera for testing/development if MOCK_CAMERA environment variable is set
if os.environ.get('MOCK_CAMERA', '').lower() in ('1', 'true', 'yes'):
    from .camera_controller_mock import MockCameraController as CameraController
else:
    try:
        from .camera_controller import CameraController
    except ImportError:
        # Fallback to mock if real camera unavailable
        from .camera_controller_mock import MockCameraController as CameraController

__all__ = ["CameraController"]
