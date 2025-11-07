#!/usr/bin/env python3
"""
Ball Blocking System Simple Test
Tests the new high-speed ultrasonic ball blocking system

Test scenarios:
1. Manual trigger test - manually trigger left/right blocking
2. Ultrasonic sensor test - test left and right sensors individually
3. Ball side detection test - test position-to-side mapping logic

Usage:
    python3 tests/test_ball_blocking_simple.py --test manual
    python3 tests/test_ball_blocking_simple.py --test ultrasonic
    python3 tests/test_ball_blocking_simple.py --test sides
"""

import sys
import time
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.arduino.serial_controller import SerialController
from src.blocking.ball_blocker import BallBlocker, BallSide

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_manual_trigger(serial_controller: SerialController):
    """
    Test manual triggering of ball blocking system

    Args:
        serial_controller: Connected SerialController instance
    """
    print("\n" + "="*70)
    print("Manual Trigger Test - High-Speed Ultrasonic Ball Blocking")
    print("="*70)
    print("\nThis test will manually trigger the Arduino's high-speed monitoring.")
    print("The Arduino will:")
    print("  1. Monitor ultrasonic sensor for 4 seconds at ~50Hz")
    print("  2. Detect ball crossing via distance change (>10cm threshold)")
    print("  3. Raise servo automatically on detection")
    print()
    print("To test, wave your hand in front of the sensor during monitoring!")
    print()

    blocker = BallBlocker(serial_controller)

    # Test left side
    input("Press Enter to test LEFT side (pins 8,9 sensor -> servo 7)...")
    print("\nTriggering left side monitoring for 4 seconds...")
    print("Wave your hand in front of the LEFT sensor now!")

    start_time = time.time()
    success = blocker.trigger_blocking(BallSide.LEFT)
    elapsed = time.time() - start_time

    print(f"\nMonitoring completed in {elapsed:.1f} seconds")
    if success:
        print("✓ Ball crossing detected! Servo 7 was raised.")
    else:
        print("✗ No ball crossing detected (no significant distance change)")

    time.sleep(2)

    # Test right side
    input("\nPress Enter to test RIGHT side (pins 10,11 sensor -> servo 5)...")
    print("\nTriggering right side monitoring for 4 seconds...")
    print("Wave your hand in front of the RIGHT sensor now!")

    start_time = time.time()
    success = blocker.trigger_blocking(BallSide.RIGHT)
    elapsed = time.time() - start_time

    print(f"\nMonitoring completed in {elapsed:.1f} seconds")
    if success:
        print("✓ Ball crossing detected! Servo 5 was raised.")
    else:
        print("✗ No ball crossing detected (no significant distance change)")

    # Show statistics
    stats = blocker.get_statistics()
    print("\n" + "-"*70)
    print("Test Statistics:")
    print(f"  Total detections: {stats['total_detections']}")
    print(f"  Successful blocks: {stats['successful_blocks']}")
    print(f"  Failed blocks: {stats['failed_blocks']}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    print("-"*70)


def test_ball_side_detection():
    """
    Test ball side detection logic without Arduino
    """
    print("\n" + "="*70)
    print("Ball Side Detection Test")
    print("="*70)
    print("\nTesting ball position to side mapping logic...")
    print()

    # Create blocker with dummy serial (won't be used)
    class DummySerial:
        pass

    blocker = BallBlocker(
        DummySerial(),
        left_threshold=0.3,
        right_threshold=0.7
    )

    # Test various positions
    frame_width = 640
    test_positions = [
        (50, "LEFT"),     # Far left
        (150, "LEFT"),    # Left region
        (192, "LEFT"),    # Left threshold boundary
        (320, "CENTER"),  # Center
        (448, "RIGHT"),   # Right threshold boundary
        (500, "RIGHT"),   # Right region
        (590, "RIGHT"),   # Far right
    ]

    print(f"Frame width: {frame_width}px")
    print(f"Left threshold: {blocker.left_threshold} (<{int(blocker.left_threshold * frame_width)}px)")
    print(f"Right threshold: {blocker.right_threshold} (>{int(blocker.right_threshold * frame_width)}px)")
    print(f"Center region: {int(blocker.left_threshold * frame_width)}px - {int(blocker.right_threshold * frame_width)}px")
    print()

    print("Position tests:")
    for x_pos, expected_side in test_positions:
        detected_side = blocker.determine_ball_side(x_pos, frame_width)
        normalized = x_pos / frame_width
        match = "✓" if detected_side.value.upper() == expected_side else "✗"
        print(f"  {match} X={x_pos:3d}px ({normalized:.3f}) -> {detected_side.value.upper():6s} (expected: {expected_side})")


def test_ultrasonic_sensors(serial_controller: SerialController):
    """
    Test ultrasonic sensors individually

    Args:
        serial_controller: Connected SerialController instance
    """
    print("\n" + "="*70)
    print("Ultrasonic Sensors Test")
    print("="*70)
    print("\nTesting left and right ultrasonic sensors individually...")
    print("Hardware mapping:")
    print("  - Left sensor: pins 8 (TRIG), 9 (ECHO)")
    print("  - Right sensor: pins 10 (TRIG), 11 (ECHO)")
    print()
    print("Move your hand in front of each sensor to see distance readings.")
    print("Press Ctrl+C to stop.\n")

    try:
        for i in range(30):
            # Read left sensor
            dist_left = serial_controller.read_distance_left()
            left_str = f"{dist_left:6.1f} cm" if dist_left and dist_left > 0 else "  ERROR  "

            # Small delay between sensor reads
            time.sleep(0.05)

            # Read right sensor
            dist_right = serial_controller.read_distance_right()
            right_str = f"{dist_right:6.1f} cm" if dist_right and dist_right > 0 else "  ERROR  "

            print(f"[{i+1:2d}] Left (8,9): {left_str} | Right (10,11): {right_str}")
            time.sleep(0.4)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")


def test_complete_workflow(serial_controller: SerialController):
    """
    Test complete workflow: simulate camera detection -> trigger blocking

    Args:
        serial_controller: Connected SerialController instance
    """
    print("\n" + "="*70)
    print("Complete Workflow Test")
    print("="*70)
    print("\nThis test simulates the complete ball blocking workflow:")
    print("  1. Simulate camera detecting ball at position")
    print("  2. Determine side (left/right)")
    print("  3. Trigger high-speed ultrasonic monitoring")
    print("  4. Arduino detects crossing and blocks")
    print()

    blocker = BallBlocker(serial_controller)

    # Simulate ball detection on left side
    print("Simulating ball detection on LEFT side (x=150, width=640)...")
    print("Wave your hand in front of LEFT sensor during monitoring!")
    input("Press Enter to start...")

    success = blocker.process_ball_detection(
        ball_x=150,
        ball_y=240,
        frame_width=640,
        frame_height=480,
        confidence=0.85
    )

    if success:
        print("\n✓ Complete workflow successful on LEFT side!")
    else:
        print("\n✗ Workflow failed or no crossing detected")

    time.sleep(3)

    # Simulate ball detection on right side
    print("\nSimulating ball detection on RIGHT side (x=500, width=640)...")
    print("Wave your hand in front of RIGHT sensor during monitoring!")
    input("Press Enter to start...")

    success = blocker.process_ball_detection(
        ball_x=500,
        ball_y=240,
        frame_width=640,
        frame_height=480,
        confidence=0.90
    )

    if success:
        print("\n✓ Complete workflow successful on RIGHT side!")
    else:
        print("\n✗ Workflow failed or no crossing detected")

    # Show final statistics
    stats = blocker.get_statistics()
    print("\n" + "-"*70)
    print("Final Statistics:")
    print(f"  Total detections: {stats['total_detections']}")
    print(f"  Successful blocks: {stats['successful_blocks']}")
    print(f"  Failed blocks: {stats['failed_blocks']}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    print("-"*70)


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(
        description='Ball Blocking System Test',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--test',
        choices=['manual', 'sides', 'ultrasonic', 'workflow', 'all'],
        default='all',
        help='Which test to run (default: all)'
    )
    parser.add_argument(
        '--port',
        type=str,
        default='/dev/ttyACM0',
        help='Arduino serial port (default: /dev/ttyACM0)'
    )

    args = parser.parse_args()

    print("="*70)
    print("Ball Blocking System Test - High-Speed Ultrasonic")
    print("="*70)
    print(f"Arduino port: {args.port}")
    print(f"Test mode: {args.test}")
    print()

    # Run tests that don't need Arduino first
    if args.test in ['sides', 'all']:
        test_ball_side_detection()

    # Connect to Arduino for tests that need it
    needs_arduino = args.test in ['manual', 'ultrasonic', 'workflow', 'all']

    if needs_arduino:
        print("\nConnecting to Arduino...")
        serial = SerialController(port=args.port)

        if not serial.connect():
            print("\n" + "="*70)
            print("ERROR: Failed to connect to Arduino")
            print("="*70)
            print("Please check:")
            print("  1. Arduino is connected to USB")
            print("  2. Correct port specified (current: {})".format(args.port))
            print("  3. Arduino firmware is uploaded")
            print("  4. User has permission to access serial port")
            print("\nTry: sudo usermod -a -G dialout $USER")
            print("Then log out and log back in")
            print("="*70)
            sys.exit(1)

        print("✓ Connected to Arduino successfully\n")

        try:
            # Run Arduino-dependent tests
            if args.test in ['manual', 'all']:
                test_manual_trigger(serial)

            if args.test in ['ultrasonic', 'all']:
                test_ultrasonic_sensors(serial)

            if args.test in ['workflow', 'all']:
                test_complete_workflow(serial)

            print("\n" + "="*70)
            print("All tests completed successfully!")
            print("="*70)

        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")

        finally:
            serial.cleanup()
            print("\nArduino connection closed")


if __name__ == "__main__":
    main()
