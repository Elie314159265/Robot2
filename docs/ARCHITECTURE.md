# System Architecture

## Overview

The Robot PK system is divided into two main processing units:

1. **RaspberryPi** - High-level vision and planning
2. **Arduino Uno** - Low-level motor and sensor control

## Component Interactions

```
┌─────────────────────────────────┐
│  RaspberryPi 4 (Ubuntu)         │
├─────────────────────────────────┤
│                                 │
│  ┌──────────────┐              │
│  │   Camera     │              │
│  │  (piCam 3)   │              │
│  └──────────────┘              │
│         │                       │
│         ▼                       │
│  ┌──────────────┐              │
│  │  Frame Cap   │              │
│  │  640x480@30  │              │
│  └──────────────┘              │
│         │                       │
│         ▼                       │
│  ┌──────────────┐              │
│  │   TPU Core   │              │
│  │  Inference   │              │
│  └──────────────┘              │
│         │                       │
│         ▼                       │
│  ┌──────────────┐              │
│  │    Ball      │              │
│  │  Detection   │              │
│  └──────────────┘              │
│         │                       │
│         ▼                       │
│  ┌──────────────┐              │
│  │  Tracking &  │              │
│  │  Prediction  │              │
│  └──────────────┘              │
│         │                       │
│         │ Serial (9600 baud)   │
└─────────┼───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  Arduino Uno                    │
├─────────────────────────────────┤
│                                 │
│  ┌──────────────────────────┐  │
│  │  Serial Handler          │  │
│  │  (Command Parser)        │  │
│  └──────────────────────────┘  │
│         │                       │
│         ├─────────┬────────┐    │
│         │         │        │    │
│         ▼         ▼        ▼    │
│  ┌────────┐ ┌────────┐ ┌────┐ │
│  │PCA9685 │ │Ultrasonic
│  │Servo  │ │Sensor  │ │DC  │ │
│  │Driver  │ │(HC-SR04)
│  │(I2C)   │ │        │ │Motor
│  └────────┘ └────────┘ └────┘ │
│      │           │        │    │
│      ▼           ▼        ▼    │
│   16x Servo   Distance  Walking │
│   Motors      Measure  Control  │
│                                 │
└─────────────────────────────────┘
```

## Data Flow

### Detection Pipeline
```
Camera Frame → TPU Inference → Ball Detection → Tracking → Servo Command
```

### Position Estimation
```
Servo Angle + Distance → Coordinate Transform → Kalman Filter → Position
```

### Prediction
```
Position History → Trajectory Model → Landing Position Prediction
```

## Module Details

### Camera Module (`src/camera/`)
- **CameraController**: Manages picamera2 initialization and frame capture
- Handles 30 FPS streaming at 640x480 resolution
- Provides both raw frame and JPEG output

### Detection Module (`src/detection/`)
- **TPUEngine**: Wrapper for Edge TPU inference
- **BallDetector**: Filters detections for sports ball (COCO class 37)
- Runs COCO SSD MobileNet v2 model
- Target: <20ms inference time

### Tracking Module (`src/tracking/`)
- **PIDController**: Classic PID feedback control
- **BallTracker**: State machine for tracking lifecycle
- Maintains tracking state (idle, tracking, lost)
- Outputs servo angle commands

### Positioning Module (`src/positioning/`)
- **CoordinateTransformer**: Polar (angle, distance) → Cartesian (x, y)
- **KalmanFilter**: Noise reduction for distance measurements

### Prediction Module (`src/prediction/`)
- **TrajectoryPredictor**: Fits polynomial model to position history
- Predicts ball landing position
- Estimates velocity vector

### Arduino Module (`src/arduino/`)
- **SerialController**: Serial protocol handler
- Sends servo commands and receives sensor data
- Protocol: ASCII-based commands (e.g., "S0090\n" = servo 0 to 90°)

### Arm Module (`src/arm/`)
- **InverseKinematics**: Calculates joint angles from target position
- Used for robot arm positioning

### Utils Module (`src/utils/`)
- **Logger**: Centralized logging configuration
- **Config**: YAML-based configuration management

## Performance Requirements

| Metric | Target | Status |
|--------|--------|--------|
| Frame Rate | 30 FPS | ✅ |
| TPU Inference | <20ms | ⏳ |
| Serial Latency | <10ms | ⏳ |
| Detection Accuracy | ≥80% | ⏳ |
| Tracking Precision | ±20px | ⏳ |
| Position Error | ±10cm @ 2m | ⏳ |

## Key Design Decisions

1. **Modular Architecture**: Each module independent and testable
2. **Single Responsibility**: Each file handles one concern
3. **Configuration via YAML**: Easy runtime parameter adjustment
4. **Staged Development**: Implement and test each phase sequentially
5. **Real-time Priority**: Minimize latency in detection loop

## Critical Paths

1. **Detection Loop** (highest priority)
   - Frame capture → Detection → Tracking → Servo command
   - Target latency: <50ms (30 FPS = 33ms per frame)

2. **Serial Communication**
   - Must not block main detection loop
   - Consider multi-threading for servo commands

3. **Sensor Input**
   - Distance sensor readings should be non-blocking
   - May need debouncing for ultrasonic

## Thread Safety Considerations

- Camera frame capture in main thread
- TPU inference can be in separate thread (Python threading)
- Serial communication should be non-blocking (queue-based)
- Shared state between threads must use locks

## Error Handling Strategy

- Graceful degradation when detection fails
- Continue servo centering on lost ball
- Log all errors for debugging
- Timeout mechanisms for unresponsive components

## Future Extensions

- Multiple camera support for stereo vision
- ROS integration for modularity
- Cloud logging and monitoring
- Machine learning model fine-tuning
- Real-time video streaming for debugging
