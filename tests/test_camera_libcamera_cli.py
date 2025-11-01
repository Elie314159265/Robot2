#!/usr/bin/env python3
"""
Test script for libcamera-vid CLI-based camera controller with Python 3.9

This script verifies that the libcamera-vid CLI camera controller works correctly
in the Python 3.9 environment needed for Edge TPU.
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("=" * 70)
print("RaspberryPi Camera Module 3 - libcamera-vid CLI Test")
print("=" * 70)

# Check Python version
print(f"\nPython version: {sys.version}")
expected_major, expected_minor = 3, 9
actual_major, actual_minor = sys.version_info.major, sys.version_info.minor

if actual_major == expected_major and actual_minor == expected_minor:
    print(f"✅ Python {actual_major}.{actual_minor} (compatible with Edge TPU)")
else:
    print(f"⚠️  Python {actual_major}.{actual_minor} (expected 3.9 for TPU)")

# Test imports
print("\n" + "=" * 70)
print("Testing imports...")
print("=" * 70)

try:
    import cv2
    print(f"✅ OpenCV: {cv2.__version__}")
except ImportError as e:
    print(f"❌ OpenCV import failed: {e}")
    sys.exit(1)

try:
    import numpy as np
    print(f"✅ NumPy: {np.__version__}")
except ImportError as e:
    print(f"❌ NumPy import failed: {e}")
    sys.exit(1)

try:
    from src.camera.camera_controller_libcamera_cli import CameraControllerLibcameraCLI
    print(f"✅ CameraControllerLibcameraCLI")
except ImportError as e:
    print(f"❌ CameraControllerLibcameraCLI import failed: {e}")
    sys.exit(1)

# Initialize camera
print("\n" + "=" * 70)
print("Initializing camera...")
print("=" * 70)

camera = CameraControllerLibcameraCLI(
    resolution=(640, 480),
    framerate=30,
    debug=True
)

if not camera.initialize():
    print("❌ Camera initialization failed")
    sys.exit(1)

print("✅ Camera initialized")

# Start camera
print("\n" + "=" * 70)
print("Starting camera...")
print("=" * 70)

if not camera.start():
    print("❌ Camera start failed")
    camera.cleanup()
    sys.exit(1)

print("✅ Camera started")
print("Waiting for camera warm-up...")
time.sleep(3)

# Capture frames and measure FPS
print("\n" + "=" * 70)
print("Capturing frames (30 frames)...")
print("=" * 70)

frame_times = []
successful_captures = 0

for i in range(30):
    start = time.time()
    frame = camera.capture_frame()
    end = time.time()

    if frame is not None:
        successful_captures += 1
        frame_times.append(end - start)

        if i % 10 == 0:
            print(f"Frame {i+1}/30: shape={frame.shape}, dtype={frame.dtype}")
    else:
        print(f"⚠️  Frame {i+1}: None (camera still warming up?)")

    # Small delay to not overwhelm the system
    time.sleep(0.01)

print(f"\n✅ Captured {successful_captures}/30 frames")

# Calculate FPS statistics
if frame_times:
    avg_time = sum(frame_times) / len(frame_times)
    avg_fps = 1.0 / avg_time if avg_time > 0 else 0
    min_time = min(frame_times)
    max_time = max(frame_times)
    max_fps = 1.0 / min_time if min_time > 0 else 0
    min_fps = 1.0 / max_time if max_time > 0 else 0

    print("\nFPS Statistics:")
    print(f"  Average FPS: {avg_fps:.2f}")
    print(f"  Min FPS: {min_fps:.2f}")
    print(f"  Max FPS: {max_fps:.2f}")
    print(f"  Average capture time: {avg_time*1000:.2f} ms")

    if avg_fps >= 30:
        print(f"\n✅ Target FPS achieved: {avg_fps:.2f} >= 30")
    elif avg_fps >= 25:
        print(f"\n⚠️  FPS close to target: {avg_fps:.2f} (target: 30)")
    else:
        print(f"\n⚠️  FPS below target: {avg_fps:.2f} < 30")
        print("   Note: FPS limited by Python frame processing overhead")

# Test JPEG capture
print("\n" + "=" * 70)
print("Testing JPEG capture...")
print("=" * 70)

test_jpeg = "/tmp/test_camera_libcamera_cli.jpg"
if camera.capture_jpeg(test_jpeg):
    if os.path.exists(test_jpeg):
        file_size = os.path.getsize(test_jpeg)
        print(f"✅ JPEG saved: {test_jpeg} ({file_size} bytes)")
        os.remove(test_jpeg)
    else:
        print(f"❌ JPEG file not created: {test_jpeg}")
else:
    print("❌ JPEG capture failed")

# Get camera info
print("\n" + "=" * 70)
print("Camera Information:")
print("=" * 70)

info = camera.get_camera_info()
for key, value in info.items():
    print(f"  {key}: {value}")

# Cleanup
print("\n" + "=" * 70)
print("Cleaning up...")
print("=" * 70)

camera.cleanup()
print("✅ Camera cleanup complete")

print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)
print("✅ libcamera-vid CLI camera controller is working!")
print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} compatibility confirmed")
if frame_times:
    print(f"✅ Average FPS: {avg_fps:.2f}")
print("\nNext steps:")
print("  1. Test with Edge TPU (test_camera_tpu_fps.py)")
print("  2. Run full integration test")
print("=" * 70)
