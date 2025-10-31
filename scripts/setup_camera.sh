#!/bin/bash
# Camera Setup Script for RaspberryPi
# Installs required packages for picamera2 and camera support

echo "==========================================="
echo "Robot PK - Camera Setup Script"
echo "==========================================="

# Update package list
echo "Updating package list..."
sudo apt update

# Install required packages
echo "Installing camera support packages..."
sudo apt install -y \
    python3-picamera2 \
    python3-opencv \
    python3-numpy \
    libcamera-tools \
    python3-libcamera

# Verify camera
echo ""
echo "Verifying camera..."
libcamera-hello --list-cameras

echo ""
echo "Camera setup complete!"
echo "To enable camera in RaspberryPi:"
echo "  1. Run: sudo raspi-config"
echo "  2. Navigate to: 3 -> P1 (Camera)"
echo "  3. Enable the camera"
echo "  4. Reboot"
