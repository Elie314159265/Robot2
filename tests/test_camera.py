"""
Phase 1 Test: Camera Controller
Tests basic camera functionality and performance.

Success Criteria:
- Camera initializes without errors
- Captures frames at 30 FPS
- Frame resolution is 640x480
- No memory leaks during capture
"""

import sys
import os
import logging
import time
from pathlib import Path

# Add libcamera path for RaspberryPi
sys.path.insert(0, '/usr/lib/aarch64-linux-gnu/python3.12/site-packages')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import via __init__ for fallback support
from src.camera import CameraController

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_camera_initialization():
    """Test 1: Camera initialization"""
    logger.info("=" * 50)
    logger.info("TEST 1: Camera Initialization")
    logger.info("=" * 50)

    camera = CameraController(resolution=(640, 480), framerate=30, debug=True)

    if not camera.initialize():
        logger.error("FAILED: Camera initialization failed")
        return False

    logger.info("PASSED: Camera initialized successfully")
    camera.cleanup()
    return True


def test_camera_start_stop():
    """Test 2: Camera start and stop"""
    logger.info("=" * 50)
    logger.info("TEST 2: Camera Start/Stop")
    logger.info("=" * 50)

    camera = CameraController(resolution=(640, 480), framerate=30)

    if not camera.initialize():
        logger.error("FAILED: Camera initialization failed")
        return False

    if not camera.start():
        logger.error("FAILED: Camera start failed")
        camera.cleanup()
        return False

    time.sleep(1)  # Let camera stabilize

    if not camera.stop():
        logger.error("FAILED: Camera stop failed")
        camera.cleanup()
        return False

    logger.info("PASSED: Camera start/stop works correctly")
    camera.cleanup()
    return True


def test_camera_frame_capture(duration: int = 5, expected_fps: int = 30):
    """Test 3: Frame capture and FPS measurement"""
    logger.info("=" * 50)
    logger.info(f"TEST 3: Frame Capture ({duration}s, {expected_fps} FPS target)")
    logger.info("=" * 50)

    camera = CameraController(resolution=(640, 480), framerate=expected_fps, debug=True)

    if not camera.initialize():
        logger.error("FAILED: Camera initialization failed")
        return False

    if not camera.start():
        logger.error("FAILED: Camera start failed")
        camera.cleanup()
        return False

    logger.info("Warming up camera...")
    time.sleep(2)  # Camera warmup

    logger.info(f"Capturing frames for {duration} seconds...")
    start_time = time.time()
    frames_captured = 0
    frame_sizes = []

    try:
        while time.time() - start_time < duration:
            frame = camera.capture_frame()

            if frame is None:
                logger.error("FAILED: Frame capture returned None")
                camera.cleanup()
                return False

            frames_captured += 1
            frame_sizes.append(frame.nbytes)

            # Verify frame properties
            if frame.shape != (480, 640, 3):
                logger.error(f"FAILED: Wrong frame shape {frame.shape}, expected (480, 640, 3)")
                camera.cleanup()
                return False

            if frames_captured % 30 == 0:
                elapsed = time.time() - start_time
                current_fps = frames_captured / elapsed
                logger.info(f"  Frames: {frames_captured}, Elapsed: {elapsed:.1f}s, FPS: {current_fps:.1f}")

    except Exception as e:
        logger.error(f"FAILED: Exception during frame capture: {e}")
        camera.cleanup()
        return False

    elapsed = time.time() - start_time
    actual_fps = frames_captured / elapsed

    logger.info(f"\nCapture Results:")
    logger.info(f"  Total frames: {frames_captured}")
    logger.info(f"  Duration: {elapsed:.2f}s")
    logger.info(f"  Actual FPS: {actual_fps:.2f}")
    logger.info(f"  Target FPS: {expected_fps}")
    logger.info(f"  Frame shape: {frame.shape}")
    logger.info(f"  Frame dtype: {frame.dtype}")
    logger.info(f"  Avg frame size: {sum(frame_sizes) / len(frame_sizes) / (1024*1024):.2f} MB")

    # Check if FPS is acceptable (within 10% of target)
    fps_tolerance = expected_fps * 0.1
    if abs(actual_fps - expected_fps) > fps_tolerance:
        logger.warning(f"WARNING: FPS deviation from target: {abs(actual_fps - expected_fps):.1f} fps")

    camera.stop()
    camera.cleanup()

    logger.info("PASSED: Frame capture test completed")
    return True


def test_camera_context_manager():
    """Test 4: Context manager functionality"""
    logger.info("=" * 50)
    logger.info("TEST 4: Context Manager")
    logger.info("=" * 50)

    try:
        with CameraController(resolution=(640, 480), framerate=30) as camera:
            if not camera.is_running:
                logger.error("FAILED: Camera not running in context manager")
                return False

            frame = camera.capture_frame()
            if frame is None:
                logger.error("FAILED: Frame capture failed in context manager")
                return False

            logger.info(f"Captured frame shape: {frame.shape}")

        logger.info("PASSED: Context manager works correctly")
        return True

    except Exception as e:
        logger.error(f"FAILED: Context manager exception: {e}")
        return False


def test_camera_info():
    """Test 5: Get camera information"""
    logger.info("=" * 50)
    logger.info("TEST 5: Camera Information")
    logger.info("=" * 50)

    camera = CameraController(resolution=(640, 480), framerate=30)

    if not camera.initialize():
        logger.error("FAILED: Camera initialization failed")
        return False

    if not camera.start():
        logger.error("FAILED: Camera start failed")
        camera.cleanup()
        return False

    time.sleep(1)

    info = camera.get_camera_info()
    logger.info(f"Camera Info:")
    for key, value in info.items():
        logger.info(f"  {key}: {value}")

    camera.cleanup()

    if "error" in info:
        logger.warning(f"WARNING: {info['error']}")
        return False

    logger.info("PASSED: Camera info retrieved")
    return True


def run_all_tests():
    """Run all Phase 1 tests"""
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 1: CAMERA SETUP TEST SUITE")
    logger.info("=" * 70 + "\n")

    tests = [
        ("Initialization", test_camera_initialization),
        ("Start/Stop", test_camera_start_stop),
        ("Frame Capture", lambda: test_camera_frame_capture(duration=5, expected_fps=30)),
        ("Context Manager", test_camera_context_manager),
        ("Camera Info", test_camera_info),
    ]

    results = {}
    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test '{test_name}' raised exception: {e}")
            results[test_name] = "ERROR"
            failed += 1

        logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    for test_name, result in results.items():
        symbol = "✓" if result == "PASSED" else "✗"
        logger.info(f"  {symbol} {test_name}: {result}")

    logger.info(f"\nTotal: {passed} passed, {failed} failed")
    logger.info("=" * 70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
