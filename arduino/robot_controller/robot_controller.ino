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

// Leg configurations (from walk_program.ino)
// Leg numbers: FL=0,1 / FR=2,3 / BL=4,5 / BR=6,7
// Format: hip_channel, knee_channel
const int KNEE_UPL = 150;    // 左足を上げる
const int KNEE_DOWNL = 350;  // 左足を下ろす
const int KNEE_UPR = 350;    // 右足を上げる
const int KNEE_DOWNR = 150;  // 右足を下ろす

// Ultrasonic sensor pins (Left sensor)
#define TRIG_PIN_LEFT 8
#define ECHO_PIN_LEFT 9

// Ultrasonic sensor pins (Right sensor)
#define TRIG_PIN_RIGHT 10
#define ECHO_PIN_RIGHT 11

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
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);
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

    case 'D': // Distance sensor read: DL or DR (Left or Right)
      if (cmd.length() == 2) {
        char side = cmd.charAt(1);
        float distance = -1.0;

        if (side == 'L') {
          distance = readDistanceLeft();
        } else if (side == 'R') {
          distance = readDistanceRight();
        } else {
          Serial.println("ERR");
          break;
        }

        // Format: D[VALUE:5] (in mm, e.g., D00125 = 12.5cm)
        int distanceMM = (int)(distance * 10);
        char buffer[10];
        sprintf(buffer, "D%05d", distanceMM);
        Serial.println(buffer);
      } else {
        Serial.println("ERR");
      }
      break;

    case 'H': // High-speed monitoring: HL or HR (Left or Right)
      if (cmd.length() == 2) {
        char side = cmd.charAt(1);
        if (side == 'L') {
          highSpeedMonitorLeft();
          Serial.println("OK");
        } else if (side == 'R') {
          highSpeedMonitorRight();
          Serial.println("OK");
        } else {
          Serial.println("ERR");
        }
      } else {
        Serial.println("ERR");
      }
      break;

    case 'B': // Ball block command: BL or BR (Left or Right)
      if (cmd.length() == 2) {
        char side = cmd.charAt(1);
        if (side == 'L') {
          blockBallLeft();
          Serial.println("OK");
        } else if (side == 'R') {
          blockBallRight();
          Serial.println("OK");
        } else {
          Serial.println("ERR");
        }
      } else {
        Serial.println("ERR");
      }
      break;

    default:
      Serial.println("ERR");
      break;
  }
}

float readDistanceLeft() {
  // HC-SR04 ultrasonic sensor (Left)
  // Returns distance in cm

  // Send trigger pulse
  digitalWrite(TRIG_PIN_LEFT, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN_LEFT, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN_LEFT, LOW);

  // Read echo pulse
  long duration = pulseIn(ECHO_PIN_LEFT, HIGH, 30000); // 30ms timeout

  if (duration == 0) {
    return -1.0; // No echo (out of range)
  }

  // Calculate distance (speed of sound: 340m/s = 0.034cm/μs)
  // distance = (duration / 2) * 0.034
  float distance = (duration * 0.034) / 2.0;

  return distance;
}

float readDistanceRight() {
  // HC-SR04 ultrasonic sensor (Right)
  // Returns distance in cm

  // Send trigger pulse
  digitalWrite(TRIG_PIN_RIGHT, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN_RIGHT, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN_RIGHT, LOW);

  // Read echo pulse
  long duration = pulseIn(ECHO_PIN_RIGHT, HIGH, 30000); // 30ms timeout

  if (duration == 0) {
    return -1.0; // No echo (out of range)
  }

  // Calculate distance (speed of sound: 340m/s = 0.034cm/μs)
  // distance = (duration / 2) * 0.034
  float distance = (duration * 0.034) / 2.0;

  return distance;
}

void highSpeedMonitorLeft() {
  // 左側超音波センサーで4秒間高速データ取得（約50Hz）
  // ボールが横切った瞬間を検出し、サーボ7番を上げる

  unsigned long startTime = millis();
  unsigned long duration = 4000; // 4秒間
  float lastDistance = -1.0;
  int sequenceNum = 0;

  // 移動平均用バッファ
  const int BUFFER_SIZE = 5;
  float distanceBuffer[BUFFER_SIZE];
  int bufferIndex = 0;
  int bufferCount = 0;

  // 初期化
  for (int i = 0; i < BUFFER_SIZE; i++) {
    distanceBuffer[i] = 0.0;
  }

  while (millis() - startTime < duration) {
    float distance = readDistanceLeft();
    unsigned long currentTime = millis() - startTime;

    if (distance > 0 && distance < 400.0) {
      // 移動平均に追加
      distanceBuffer[bufferIndex] = distance;
      bufferIndex = (bufferIndex + 1) % BUFFER_SIZE;
      if (bufferCount < BUFFER_SIZE) bufferCount++;

      // 移動平均を計算
      float avgDistance = 0.0;
      for (int i = 0; i < bufferCount; i++) {
        avgDistance += distanceBuffer[i];
      }
      avgDistance /= bufferCount;

      // データをストリーム送信（Format: D:<distance>,T:<time>,N:<seq>）
      Serial.print("D:");
      Serial.print(distance, 2);
      Serial.print(",T:");
      Serial.print(currentTime);
      Serial.print(",N:");
      Serial.println(sequenceNum++);

      // ボール横切り検出（急激な距離変化）
      if (lastDistance > 0 && bufferCount >= BUFFER_SIZE) {
        float distanceChange = abs(distance - lastDistance);

        // 閾値: 10cm以上の急激な変化
        if (distanceChange > 10.0) {
          // ボール検出！サーボ7番を上げる
          pwm.setPWM(7, 0, KNEE_UPR);
          Serial.println("BALL_DETECTED_LEFT");
          delay(2000); // 2秒間保持
          pwm.setPWM(7, 0, KNEE_DOWNR);
          return; // 検出後は終了
        }
      }

      lastDistance = avgDistance;
    }

    delay(20); // 約50Hz（20ms間隔）
  }
}

void highSpeedMonitorRight() {
  // 右側超音波センサーで4秒間高速データ取得（約50Hz）
  // ボールが横切った瞬間を検出し、サーボ5番を上げる

  unsigned long startTime = millis();
  unsigned long duration = 4000; // 4秒間
  float lastDistance = -1.0;
  int sequenceNum = 0;

  // 移動平均用バッファ
  const int BUFFER_SIZE = 5;
  float distanceBuffer[BUFFER_SIZE];
  int bufferIndex = 0;
  int bufferCount = 0;

  // 初期化
  for (int i = 0; i < BUFFER_SIZE; i++) {
    distanceBuffer[i] = 0.0;
  }

  while (millis() - startTime < duration) {
    float distance = readDistanceRight();
    unsigned long currentTime = millis() - startTime;

    if (distance > 0 && distance < 400.0) {
      // 移動平均に追加
      distanceBuffer[bufferIndex] = distance;
      bufferIndex = (bufferIndex + 1) % BUFFER_SIZE;
      if (bufferCount < BUFFER_SIZE) bufferCount++;

      // 移動平均を計算
      float avgDistance = 0.0;
      for (int i = 0; i < bufferCount; i++) {
        avgDistance += distanceBuffer[i];
      }
      avgDistance /= bufferCount;

      // データをストリーム送信（Format: D:<distance>,T:<time>,N:<seq>）
      Serial.print("D:");
      Serial.print(distance, 2);
      Serial.print(",T:");
      Serial.print(currentTime);
      Serial.print(",N:");
      Serial.println(sequenceNum++);

      // ボール横切り検出（急激な距離変化）
      if (lastDistance > 0 && bufferCount >= BUFFER_SIZE) {
        float distanceChange = abs(distance - lastDistance);

        // 閾値: 10cm以上の急激な変化
        if (distanceChange > 10.0) {
          // ボール検出！サーボ5番を上げる
          pwm.setPWM(5, 0, KNEE_UPL);
          Serial.println("BALL_DETECTED_RIGHT");
          delay(2000); // 2秒間保持
          pwm.setPWM(5, 0, KNEE_DOWNL);
          return; // 検出後は終了
        }
      }

      lastDistance = avgDistance;
    }

    delay(20); // 約50Hz（20ms間隔）
  }
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

void blockBallLeft() {
  // ボールが画面左側に現れた場合、7番の足(BR: 右後脚)を上げてブロック
  // Leg BR: hip=6, knee=7
  // 5秒間足を上げてボールをブロック
  pwm.setPWM(7, 0, KNEE_UPR);  // 右足を上げる
  delay(5000);                  // 5秒間保持
  pwm.setPWM(7, 0, KNEE_DOWNR); // 右足を下ろす
}

void blockBallRight() {
  // ボールが画面右側に現れた場合、5番の足(BL: 左後脚)を上げてブロック
  // Leg BL: hip=8(or 4), knee=5
  // 5秒間足を上げてボールをブロック
  pwm.setPWM(5, 0, KNEE_UPL);  // 左足を上げる
  delay(5000);                  // 5秒間保持
  pwm.setPWM(5, 0, KNEE_DOWNL); // 左足を下ろす
}
