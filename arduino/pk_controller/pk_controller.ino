/*
PK Controller - Arduino Uno Firmware for Ball Blocking
PK課題専用のArduinoファームウェア

PWM values based on walk_program_refactored_20260109.ino

Hardware:
- PCA9685 Servo Driver (I2C)
- Ultrasonic Distance Sensors (HC-SR04) x2
- 8 Servo Motors (4 legs x 2 joints)

Protocol:
- Serial communication with RaspberryPi (9600 baud)
- Command format: [COMMAND][PARAMS]\n
*/

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// ========================================
// サーボチャンネル定義（walk_program_refactored準拠）
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
// PWM値定義（walk_program_refactored_20260109.ino準拠）
// ========================================

// --- 左前脚 (FL) ---
const int FL_HIP_NEUTRAL = 160;  // ch0: デフォルト160
const int FL_KNEE_UP = 100;
const int FL_KNEE_DOWN = 300;    // ch1: デフォルト300

// --- 右前脚 (FR) ---
const int FR_HIP_NEUTRAL = 300;  // ch2: デフォルト300
const int FR_KNEE_UP = 380;
const int FR_KNEE_DOWN = 150;    // ch3: デフォルト150

// --- 左後脚 (BL) - ボールブロック用 ---
const int BL_HIP_NEUTRAL = 290;  // ch8: デフォルト290
const int BL_KNEE_UP = 150;      // 膝を上げた時
const int BL_KNEE_DOWN = 400;    // ch5: デフォルト400

// --- 右後脚 (BR) - ボールブロック用 ---
const int BR_HIP_NEUTRAL = 230;  // ch6: デフォルト230
const int BR_KNEE_UP = 380;      // 膝を上げた時
const int BR_KNEE_DOWN = 150;    // ch7: デフォルト150

// ========================================
// 超音波センサーピン定義
// ========================================
// 左側センサー (HC-SR04)
//   VCC  -> Arduino 5V
//   GND  -> Arduino GND
//   Trig -> Arduino D8
//   Echo -> Arduino D9
const int TRIG_PIN_LEFT = 8;
const int ECHO_PIN_LEFT = 9;

// 右側センサー (HC-SR04)
//   VCC  -> Arduino 5V
//   GND  -> Arduino GND
//   Trig -> Arduino D10
//   Echo -> Arduino D11
const int TRIG_PIN_RIGHT = 10;
const int ECHO_PIN_RIGHT = 11;

// ========================================
// 設定
// ========================================
const int BAUD_RATE = 9600;
const int SERVO_FREQ = 60;

// ========================================
// セットアップ
// ========================================
void setup() {
  Serial.begin(BAUD_RATE);

  // PWMドライバー初期化
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(10);

  // 超音波センサーピン設定
  pinMode(TRIG_PIN_LEFT, OUTPUT);
  pinMode(ECHO_PIN_LEFT, INPUT);
  pinMode(TRIG_PIN_RIGHT, OUTPUT);
  pinMode(ECHO_PIN_RIGHT, INPUT);

  // 全脚をニュートラル位置に初期化（walk_program_refactored準拠）
  initializeLegs();

  Serial.println("PK Controller initialized");
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
}

// ========================================
// メインループ
// ========================================
void loop() {
  if (Serial.available() > 0) {
    processCommand();
  }
  delay(10);
}

// ========================================
// コマンド処理
// ========================================
void processCommand() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd.length() == 0) {
    return;
  }

  char command = cmd.charAt(0);

  switch (command) {
    case 'S': // サーボコマンド: S[ID:2][PWM:3]
      if (cmd.length() == 6) {
        int servoId = cmd.substring(1, 3).toInt();
        int pwmValue = cmd.substring(3, 6).toInt();
        setServoPWM(servoId, pwmValue);
        Serial.println("OK");
      } else {
        Serial.println("ERR");
      }
      break;

    case 'D': // 距離センサー読み取り: DL or DR
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

        int distanceMM = (int)(distance * 10);
        char buffer[10];
        sprintf(buffer, "D%05d", distanceMM);
        Serial.println(buffer);
      } else {
        Serial.println("ERR");
      }
      break;

    case 'B': // ボールブロック: BL or BR
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

    case 'I': // 初期化: I
      initializeLegs();
      Serial.println("OK");
      break;

    default:
      Serial.println("ERR");
      break;
  }
}

// ========================================
// サーボPWM直接設定
// ========================================
void setServoPWM(int servoId, int pwmValue) {
  if (servoId < 0 || servoId > 15) {
    return;
  }
  if (pwmValue < 100 || pwmValue > 600) {
    return;
  }
  pwm.setPWM(servoId, 0, pwmValue);
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
// ボールブロック: 左側（右後脚BR ch7 + 右前脚FR ch3を上げる）
// ========================================
void blockBallLeft() {
  // ボールが画面左側 → 右後脚(BR ch7) + 右前脚(FR ch3)を上げてブロック
  // BR_KNEE (ch 7): DOWN=150 → UP=380
  // FR_KNEE (ch 3): DOWN=150 → UP=380
  pwm.setPWM(BR_KNEE, 0, BR_KNEE_UP);   // ch7: 380 膝を上げる
  pwm.setPWM(FR_KNEE, 0, FR_KNEE_UP);   // ch3: 380 膝を上げる
  delay(5000);                           // 5秒間保持
  pwm.setPWM(BR_KNEE, 0, BR_KNEE_DOWN); // ch7: 150 膝を下ろす
  pwm.setPWM(FR_KNEE, 0, FR_KNEE_DOWN); // ch3: 150 膝を下ろす
}

// ========================================
// ボールブロック: 右側（左後脚BL ch5 + 左前脚FL ch1を上げる）
// ========================================
void blockBallRight() {
  // ボールが画面右側 → 左後脚(BL ch5) + 左前脚(FL ch1)を上げてブロック
  // BL_KNEE (ch 5): DOWN=400 → UP=150
  // FL_KNEE (ch 1): DOWN=300 → UP=100
  pwm.setPWM(BL_KNEE, 0, BL_KNEE_UP);   // ch5: 150 膝を上げる
  pwm.setPWM(FL_KNEE, 0, FL_KNEE_UP);   // ch1: 100 膝を上げる
  delay(5000);                           // 5秒間保持
  pwm.setPWM(BL_KNEE, 0, BL_KNEE_DOWN); // ch5: 400 膝を下ろす
  pwm.setPWM(FL_KNEE, 0, FL_KNEE_DOWN); // ch1: 300 膝を下ろす
}
