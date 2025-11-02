#!/usr/bin/env python3
"""
Run servo test via serial communication
"""

import serial
import time
import sys

port = "/dev/ttyACM0"
baudrate = 9600

print("=== Servo Test Runner ===")
print(f"Connecting to {port}...")

try:
    ser = serial.Serial(port, baudrate, timeout=2)
    time.sleep(2)  # Wait for Arduino reset

    # Clear buffer
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Read initial messages
    print("\n--- Arduino Output ---")
    for _ in range(20):
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            print(line)
        time.sleep(0.1)

    print("\n=== Running Full Servo Sweep Test ===")
    print("Sending command '1' (Test all servos sweep)...\n")

    # Send command '1' for full sweep test
    ser.write(b'1\n')

    # Read and display output for 60 seconds
    start_time = time.time()
    while time.time() - start_time < 60:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                print(line)
        time.sleep(0.1)

    print("\n=== Test Complete ===")

    ser.close()

except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    ser.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
