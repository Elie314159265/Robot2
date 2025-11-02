/*
Robot Controller - Arduino Uno Firmware
Manages servo control and sensor reading

Hardware:
- PCA9685 Servo Driver (I2C)
- Ultrasonic Distance Sensor (HC-SR04)
- 16 Servo Motors
- DC Motor for walking

Protocol:
- Serial communication with RaspberryPi (9600 baud)
- Command format: [COMMAND][ID][VALUE]\n
*/

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// PCA9685 I2C address
#define SERVO_DRIVER_ADDR 0x40

// Servo configuration (based on walk_program.ino)
#define NUM_SERVOS 16
#define SERVO_MIN 150    // Min PWM value (0 degrees)
#define SERVO_MAX 600    // Max PWM value (180 degrees)
#define SERVO_FREQ 60    // 60Hz for standard servos (walk_program.ino setting)

// Ultrasonic sensor pins
#define TRIG_PIN 9
#define ECHO_PIN 10

// DC motor pins
#define MOTOR_PIN1 5
#define MOTOR_PIN2 6

// Serial communication
#define BAUD_RATE 9600

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(SERVO_DRIVER_ADDR);

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);

  // Initialize I2C and PCA9685
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);

  // Initialize sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(MOTOR_PIN1, OUTPUT);
  pinMode(MOTOR_PIN2, OUTPUT);

  // Center all servos
  for (int i = 0; i < NUM_SERVOS; i++) {
    pwm.setPWM(i, 0, (SERVO_MIN + SERVO_MAX) / 2);
  }

  Serial.println("Arduino initialized");
}

void loop() {
  // Check for incoming serial commands
  if (Serial.available() > 0) {
    processCommand();
  }

  delay(10);
}

void processCommand() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd.length() == 0) {
    return;
  }

  char command = cmd.charAt(0);

  switch (command) {
    case 'S': // Servo command: S[ID:2][ANGLE:3]
      if (cmd.length() == 6) {
        int servoId = cmd.substring(1, 3).toInt();
        int angle = cmd.substring(3, 6).toInt();
        setServo(servoId, angle);
        Serial.println("OK");
      } else {
        Serial.println("ERR");
      }
      break;

    case 'D': // Distance sensor read
      {
        float distance = readDistance();
        // Format: D[VALUE:5] (in mm, e.g., D00125 = 12.5cm)
        int distanceMM = (int)(distance * 10);
        char buffer[10];
        sprintf(buffer, "D%05d", distanceMM);
        Serial.println(buffer);
      }
      break;

    default:
      Serial.println("ERR");
      break;
  }
}

float readDistance() {
  // HC-SR04 ultrasonic sensor
  // Returns distance in cm

  // Send trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Read echo pulse
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout

  if (duration == 0) {
    return -1.0; // No echo (out of range)
  }

  // Calculate distance (speed of sound: 340m/s = 0.034cm/μs)
  // distance = (duration / 2) * 0.034
  float distance = (duration * 0.034) / 2.0;

  return distance;
}

void setServo(int servoId, int angle) {
  // Servo control via PCA9685
  // servoId: 0-15
  // angle: 0-180 degrees

  if (servoId < 0 || servoId >= NUM_SERVOS) {
    return; // Invalid servo ID
  }

  if (angle < 0) angle = 0;
  if (angle > 180) angle = 180;

  // Map angle (0-180) to PWM value (SERVO_MIN-SERVO_MAX)
  int pwmValue = map(angle, 0, 180, SERVO_MIN, SERVO_MAX);

  pwm.setPWM(servoId, 0, pwmValue);
}

void setMotor(int speed) {
  // Placeholder for DC motor control
  // speed: -255 to 255
}

void setMotorWalk(int direction, int speed) {
  // Placeholder for 4-leg walking pattern
  // direction: 0=forward, 1=backward, 2=left, 3=right
}
