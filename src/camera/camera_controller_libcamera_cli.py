"""
Camera Controller for RaspberryPi Camera Module 3 (libcamera-vid CLI version)
Uses libcamera-vid subprocess for Python 3.9 compatibility.

This version wraps the libcamera-vid command-line tool, avoiding the need
for libcamera Python bindings while still accessing the camera.
Target: 30 FPS @ 640x480 resolution
"""

import cv2
import numpy as np
import logging
import subprocess
import threading
import queue
from typing import Optional, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class CameraControllerLibcameraCLI:
    """
    Manages RaspberryPi Camera Module 3 operations using libcamera-vid CLI.

    This controller wraps libcamera-vid subprocess, making it compatible with
    Python 3.9 without requiring libcamera Python bindings.

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
        self.camera_cmd: Optional[str] = None  # Will be set in initialize()

        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.frame_count = 0
        self.last_fps_check = datetime.now()

        # Frame buffer
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.capture_thread: Optional[threading.Thread] = None
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

        if debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(
                f"CameraControllerLibcameraCLI initialized: "
                f"resolution={resolution}, fps={framerate}"
            )

    def initialize(self) -> bool:
        """
        Initialize and configure the camera.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Checking rpicam-vid/libcamera-vid availability...")

            # Check if rpicam-vid or libcamera-vid is available
            # (rpicam-vid is the new name in recent Raspberry Pi OS)
            self.camera_cmd = None
            for cmd in ["rpicam-vid", "libcamera-vid"]:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.camera_cmd = cmd
                    break

            if self.camera_cmd is None:
                logger.error("rpicam-vid/libcamera-vid not found. Install with: sudo apt install rpicam-apps")
                return False

            logger.info(f"✅ {self.camera_cmd} found")
            logger.info(f"Camera will be configured: {self.resolution} @ {self.framerate} FPS")

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
            if self.is_running:
                logger.warning("Camera already running")
                return True

            width, height = self.resolution

            # Build rpicam-vid/libcamera-vid command
            # Output raw YUV420 frames to stdout
            cmd = [
                self.camera_cmd,
                "--width", str(width),
                "--height", str(height),
                "--framerate", str(self.framerate),
                "-t", "0",  # Run indefinitely (0 = infinite)
                "--codec", "yuv420",  # Raw YUV output
                "-o", "-",  # Output to stdout
                "-n",  # No preview window
                "--flush",  # Flush output immediately
            ]

            if self.debug:
                logger.debug(f"Starting libcamera-vid: {' '.join(cmd)}")

            # Start subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )

            # Start capture thread
            self.is_running = True
            self.frame_count = 0
            self.last_fps_check = datetime.now()

            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True
            )
            self.capture_thread.start()

            # Wait for first frame
            time.sleep(2)

            logger.info("Camera started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            self.is_running = False
            if self.process:
                self.process.terminate()
            return False

    def _capture_loop(self):
        """Background thread to capture frames from libcamera-vid"""
        try:
            width, height = self.resolution
            frame_size = width * height * 3 // 2  # YUV420 size

            logger.info(f"Capture loop started: expecting {frame_size} bytes per frame")

            frame_index = 0
            while self.is_running and self.process:
                # Check if process is still alive
                if self.process.poll() is not None:
                    logger.error(f"rpicam-vid process died! Return code: {self.process.poll()}")
                    # Log stderr
                    try:
                        stderr_output = self.process.stderr.read().decode('utf-8', errors='ignore')
                        logger.error(f"rpicam-vid stderr: {stderr_output}")
                    except:
                        pass
                    break

                # Read YUV420 frame from stdout
                yuv_data = self.process.stdout.read(frame_size)

                if len(yuv_data) != frame_size:
                    logger.warning(f"Incomplete frame: {len(yuv_data)}/{frame_size}")
                    if len(yuv_data) == 0:
                        logger.error("No data from rpicam-vid stdout!")
                        break
                    continue

                frame_index += 1
                if frame_index == 1:
                    logger.info(f"✅ First frame received: {len(yuv_data)} bytes")

                # Convert YUV420 to RGB
                try:
                    yuv = np.frombuffer(yuv_data, dtype=np.uint8)
                    yuv = yuv.reshape((height * 3 // 2, width))

                    # Convert to BGR first (OpenCV uses BGR)
                    bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

                    # Convert to RGB (to match picamera2 API)
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

                    # Update latest frame
                    with self.frame_lock:
                        self.latest_frame = rgb

                except Exception as e:
                    if self.debug:
                        logger.debug(f"Frame conversion error: {e}")

        except Exception as e:
            logger.error(f"Capture loop error: {e}")
        finally:
            logger.info("Capture loop ended")

    def stop(self) -> bool:
        """
        Stop camera streaming.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_running:
                return True

            self.is_running = False

            # Wait for capture thread to finish
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=2)

            # Terminate subprocess
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                self.process = None

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

            # Get latest frame from buffer
            with self.frame_lock:
                if self.latest_frame is None:
                    return None
                frame = self.latest_frame.copy()

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
            frame = self.capture_frame()
            if frame is None:
                return False

            # Convert RGB to BGR for OpenCV
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
        return {
            "resolution": self.resolution,
            "framerate": self.framerate,
            "frame_count": self.frame_count,
            "is_running": self.is_running,
            "backend": "libcamera-vid (CLI)",
            "process_alive": self.process.poll() is None if self.process else False,
        }

    def cleanup(self) -> None:
        """Clean up camera resources"""
        self.stop()
        logger.info("Camera cleanup complete")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


# Alias for compatibility
CameraController = CameraControllerLibcameraCLI
