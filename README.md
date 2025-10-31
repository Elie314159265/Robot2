# Robot PK - 4-legged Goalkeeper Robot

A RaspberryPi-based autonomous goalkeeper robot that detects and blocks incoming soccer balls using AI and computer vision.

## Project Overview

**Challenge**: Build a 4-legged crab-type robot that:
- Walks and rotates
- Climbs 3cm steps
- Detects incoming soccer balls using AI
- Tracks and blocks the ball in real-time

## Hardware Architecture

### Main Components
- **RaspberryPi 4** (8GB, Ubuntu OS) - Camera processing and TPU inference
- **Arduino Uno** - Servo and sensor control
- **RaspberryPi Camera Module 3** - Video input
- **Google Coral Edge TPU** - AI acceleration
- **PCA9685 Servo Driver** - 16-servo control
- **HC-SR04 Ultrasonic Sensor** - Distance measurement
- **DC Motors** - Walking mechanism

### Communication
```
RaspberryPi ←→ Arduino (Serial @ 9600 baud)
  ↓                        ↓
Camera + TPU        Servo + Sensor Control
```

## Software Architecture

```
src/
├── camera/          # picamera2 camera control
├── detection/       # TPU inference & ball detection
├── tracking/        # PID servo control for tracking
├── positioning/     # Coordinate transformation & Kalman filter
├── prediction/      # Trajectory prediction
├── arduino/         # Serial communication with Arduino
├── arm/             # Inverse kinematics for arm control
├── utils/           # Logging and configuration
└── main.py          # Main program entry

tests/               # Unit and integration tests
arduino/            # Arduino firmware
config/             # YAML configuration files
scripts/            # Setup and utility scripts
models/             # ML models (downloaded at runtime)
logs/               # Runtime logs
```

## Quick Start

### 1. Setup Environment

```bash
# Clone repository
cd /home/master/robot_pk

# Install Python dependencies
pip install -r requirements.txt

# Setup camera (on RaspberryPi)
bash scripts/setup_camera.sh

# Setup TPU (on RaspberryPi)
bash scripts/setup_tpu.sh

# Download ML models
bash scripts/download_models.sh
```

### 2. Run Tests

```bash
# Phase 1: Camera test
python3 tests/test_camera.py

# Phase 2: Detection test (when implemented)
python3 tests/test_detection.py

# Phase 5: Tracking test (when implemented)
python3 tests/test_tracking.py
```

### 3. Run Main Program

```bash
# Start main robot control
python3 src/main.py

# Debug mode
python3 src/main.py --debug

# Specific phase
python3 src/main.py --phase 1
```

## Development Phases

| Phase | Task | Status |
|-------|------|--------|
| 1 | Camera setup (30fps @ 640x480) | ✅ Done |
| 2 | TPU setup & ball detection | ⏳ In Progress |
| 3 | Arduino integration | ⏳ Pending |
| 4 | Real-time detection | ⏳ Pending |
| 5 | PID tracking control | ⏳ Pending |
| 6 | 2D position mapping | ⏳ Pending |
| 7 | Trajectory prediction | ⏳ Pending |
| 8+ | Integration testing | ⏳ Pending |

## Key Features

### Phase 1: Camera Control ✅
- Initialize RaspberryPi Camera Module 3
- Capture frames at 30 FPS
- 640x480 resolution
- Real-time performance monitoring

### Phase 2: Object Detection (In Progress)
- COCO pre-trained model for "sports ball" detection
- Target accuracy: ≥80%
- Edge TPU acceleration for real-time inference
- <20ms inference time target

### Phase 3: Arduino Integration (Pending)
- Serial communication (9600 baud, <10ms latency)
- 16 servo motor control via PCA9685
- Ultrasonic distance sensor reading
- DC motor control for walking

### Phase 4-5: Ball Tracking (Pending)
- PID controller for servo positioning
- Real-time ball following
- Camera-based target acquisition

### Phase 6-7: Position & Prediction (Pending)
- Polar to Cartesian coordinate transformation
- Kalman filter for noise reduction
- Trajectory prediction using position history

## Configuration

Edit `config/robot_config.yaml` to adjust:
- Camera resolution and framerate
- Detection confidence threshold
- PID controller gains
- Arduino serial port
- System debug settings

## Troubleshooting

### Camera Not Found
```bash
# List available cameras
libcamera-hello --list-cameras

# Check if enabled
vcgencmd get_camera
```

### TPU Not Detected
```bash
# Verify TPU is connected
lsusb | grep Coral
```

### Serial Communication Issues
```bash
# Check Arduino port
ls /dev/ttyACM*

# Test connection
screen /dev/ttyACM0 9600
```

## Technical Specifications

- **Target FPS**: 30 fps
- **Camera Resolution**: 640x480
- **TPU Inference**: <20ms
- **Serial Latency**: <10ms
- **Detection Accuracy**: ≥80%
- **Tracking Precision**: ±20px
- **Position Error**: ±10cm @ 2m distance

## Design Principles

1. **Modularity**: Each file ≤200 lines, single responsibility
2. **Real-time Performance**: 30 FPS end-to-end target
3. **Staged Development**: Test each phase before proceeding
4. **Git Discipline**: Commit after each working feature
5. **Power Management**: Separate servo and RaspberryPi power

## Important Notes

### Power Management
⚠️ **Critical**: Servo power must be separate from RaspberryPi
- Use 10A+ power supply for servos
- Avoid simultaneous multi-servo movement to prevent brown-out

### Ubuntu Server Setup
- Uses `picamera2` (not deprecated `picamera`)
- Requires libcamera backend
- SSH-friendly (no GUI needed)

### Python Environment
- Python 3.9+
- Virtual environment recommended
- GIL considerations for threading

## References

- [picamera2 Documentation](https://github.com/raspberrypi/picamera2)
- [Google Coral TPU Guide](https://coral.ai/)
- [COCO Dataset](https://cocodataset.org/)
- [Adafruit PCA9685](https://github.com/adafruit/Adafruit-PCA9685-Python-Library)

## License

See LICENSE file for details

## Authors

Robot Development Team
