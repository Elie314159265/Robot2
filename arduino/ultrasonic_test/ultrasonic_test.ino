/*
 * 超音波センサ高速測定プログラム（最適化版）
 * HC-SR04センサー用
 * Trig: Pin 8
 * Echo: Pin 9
 *
 * 最適化ポイント:
 * - 測定間隔を60msに短縮（HC-SR04の推奨最小値）
 * - タイムアウトを23msに最適化（最大距離400cm対応）
 * - 高速シリアル出力（簡潔なフォーマット）
 */

const int TRIG_PIN = 8;
const int ECHO_PIN = 9;
const unsigned long MEASUREMENT_INTERVAL = 60;  // 測定間隔（ms）
const unsigned long PULSE_TIMEOUT = 23000;      // タイムアウト（μs、400cm対応）

unsigned long lastMeasurementTime = 0;
unsigned long measurementCount = 0;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // 初期化メッセージ
  Serial.println("=== High-Speed Ultrasonic Sensor Test ===");
  Serial.println("Mode: Optimized for maximum measurement rate");
  Serial.println("Interval: 60ms (~16.7 Hz)");
  Serial.println("Format: D:<distance_cm>");
  Serial.println("Ready");
  Serial.println();

  lastMeasurementTime = millis();
}

void loop() {
  unsigned long currentTime = millis();

  // 測定間隔チェック（60ms経過していれば測定）
  if (currentTime - lastMeasurementTime >= MEASUREMENT_INTERVAL) {
    lastMeasurementTime = currentTime;
    measurementCount++;

    // 高速距離測定
    float distance = measureDistanceFast();

    // 簡潔なフォーマットで出力（パース高速化）
    Serial.print("D:");
    Serial.print(distance, 2);  // 小数点以下2桁
    Serial.print(",T:");
    Serial.print(currentTime);
    Serial.print(",N:");
    Serial.println(measurementCount);
  }

  // その他の処理があればここに追加可能
  // delay()は使用しない（測定間隔はタイマーで制御）
}

float measureDistanceFast() {
  // トリガーパルス送信（最小限の遅延）
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // エコーパルス測定（最適化されたタイムアウト）
  long duration = pulseIn(ECHO_PIN, HIGH, PULSE_TIMEOUT);

  // 距離計算（音速 = 340m/s = 0.034cm/μs、往復なので÷2）
  if (duration == 0) {
    return -1.0;  // タイムアウト（測定範囲外）
  }

  float distance = duration * 0.034 / 2.0;

  // 範囲チェック（2cm～400cm）
  if (distance < 2.0 || distance > 400.0) {
    return -1.0;  // 無効な測定値
  }

  return distance;
}
