#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// 超音波センサー用のピン
const int trigPin = 9;
const int echoPin = 10;

// サーボ用のパルス幅を定義（要調整）
//.setPWMは0~4095の範囲。
//ある資料では150~600が0°～180°のマッピングであった
const int HIP1_NEUTRAL = 263; //Left Side
const int HIP1_FORWARD = 150;
const int HIP1_BACKWARD = 375;

const int HIP2_NEUTRAL = 263; //Right Side
const int HIP2_FORWARD = 375;
const int HIP2_BACKWARD = 150;

const int KNEE_UPL = 150;//左足
const int KNEE_DOWNL = 350;
const int KNEE_UPR = 350;//右足
const int KNEE_DOWNR = 150;

const int DEFAULT1 =0;  //基本的に0固定。
//const int DEFAULT2 =600; 
const int delay1=300;
const int delay2=600; 
const int OBSTACLE_THRESHOLD = 40;
int distance = 0;

// setup
void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(60);
  delay(10);

  // set1：ニュートラル
  moveHipNeutralL(0); 
  moveHipNeutralR(2);
  //moveHipNeutralL(4); 
  moveHipNeutralL(8); 
  moveHipNeutralR(6);
  putDownLegL(1); 
  putDownLegR(3); 
  putDownLegL(5); 
  putDownLegR(7);
  delay(200);
  // 超音波センサーのピン設定
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

// loop
void loop() {
  // 右旋回して
  distance = getDistance();  // 障害物までの距離を測定
  Serial.print("Distance: ");
  Serial.print(distance);
  //Serial.println(" cm");

  // 障害物が近い場合、回避動作を行う
  if (distance < OBSTACLE_THRESHOLD && distance != 0) {
    Serial.println("  Obstacle detected! Turning...");
    turnRightStep();
    creepGaitStep();
    creepGaitStep();
    creepGaitStep();
    creepGaitStep();
    turnLeftStep();
  } else {
    Serial.println("  No obstacle. Moving forward...");
    creepGaitStep();// 障害物がなければ前進
  }

}

// レッグ番号とサーボ番号
// FL: 0(hip),1(knee) / FR:2,3 / BL:4,5 / BR:6,7

// 左足を持ち上げる
void liftLegL(int kneeChannel) {
  pwm.setPWM(kneeChannel,DEFAULT1, KNEE_UPL);
}

// 左足を下ろす
void putDownLegL(int kneeChannel) {
  pwm.setPWM(kneeChannel, DEFAULT1, KNEE_DOWNL);
}
// 右足を持ち上げる
void liftLegR(int kneeChannel) {
  pwm.setPWM(kneeChannel,DEFAULT1, KNEE_UPR);
}

// 右足を下ろす
void putDownLegR(int kneeChannel) {
  pwm.setPWM(kneeChannel, DEFAULT1, KNEE_DOWNR);
}


// ヒップを前に振る
void moveHipForwardL(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP1_FORWARD);
}
void moveHipForwardR(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP2_FORWARD);
}



// ヒップを後ろからニュートラルへに振る
void moveHipBackwardL1(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP1_NEUTRAL);
}
// ヒップをニュートラルから後ろに振る
void moveHipBackwardL2(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP1_BACKWARD);
}

// ヒップを前からニュートラルへに振る
void moveHipBackwardR1(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP2_NEUTRAL);
}
// ヒップをニュートラルから後ろに振る
void moveHipBackwardR2(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP2_BACKWARD);
}




// ヒップを中立に戻す
void moveHipNeutralL(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP1_NEUTRAL);
}

void moveHipNeutralR(int hipChannel) {
  pwm.setPWM(hipChannel, DEFAULT1, HIP2_NEUTRAL);
}

// 右旋回（時計回り）
void turnRightStep() {
  //1
  // 右前脚（FR）後ろに
  delay(delay2);
  liftLegR(3);
  moveHipBackwardR2(2);
  delay(delay1);
  putDownLegR(3);
  delay(delay2);

  // 左後脚（BL）前に
  liftLegL(5);
  //moveHipForwardL(4);
  moveHipForwardL(8);
  delay(delay1);
  putDownLegL(5);

  // 右後脚（BR）後ろに
  delay(delay2);
  liftLegR(7);
  moveHipBackwardR2(6);
  delay(delay1);
  putDownLegR(7);


  delay(delay2);
  // 左前脚（FL）前に
  liftLegL(1);
  moveHipForwardL(0);
  delay(delay1);
  putDownLegL(1);
  delay(delay2);

  // 押し出し
  moveHipBackwardL2(0);
  //moveHipBackwardL2(4);
  moveHipBackwardL2(8);
  moveHipForwardR(2);
  moveHipForwardR(6);

  DefaultLeg();

  //2
  // 右前脚（FR）後ろに
  delay(delay2);
  liftLegR(3);
  moveHipBackwardR2(2);
  delay(delay1);
  putDownLegR(3);
  delay(delay2);

  // 左後脚（BL）前に
  liftLegL(5);
  //moveHipForwardL(4);
  moveHipForwardL(8);
  delay(delay1);
  putDownLegL(5);

// 右後脚（BR）後ろに
  delay(delay2);
  liftLegR(7);
  moveHipBackwardR2(6);
  delay(delay1);
  putDownLegR(7);
  delay(delay2);


  // 左前脚（FL）前に
  liftLegL(1);
  moveHipForwardL(0);
  delay(delay1);
  putDownLegL(1);
  delay(delay2);

  // 押し出し
  moveHipBackwardL2(0);
  //moveHipBackwardL2(4);
  moveHipBackwardL2(8);
  moveHipForwardR(2);
  moveHipForwardR(6);
}

// 左旋回（反時計回り）
void turnLeftStep() {
  //1
  // 右前脚（FR）前に
  liftLegR(3);
  moveHipForwardR(2);
  delay(delay1);
  putDownLegR(3);
  delay(delay2);

  // 左後脚（BL）後ろに
  liftLegL(5);
  //moveHipBackwardL2(4);
  moveHipBackwardL2(8);
  delay(delay1);
  putDownLegL(5);
  delay(delay2);

  // 右後脚（BR）前に
  liftLegR(7);
  moveHipForwardR(6);
  delay(delay1);
  putDownLegR(7);
  delay(delay2);

  // 左前脚（FL）後ろに
  liftLegL(1);
  moveHipBackwardL2(0);
  delay(delay1);
  putDownLegL(1);
  delay(delay2);

  // 押し出し
  moveHipBackwardR2(2);
  moveHipBackwardR2(6);
  moveHipForwardL(0);
  moveHipForwardL(8);
  //moveHipForwardL(4);
  delay(delay2);
  //2
  // 右前脚（FR）前に
  liftLegR(3);
  moveHipForwardR(2);
  delay(delay1);
  putDownLegR(3);
  delay(delay2);

  // 左後脚（BL）後ろに
  liftLegL(5);
  //moveHipBackwardL2(4);
  moveHipBackwardL2(8);
  delay(delay1);
  putDownLegL(5);
  delay(delay2);

  // 右後脚（BR）前に
  liftLegR(7);
  moveHipForwardR(6);
  delay(delay1);
  putDownLegR(7);
  delay(delay2);

  // 左前脚（FL）後ろに
  liftLegL(1);
  moveHipBackwardL2(0);
  delay(delay1);
  putDownLegL(1);
  delay(delay2);

  // 押し出し
  moveHipBackwardR2(2);
  moveHipBackwardR2(6);
  moveHipForwardL(0);
  moveHipForwardL(8);
  //moveHipForwardL(4);
  delay(delay2);
}


void DefaultLeg(){
  //右前脚をニュートラルに
  delay(delay2);
  liftLegR(3);
  moveHipNeutralR(2);
  delay(delay1);
  putDownLegR(3);
  delay(delay2);

  //左後脚をニュートラルに
  delay(delay2);
  liftLegL(5);
  //moveHipForwardL(4);
  moveHipNeutralL(8);
  delay(delay1);
  putDownLegL(5);

  //左前脚をニュートラルに
  delay(delay2);
  liftLegL(1);
  moveHipNeutralL(0);
  delay(delay1);
  putDownLegL(1);
  delay(delay2);

  // step4：右後脚（BR=6,7）を前に
  delay(delay2);
  liftLegR(7);
  moveHipNeutralR(6);
  delay(delay1);
  putDownLegR(7);
}


// クリープゲイトの1周期
void creepGaitStep() {
  // step1：右前脚（FR=2,3）を前に
  delay(delay2);
  liftLegR(3);
  moveHipForwardR(2);
  delay(delay1);
  putDownLegR(3);
  delay(delay2);

  // move1：本体押し出し
  moveHipBackwardL2(0);
  moveHipBackwardR1(6);
  //moveHipBackwardL2(4);
  moveHipBackwardL2(8);
  moveHipBackwardR1(2);

  // step2：左後脚（BL=4,5）を前に
  delay(delay2);
  liftLegL(5);
  //moveHipForwardL(4);
  moveHipForwardL(8);
  delay(delay1);
  putDownLegL(5);

  // step3：左前脚（FL=0,1）を前に
  delay(delay2);
  liftLegL(1);
  moveHipForwardL(0);
  delay(delay1);
  putDownLegL(1);
  delay(delay2);
  // move2：本体押し出し
  moveHipBackwardL1(0);
  moveHipBackwardR2(6);
  //moveHipBackwardL1(4);
  moveHipBackwardL1(8);
  moveHipBackwardR2(2);

  // step4：右後脚（BR=6,7）を前に
  delay(delay2);
  liftLegR(7);
  moveHipForwardR(6);
  delay(delay1);
  putDownLegR(7);
}

// 超音波センサーで距離を測定する関数
long getDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  long distance = duration * 0.034 / 2;
  
  return distance;
}


/*
右旋回制御フロー（時計回り）


左前脚（FL=0,1）を持ち上げる
　→ liftLeg(1);

左前脚（FL=0,1）を前方（右前方向）に振り出す
　→ moveHipForward(0);

左前脚（FL=0,1）を地面に下ろす
　→ putDownLeg(1);

本体を押し出す
　- 左前脚（FL=0）と左後脚（BL=4）を「後ろに振る」
　- 右前脚（FR=2）と右後脚（BR=6）を「ニュートラルに戻す」
　→ moveHipBackward(0); moveHipBackward(4); moveHipNeutral(2); moveHipNeutral(6);

左後脚（BL=4,5）を持ち上げる
　→ liftLeg(5);

左後脚（BL=4,5）を前方（右後方向）に振り出す
　→ moveHipForward(4);

左後脚（BL=4,5）を地面に下ろす
　→ putDownLeg(5);

本体を押し出す（再度）
　- 左前脚（FL=0）と左後脚（BL=4）を「後ろに振る」
　- 右前脚（FR=2）と右後脚（BR=6）を「ニュートラルに戻す」
　→ moveHipBackward(0); moveHipBackward(4); moveHipNeutral(2); moveHipNeutral(6);

*/

/*
左旋回制御フロー（反時計回り）


右前脚（FR=2,3）を持ち上げる

→ liftLeg(3);

右前脚（FR=2,3）を前方（左前方向）に振り出す

→ moveHipForward(2);

右前脚（FR=2,3）を地面に下ろす

→ putDownLeg(3);

本体を押し出す

右前脚（FR=2）と右後脚（BR=6）を「後ろに振る」

左前脚（FL=0）と左後脚（BL=4）を「ニュートラルに戻す」

→ moveHipBackward(2); moveHipBackward(6); moveHipNeutral(0); moveHipNeutral(4);

右後脚（BR=6,7）を持ち上げる

→ liftLeg(7);

右後脚（BR=6,7）を前方（左後方向）に振り出す

→ moveHipForward(6);

右後脚（BR=6,7）を地面に下ろす

→ putDownLeg(7);

本体を押し出す（再度）

右前脚（FR=2）と右後脚（BR=6）を「後ろに振る」

左前脚（FL=0）と左後脚（BL=4）を「ニュートラルに戻す」

→ moveHipBackward(2); moveHipBackward(6); moveHipNeutral(0); moveHipNeutral(4);


*/
