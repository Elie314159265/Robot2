# Setup Guide

## Prerequisites

- RaspberryPi 4 (8GB RAM recommended)
- Ubuntu Server 20.04 LTS (or later)
- RaspberryPi Camera Module 3
- Google Coral Edge TPU (USB)
- Arduino Uno
- PCA9685 Servo Driver
- HC-SR04 Ultrasonic Sensor
- 16x Servo Motors
- DC Motor for walking
- 10A+ Power Supply

## Step 1: RaspberryPi Setup

### 1.1 Flash Ubuntu Server

```bash
# Use Raspberry Pi Imager to flash Ubuntu Server 20.04 LTS (64-bit)
# https://www.raspberrypi.com/software/
```

### 1.2 Enable Camera Interface

```bash
# Connect to RaspberryPi via SSH
ssh ubuntu@<raspberrypi-ip>

# Edit boot config
sudo nano /boot/firmware/config.txt

# Add or uncomment:
# dtoverlay=vc4-fkms-v3d
# camera_auto_detect=1

# Reboot
sudo reboot
```

### 1.3 Verify Camera

```bash
# List cameras
libcamera-hello --list-cameras

# Test camera
libcamera-hello --duration 5000
```

## Step 2: Install Python Dependencies

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install Python packages
sudo apt install -y \
    python3-pip \
    python3-picamera2 \
    python3-opencv \
    python3-numpy \
    python3-dev \
    libopenjp2-7 \
    libtiff6 \
    libjasper1 \
    libharfbuzz0b \
    libwebp6 \
    libtiffxx5

# Clone repository
cd ~
git clone https://github.com/Elie314159265/Robot2.git
cd Robot2

# Install Python dependencies
pip install -r requirements.txt
```

## Step 3: Setup Google Coral TPU

### 3.1 Install TPU Runtime

```bash
# Add Coral repository
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | \
    sudo tee /etc/apt/sources.list.d/coral-edgetpu.list

# Add GPG key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    sudo apt-key add -

# Install runtime
sudo apt update
sudo apt install -y libedgetpu1-std

# Install Python bindings
pip install pycoral
```

### 3.2 Verify TPU

```bash
# List USB devices
lsusb | grep Coral

# Should see something like:
# Bus 001 Device 005: ID 1a6e:089a Google Inc. Coral Edge TPU
```

### 3.3 Download Models

```bash
bash scripts/download_models.sh

# Verify downloads
ls -lh models/
```

## Step 4: Arduino Setup

### 4.1 Install Arduino IDE (Optional)

```bash
sudo apt install -y arduino

# Or use command-line tools
sudo apt install -y avrdude avr-libc avr-gcc
```

### 4.2 Upload Firmware

```bash
# Using Arduino IDE: Open arduino/robot_controller/robot_controller.ino
# Select Board: Arduino Uno
# Select Port: /dev/ttyACM0 (or your port)
# Click Upload

# Or via command line:
# (after installing avr tools)
# avrdude -F -V -c arduino -b 115200 -p m328p \
#   -P /dev/ttyACM0 -U flash:w:robot_controller.ino.hex:i
```

### 4.3 Verify Serial Connection

```bash
# List serial devices
ls /dev/ttyACM* /dev/ttyUSB*

# Test connection
screen /dev/ttyACM0 9600

# Press Ctrl+A, then Ctrl+X to exit
```

## Step 5: Verify Installation

```bash
# Run camera test
python3 tests/test_camera.py

# Should output:
# TEST 1: Camera Initialization
# PASSED
# ...
```

## Step 6: Hardware Wiring

### Camera Module 3
- Connect to CSI port on RaspberryPi

### Google Coral TPU
- Connect to USB 3.0 port (recommended)

### Arduino Uno
- Connect to USB port (provides serial + power)

### PCA9685 I2C Servo Driver
- SDA (GPIO 2) → SDA pin
- SCL (GPIO 3) → SCL pin
- VCC → 5V (separate power supply!)
- GND → GND

### HC-SR04 Ultrasonic Sensor
- TRIG → Arduino Pin 9
- ECHO → Arduino Pin 10
- VCC → 5V
- GND → GND

### 16x Servo Motors
- Connected to PCA9685 (pins 0-15)
- Power from separate 5V supply

### DC Motor
- Motor 1 → Arduino Pin 5 (PWM)
- Motor 2 → Arduino Pin 6 (PWM)
- Power from separate supply

## Step 7: Test Each Component

```bash
# Test camera
python3 tests/test_camera.py

# Test TPU (when Phase 2 is complete)
python3 tests/test_detection.py

# Test tracking (when Phase 5 is complete)
python3 tests/test_tracking.py
```

## Troubleshooting

### Camera Not Detected
```bash
# Check if enabled
vcgencmd get_camera

# Enable:
sudo raspi-config
# → Interface Options → Camera → Enable
```

### TPU Not Found
```bash
# Check USB connection
lsusb | grep Coral

# Check permissions
sudo chmod 777 /dev/bus/usb/*/*
```

### Serial Connection Issues
```bash
# Check port
ls /dev/ttyACM*

# Check permissions
sudo usermod -a -G dialout $USER

# Log out and back in for changes to take effect
```

### Performance Issues
```bash
# Check system resources
free -h
top

# Monitor CPU temperature
vcgencmd measure_temp

# Check for thermal throttling
vcgencmd get_throttled
```

## Performance Optimization

### CPU Frequency Scaling
```bash
# Check current frequency
cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_cur_freq

# Set to performance mode
echo "performance" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

### Memory Settings
```bash
# Allocate more GPU memory (for image processing)
sudo nano /boot/firmware/config.txt

# Add:
# gpu_mem=256

# Reboot
sudo reboot
```

### Cooling
- Install heatsinks on CPU and RAM
- Use fan if running extended operations
- Monitor temperature: `vcgencmd measure_temp`

## Next Steps

1. Run Phase 1 camera test
2. Proceed with Phase 2 (TPU detection)
3. Complete remaining phases sequentially
4. Test on actual ball inputs
5. Fine-tune parameters via config file

See README.md for further instructions.
