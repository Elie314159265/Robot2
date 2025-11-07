#!/usr/bin/env python3
"""
Ball Blocking System Automatic Test
Tests the ball blocking system without user interaction

Usage:
    python3 tests/test_ball_blocking_auto.py
"""

import sys
import time
import logging
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


def test_automatic_trigger(serial_controller: SerialController):
    """
    Automatic test of ball blocking system
    """
    print("\n" + "="*70)
    print("Automatic Ball Blocking Test")
    print("="*70)
    print("\nThis test will automatically trigger both left and right sensors.")
    print("Wave your hand in front of the sensors to test ball detection!")
    print()

    blocker = BallBlocker(serial_controller)

    # Test left side
    print("\n" + "-"*70)
    print("Testing LEFT side (pins 8,9 sensor -> servo 7)")
    print("-"*70)
    print("Arduino will monitor for 4 seconds...")
    print(">>> WAVE YOUR HAND IN FRONT OF THE LEFT SENSOR NOW! <<<")
    print()

    time.sleep(2)  # Give user time to prepare

    start_time = time.time()
    success = blocker.trigger_blocking(BallSide.LEFT)
    elapsed = time.time() - start_time

    print(f"\nMonitoring completed in {elapsed:.1f} seconds")
    if success:
        print("✅ SUCCESS! Ball crossing detected on LEFT side!")
        print("   Servo 7 was raised for 2 seconds")
    else:
        print("⚠️  No ball crossing detected on LEFT side")
        print("   (This is OK if you didn't wave your hand)")

    # Wait between tests
    print("\nWaiting 3 seconds before next test...")
    time.sleep(3)

    # Test right side
    print("\n" + "-"*70)
    print("Testing RIGHT side (pins 10,11 sensor -> servo 5)")
    print("-"*70)
    print("Arduino will monitor for 4 seconds...")
    print(">>> WAVE YOUR HAND IN FRONT OF THE RIGHT SENSOR NOW! <<<")
    print()

    time.sleep(2)  # Give user time to prepare

    start_time = time.time()
    success = blocker.trigger_blocking(BallSide.RIGHT)
    elapsed = time.time() - start_time

    print(f"\nMonitoring completed in {elapsed:.1f} seconds")
    if success:
        print("✅ SUCCESS! Ball crossing detected on RIGHT side!")
        print("   Servo 5 was raised for 2 seconds")
    else:
        print("⚠️  No ball crossing detected on RIGHT side")
        print("   (This is OK if you didn't wave your hand)")

    # Show statistics
    stats = blocker.get_statistics()
    print("\n" + "="*70)
    print("Test Statistics:")
    print("="*70)
    print(f"  Total detections:   {stats['total_detections']}")
    print(f"  Successful blocks:  {stats['successful_blocks']}")
    print(f"  Failed blocks:      {stats['failed_blocks']}")
    print(f"  Success rate:       {stats['success_rate']:.1f}%")
    print("="*70)


def main():
    """Main test function"""
    print("="*70)
    print("Ball Blocking System - Automatic Test")
    print("="*70)
    print()

    # Connect to Arduino
    print("Connecting to Arduino on /dev/ttyACM0...")
    serial = SerialController(port='/dev/ttyACM0')

    if not serial.connect():
        print("\n" + "="*70)
        print("ERROR: Failed to connect to Arduino")
        print("="*70)
        print("Please check:")
        print("  1. Arduino is connected to USB")
        print("  2. Firmware is uploaded")
        print("  3. Port is /dev/ttyACM0")
        print("="*70)
        sys.exit(1)

    print("✅ Connected to Arduino successfully\n")

    try:
        test_automatic_trigger(serial)

        print("\n" + "="*70)
        print("Test completed!")
        print("="*70)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user (Ctrl+C)")

    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        serial.cleanup()
        print("\nArduino connection closed")


if __name__ == "__main__":
    main()
