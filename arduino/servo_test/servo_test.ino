/*
Servo Driver Test - PCA9685 and Servo Motor Test
Based on walk_program.ino settings

Hardware:
- PCA9685 Servo Driver (I2C address 0x40)
- Multiple Servo Motors
- Arduino Uno

Test sequence:
1. Initialize PCA9685
2. Test individual servos one by one
3. Sweep test for all servos
4. Report results via Serial
*/

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// PCA9685 I2C address
#define SERVO_DRIVER_ADDR 0x40

// Servo configuration (from walk_program.ino)
#define SERVO_MIN 150    // Min PWM value (0 degrees)
#define SERVO_MAX 600    // Max PWM value (180 degrees)
#define SERVO_NEUTRAL 375  // Mid PWM value (90 degrees)
#define SERVO_FREQ 60    // 60Hz for servos (from walk_program.ino)

#define NUM_SERVOS 8     // Test servos 0-7 (for 4-leg robot)

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(SERVO_DRIVER_ADDR);

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("=== PCA9685 Servo Driver Test ===");
  Serial.println();

  // Initialize I2C and PCA9685
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);

  delay(500);

  Serial.println("PCA9685 initialized");
  Serial.print("Frequency: ");
  Serial.print(SERVO_FREQ);
  Serial.println(" Hz");
  Serial.print("PWM Range: ");
  Serial.print(SERVO_MIN);
  Serial.print(" - ");
  Serial.println(SERVO_MAX);
  Serial.println();

  // Set all servos to neutral position
  Serial.println("Setting all servos to NEUTRAL position...");
  for (int i = 0; i < NUM_SERVOS; i++) {
    pwm.setPWM(i, 0, SERVO_NEUTRAL);
    delay(100);
  }
  Serial.println("Done.");
  Serial.println();

  delay(2000);
}

void loop() {
  // Test menu
  Serial.println("=== Servo Test Menu ===");
  Serial.println("1. Test all servos (sweep)");
  Serial.println("2. Test individual servo");
  Serial.println("3. Set all to NEUTRAL");
  Serial.println("4. Set all to MIN");
  Serial.println("5. Set all to MAX");
  Serial.println();
  Serial.println("Enter command:");

  // Wait for serial input
  while (Serial.available() == 0) {
    delay(100);
  }

  char cmd = Serial.read();
  // Clear remaining newline
  while (Serial.available() > 0) {
    Serial.read();
  }

  switch (cmd) {
    case '1':
      testAllServosSweep();
      break;

    case '2':
      testIndividualServo();
      break;

    case '3':
      setAllServos(SERVO_NEUTRAL);
      Serial.println("All servos set to NEUTRAL");
      break;

    case '4':
      setAllServos(SERVO_MIN);
      Serial.println("All servos set to MIN");
      break;

    case '5':
      setAllServos(SERVO_MAX);
      Serial.println("All servos set to MAX");
      break;

    default:
      Serial.println("Invalid command");
      break;
  }

  Serial.println();
  delay(1000);
}

// Test all servos with sweep motion
void testAllServosSweep() {
  Serial.println("Testing all servos with sweep...");

  for (int servoNum = 0; servoNum < NUM_SERVOS; servoNum++) {
    Serial.print("Servo ");
    Serial.print(servoNum);
    Serial.println(":");

    // MIN position
    Serial.println("  -> MIN");
    pwm.setPWM(servoNum, 0, SERVO_MIN);
    delay(800);

    // NEUTRAL position
    Serial.println("  -> NEUTRAL");
    pwm.setPWM(servoNum, 0, SERVO_NEUTRAL);
    delay(800);

    // MAX position
    Serial.println("  -> MAX");
    pwm.setPWM(servoNum, 0, SERVO_MAX);
    delay(800);

    // Back to NEUTRAL
    Serial.println("  -> NEUTRAL");
    pwm.setPWM(servoNum, 0, SERVO_NEUTRAL);
    delay(500);
  }

  Serial.println("Sweep test complete!");
}

// Test individual servo
void testIndividualServo() {
  Serial.println("Enter servo number (0-7):");

  while (Serial.available() == 0) {
    delay(100);
  }

  int servoNum = Serial.parseInt();

  // Clear buffer
  while (Serial.available() > 0) {
    Serial.read();
  }

  if (servoNum < 0 || servoNum >= NUM_SERVOS) {
    Serial.println("Invalid servo number");
    return;
  }

  Serial.print("Testing servo ");
  Serial.println(servoNum);

  // Sweep motion
  Serial.println("MIN -> NEUTRAL -> MAX -> NEUTRAL");

  pwm.setPWM(servoNum, 0, SERVO_MIN);
  delay(1000);

  pwm.setPWM(servoNum, 0, SERVO_NEUTRAL);
  delay(1000);

  pwm.setPWM(servoNum, 0, SERVO_MAX);
  delay(1000);

  pwm.setPWM(servoNum, 0, SERVO_NEUTRAL);
  delay(500);

  Serial.println("Test complete");
}

// Set all servos to specific PWM value
void setAllServos(int pwmValue) {
  for (int i = 0; i < NUM_SERVOS; i++) {
    pwm.setPWM(i, 0, pwmValue);
    delay(50);
  }
}
