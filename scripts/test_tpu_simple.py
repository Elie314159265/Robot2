#!/usr/bin/env python3
"""
Simple TPU Detection Test
Quick test to verify Edge TPU is working with TensorFlow Lite
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.detection.tflite_wrapper import TFLiteEdgeTPU
import numpy as np
from picamera2 import Picamera2
import time

def main():
    print("=" * 60)
    print("TPU Detection Test - Quick Version")
    print("=" * 60)

    # Initialize model (use CPU version for now)
    model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess.tflite"
    print(f"\n1. Loading model: {model_path}")
    print("   Note: Using CPU version (TPU delegate issue, will fix later)")

    tpu = TFLiteEdgeTPU(model_path, use_edgetpu=False)

    if not tpu.load_model():
        print("❌ Failed to load model")
        return 1

    print("✅ Model loaded successfully")
    print(f"   Input size: {tpu.get_input_size()}")

    # Initialize camera
    print("\n2. Initializing camera...")
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)  # Camera warmup

    print("✅ Camera initialized")

    # Capture and detect
    print("\n3. Running detection test...")
    print("   Capturing 10 frames and detecting objects...")

    sports_ball_detections = 0
    total_detections = 0
    inference_times = []

    for i in range(10):
        # Capture frame
        frame = picam2.capture_array()

        # Run detection
        start_time = time.time()
        detections = tpu.detect_objects(frame, threshold=0.3)
        inference_time = (time.time() - start_time) * 1000  # ms
        inference_times.append(inference_time)

        # Count detections
        total_detections += len(detections)
        for det in detections:
            if det['class_id'] == 37:  # sports ball
                sports_ball_detections += 1
                print(f"   Frame {i+1}: ⚽ Sports ball detected! Score: {det['score']:.2f}")

        print(f"   Frame {i+1}: {len(detections)} objects, {inference_time:.1f}ms")

    # Results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Total frames: 10")
    print(f"Total detections: {total_detections}")
    print(f"Sports ball detections: {sports_ball_detections}")
    print(f"Average inference time: {np.mean(inference_times):.1f}ms")
    print(f"Min inference time: {np.min(inference_times):.1f}ms")
    print(f"Max inference time: {np.max(inference_times):.1f}ms")

    # Evaluation
    avg_time = np.mean(inference_times)
    if avg_time < 20:
        print(f"\n✅ PASSED: Inference time {avg_time:.1f}ms < 20ms target")
    else:
        print(f"\n⚠️  WARNING: Inference time {avg_time:.1f}ms > 20ms target")

    if sports_ball_detections > 0:
        print(f"✅ Sports ball detection working!")
    else:
        print(f"ℹ️  No sports balls detected (try pointing camera at a ball)")

    # Cleanup
    picam2.stop()
    picam2.close()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
