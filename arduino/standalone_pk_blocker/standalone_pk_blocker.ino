/*
 * Standalone PK Ball Blocker - Arduino単体動作版
 * 超音波センサーでボールを自動検出してブロックする
 *
 * RaspberryPi不要、Arduino IDE単体で動作
 *
 * Hardware:
 * - Arduino Uno
 * - PCA9685 Servo Driver (I2C)
 * - HC-SR04 Ultrasonic Sensors x2 (左右)
 * - 8 Servo Motors (4 legs x 2 joints)
 *
 * 配線:
 * 【左側センサー】
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   Trig -> Arduino D8
 *   Echo -> Arduino D9
 *
 * 【右側センサー】
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   Trig -> Arduino D10
 *   Echo -> Arduino D11
 *
 * 【PCA9685】
 *   VCC -> Arduino 5V
 *   GND -> Arduino GND
 *   SDA -> Arduino A4
 *   SCL -> Arduino A5
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// ========================================
// サーボチャンネル定義
// ========================================
const int FL_HIP = 0;    // 左前脚の腰
const int FL_KNEE = 1;   // 左前脚の膝
const int FR_HIP = 2;    // 右前脚の腰
const int FR_KNEE = 3;   // 右前脚の膝
const int BL_HIP = 8;    // 左後脚の腰
const int BL_KNEE = 5;   // 左後脚の膝
const int BR_HIP = 6;    // 右後脚の腰
const int BR_KNEE = 7;   // 右後脚の膝

// ========================================
// PWM値定義
// ========================================

// --- 左前脚 (FL) ---
const int FL_HIP_NEUTRAL = 160;
const int FL_KNEE_UP = 100;
const int FL_KNEE_DOWN = 300;

// --- 右前脚 (FR) ---
const int FR_HIP_NEUTRAL = 300;
const int FR_KNEE_UP = 380;
const int FR_KNEE_DOWN = 150;

// --- 左後脚 (BL) - ボールブロック用 ---
const int BL_HIP_NEUTRAL = 290;
const int BL_KNEE_UP = 150;
const int BL_KNEE_DOWN = 400;

// --- 右後脚 (BR) - ボールブロック用 ---
const int BR_HIP_NEUTRAL = 230;
const int BR_KNEE_UP = 380;
const int BR_KNEE_DOWN = 150;

// ========================================
// 超音波センサーピン定義
// ========================================
const int TRIG_PIN_LEFT = 8;
const int ECHO_PIN_LEFT = 9;
const int TRIG_PIN_RIGHT = 10;
const int ECHO_PIN_RIGHT = 11;

// ========================================
// 検出設定
// ========================================
const float DETECTION_THRESHOLD = 30.0;  // ボール検出距離（cm）
const unsigned long BLOCK_COOLDOWN = 6000;  // ブロック後の待機時間（ms）
const unsigned long MEASUREMENT_INTERVAL = 100;  // センサー測定間隔（ms）

// ========================================
// システム設定
// ========================================
const int BAUD_RATE = 115200;
const int SERVO_FREQ = 60;

// ========================================
// 状態変数
// ========================================
unsigned long lastBlockTime = 0;
unsigned long lastMeasurementTime = 0;
bool isBlocking = false;
unsigned long blockCount = 0;

// ========================================
// セットアップ
// ========================================
void setup() {
  Serial.begin(BAUD_RATE);

  // 起動メッセージ
  Serial.println("========================================");
  Serial.println("   Standalone PK Ball Blocker");
  Serial.println("   Arduino単体動作版");
  Serial.println("========================================");
  Serial.println();

  // PWMドライバー初期化
  Serial.print("Initializing PCA9685... ");
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);
  Serial.println("OK");

  // 超音波センサーピン設定
  Serial.print("Initializing ultrasonic sensors... ");
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);
  Serial.println("OK");

  // 全脚をニュートラル位置に初期化
  Serial.print("Moving legs to neutral position... ");
  initializeLegs();
  Serial.println("OK");

  Serial.println();
  Serial.println("System ready!");
  Serial.print("Detection threshold: ");
  Serial.print(DETECTION_THRESHOLD);
  Serial.println(" cm");
  Serial.print("Block cooldown: ");
  Serial.print(BLOCK_COOLDOWN / 1000.0);
  Serial.println(" sec");
  Serial.println();
  Serial.println("Monitoring for ball...");
  Serial.println("----------------------------------------");

  lastMeasurementTime = millis();
}

// ========================================
// 全脚を初期位置に設定
// ========================================
void initializeLegs() {
  // 腰をニュートラルに
  pwm.setPWM(FL_HIP, 0, FL_HIP_NEUTRAL);
  pwm.setPWM(FR_HIP, 0, FR_HIP_NEUTRAL);
  pwm.setPWM(BL_HIP, 0, BL_HIP_NEUTRAL);
  pwm.setPWM(BR_HIP, 0, BR_HIP_NEUTRAL);

  // 膝を下ろした状態に（立っている状態）
  pwm.setPWM(FL_KNEE, 0, FL_KNEE_DOWN);
  pwm.setPWM(FR_KNEE, 0, FR_KNEE_DOWN);
  pwm.setPWM(BL_KNEE, 0, BL_KNEE_DOWN);
  pwm.setPWM(BR_KNEE, 0, BR_KNEE_DOWN);

  delay(500);  // サーボが位置に到達するまで待機
}

// ========================================
// メインループ
// ========================================
void loop() {
  unsigned long currentTime = millis();

  // ブロック中はスキップ
  if (isBlocking) {
    return;
  }

  // クールダウン中はスキップ
  if (currentTime - lastBlockTime < BLOCK_COOLDOWN) {
    return;
  }

  // 測定間隔チェック
  if (currentTime - lastMeasurementTime < MEASUREMENT_INTERVAL) {
    return;
  }

  lastMeasurementTime = currentTime;

  // 両方のセンサーで距離測定
  float distanceLeft = readDistanceLeft();
  float distanceRight = readDistanceRight();

  // デバッグ出力（距離表示）
  Serial.print("L: ");
  if (distanceLeft >= 0) {
    Serial.print(distanceLeft, 1);
  } else {
    Serial.print("---");
  }
  Serial.print(" cm | R: ");
  if (distanceRight >= 0) {
    Serial.print(distanceRight, 1);
  } else {
    Serial.print("---");
  }
  Serial.println(" cm");

  // ボール検出判定
  bool ballDetectedLeft = (distanceLeft >= 0 && distanceLeft <= DETECTION_THRESHOLD);
  bool ballDetectedRight = (distanceRight >= 0 && distanceRight <= DETECTION_THRESHOLD);

  if (ballDetectedLeft || ballDetectedRight) {
    // 両方検出された場合は、より近い方を優先
    if (ballDetectedLeft && ballDetectedRight) {
      if (distanceLeft <= distanceRight) {
        executeBlock('L', distanceLeft);
      } else {
        executeBlock('R', distanceRight);
      }
    } else if (ballDetectedLeft) {
      executeBlock('L', distanceLeft);
    } else {
      executeBlock('R', distanceRight);
    }
  }
}

// ========================================
// ブロック実行
// ========================================
void executeBlock(char side, float distance) {
  isBlocking = true;
  blockCount++;

  Serial.println();
  Serial.println("========================================");
  Serial.print("⚽ BALL DETECTED ");
  Serial.print(side == 'L' ? "LEFT" : "RIGHT");
  Serial.print(" (");
  Serial.print(distance, 1);
  Serial.println(" cm)");
  Serial.print("🛡️  Executing block #");
  Serial.println(blockCount);
  Serial.println("========================================");

  if (side == 'L') {
    blockBallLeft();
  } else {
    blockBallRight();
  }

  Serial.println("✅ Block complete");
  Serial.println("Returning to neutral position...");
  Serial.println();

  lastBlockTime = millis();
  isBlocking = false;
}

// ========================================
// 左側超音波センサー読み取り
// ========================================
float readDistanceLeft() {
  digitalWrite(TRIG_PIN_LEFT, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN_LEFT, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN_LEFT, LOW);

  long duration = pulseIn(ECHO_PIN_LEFT, HIGH, 30000);

  if (duration == 0) {
    return -1.0;
  }

  return (duration * 0.034) / 2.0;
}

// ========================================
// 右側超音波センサー読み取り
// ========================================
float readDistanceRight() {
  digitalWrite(TRIG_PIN_RIGHT, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN_RIGHT, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN_RIGHT, LOW);

  long duration = pulseIn(ECHO_PIN_RIGHT, HIGH, 30000);

  if (duration == 0) {
    return -1.0;
  }

  return (duration * 0.034) / 2.0;
}

// ========================================
// ボールブロック: 左側（右後脚BR + 右前脚FRを上げる）
// ========================================
void blockBallLeft() {
  // ボールが左側 → 右側の脚を上げてブロック
  Serial.println("Raising right legs (BR ch7 + FR ch3)...");

  pwm.setPWM(BR_KNEE, 0, BR_KNEE_UP);   // ch7: 380 膝を上げる
  pwm.setPWM(FR_KNEE, 0, FR_KNEE_UP);   // ch3: 380 膝を上げる
  delay(5000);                           // 5秒間保持

  Serial.println("Lowering right legs...");
  pwm.setPWM(BR_KNEE, 0, BR_KNEE_DOWN); // ch7: 150 膝を下ろす
  pwm.setPWM(FR_KNEE, 0, FR_KNEE_DOWN); // ch3: 150 膝を下ろす
  delay(500);
}

// ========================================
// ボールブロック: 右側（左後脚BL + 左前脚FLを上げる）
// ========================================
void blockBallRight() {
  // ボールが右側 → 左側の脚を上げてブロック
  Serial.println("Raising left legs (BL ch5 + FL ch1)...");

  pwm.setPWM(BL_KNEE, 0, BL_KNEE_UP);   // ch5: 150 膝を上げる
  pwm.setPWM(FL_KNEE, 0, FL_KNEE_UP);   // ch1: 100 膝を上げる
  delay(5000);                           // 5秒間保持

  Serial.println("Lowering left legs...");
  pwm.setPWM(BL_KNEE, 0, BL_KNEE_DOWN); // ch5: 400 膝を下ろす
  pwm.setPWM(FL_KNEE, 0, FL_KNEE_DOWN); // ch1: 300 膝を下ろす
  delay(500);
}
