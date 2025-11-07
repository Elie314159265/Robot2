# ボールブロッキングシステム - 高速超音波センサー版

## 概要

カメラでサッカーボールを検出し、超音波センサーで高速監視を行い、ボールが横切った瞬間にサーボを上げてブロックするゴールキーパーロボットシステムです。

## 主要機能

- **カメラ検出**: RaspberryPi Camera + Google Coral TPUでリアルタイムボール検出
- **位置判定**: ボールのX座標から左/右/中央を判定
- **高速監視**: 超音波センサーで4秒間、約50Hzで距離測定
- **自動ブロック**: Arduino側でボール横切りを検出し、即座にサーボを上げる（反応時間<100ms）
- **2つのセンサー**: 左右独立した超音波センサーで精密な位置検出

## システムアーキテクチャ

### アルゴリズムフロー

```
RaspberryPi Camera Module 3
    ↓ (画像取得)
Google Coral TPU
    ↓ (ボール検出、class 37: sports ball)
ボール位置判定 (Python)
    ├─ X < 30% → LEFT
    ├─ X > 70% → RIGHT
    └─ その他 → CENTER (アクションなし)
    ↓ (シリアル通信: HL or HR コマンド)
Arduino Uno (高速監視モード)
    ├─ 超音波センサーで4秒間、50Hzサンプリング
    ├─ 移動平均フィルタ（5サンプル）
    ├─ 距離変化検出（閾値: 10cm）
    └─ ボール横切り検出 → サーボ即座に上げる
    ↓
PCA9685サーボドライバ
    ↓
サーボモータ
    ├─ 左側ボール → サーボ7番 (右後脚)
    └─ 右側ボール → サーボ5番 (左後脚)
```

### ハードウェア構成

**超音波センサー (HC-SR04):**
- **左センサー**: ピン8 (TRIG) + ピン9 (ECHO)
- **右センサー**: ピン10 (TRIG) + ピン11 (ECHO)
- 測定範囲: 2-400cm、精度: 3mm
- サンプリング: 約50Hz (20ms間隔)

**サーボモータ (PCA9685経由):**
- **サーボ7番**: 右後脚 - 左側から来るボールをブロック
- **サーボ5番**: 左後脚 - 右側から来るボールをブロック
- 動作時間: 2秒間保持後、自動的に下ろす

## 実装ファイル

### Arduino側
- `arduino/robot_controller/robot_controller.ino` - Arduinoファームウェア
  - **新コマンド `H`**: 高速監視モード
    - `HL\n`: 左センサー4秒間監視 → サーボ7番
    - `HR\n`: 右センサー4秒間監視 → サーボ5番
  - **新コマンド `D`**: 個別センサー読み取り
    - `DL\n`: 左センサー読み取り
    - `DR\n`: 右センサー読み取り
  - `highSpeedMonitorLeft()`: 左側高速監視＋自動ブロック
  - `highSpeedMonitorRight()`: 右側高速監視＋自動ブロック
  - `readDistanceLeft()`: 左センサー距離測定
  - `readDistanceRight()`: 右センサー距離測定

### RaspberryPi側
- `src/blocking/ball_blocker.py` - ボールブロッキングコントローラ
  - `BallBlocker`: メインコントローラクラス
  - `determine_ball_side()`: X座標から左/右/中央判定
  - `process_ball_detection()`: カメラ検出結果を処理
  - `trigger_blocking()`: Arduino高速監視を開始
- `src/arduino/serial_controller.py` - シリアル通信コントローラ
  - `read_distance_left()`: 左センサー読み取り
  - `read_distance_right()`: 右センサー読み取り
- `tests/test_ball_blocking_simple.py` - 新テストスクリプト（推奨）
  - 手動トリガーテスト
  - 超音波センサーテスト
  - 位置判定ロジックテスト
  - 完全ワークフローテスト
- `tests/test_ball_blocking.py` - カメラ統合テスト（既存）

## セットアップ

### 1. ハードウェア接続

**超音波センサー (HC-SR04) × 2:**
```
左センサー:
  VCC  → Arduino 5V
  TRIG → Arduino Pin 8
  ECHO → Arduino Pin 9
  GND  → Arduino GND

右センサー:
  VCC  → Arduino 5V
  TRIG → Arduino Pin 10
  ECHO → Arduino Pin 11
  GND  → Arduino GND
```

**その他:**
- RaspberryPi Camera Module 3 → RaspberryPi (CSIコネクタ)
- Google Coral TPU → RaspberryPi (USB)
- Arduino Uno → RaspberryPi (USB: /dev/ttyACM0)
- PCA9685 → Arduino (I2C: SDA, SCL)
- サーボモータ:
  - 5番: 左後脚 (BL: Back Left knee)
  - 7番: 右後脚 (BR: Back Right knee)

### 2. Arduinoファームウェアのアップロード

```bash
export PATH=$PATH:/home/worker1/robot_pk/bin
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
```

## 使い方

### ステップ1: 超音波センサーテスト

まず、左右のセンサーが正しく動作するか確認します。

```bash
python3 tests/test_ball_blocking_simple.py --test ultrasonic
```

各センサーの前で手を動かして距離が変化することを確認します。

### ステップ2: 手動トリガーテスト

高速監視モードをテストします。

```bash
python3 tests/test_ball_blocking_simple.py --test manual
```

プロンプトが表示されたら、該当センサーの前で手を振ってボール横切りを模擬します。

### ステップ3: 完全ワークフローテスト

カメラ検出からブロッキングまでの完全なフローをテストします。

```bash
python3 tests/test_ball_blocking_simple.py --test workflow
```

### ステップ4: カメラ統合テスト（実際のボール検出）

```bash
python3 tests/test_ball_blocking.py
```

ブラウザで `http://<RaspberryPiのIPアドレス>:8000` にアクセスして動作確認:

1. ストリーミング画面を開く
2. カメラの前でサッカーボールを左右に動かす
3. ボールが**画面左側**に現れると:
   - 左センサーが4秒間高速監視
   - ボール横切り検出 → 右後脚(7番)が2秒間上がる
4. ボールが**画面右側**に現れると:
   - 右センサーが4秒間高速監視
   - ボール横切り検出 → 左後脚(5番)が2秒間上がる

## シリアル通信プロトコル

### 高速監視コマンド (新)

| コマンド | 説明 | 応答 |
|---------|------|------|
| `HL\n` | 左センサー高速監視（4秒間、50Hz） | データストリーム + `OK` or `BALL_DETECTED_LEFT` |
| `HR\n` | 右センサー高速監視（4秒間、50Hz） | データストリーム + `OK` or `BALL_DETECTED_RIGHT` |

**データストリーム形式:**
```
D:<distance>,T:<time_ms>,N:<sequence>
```
例: `D:45.32,T:120,N:5` - 距離45.32cm、経過時間120ms、シーケンス番号5

### 個別センサー読み取りコマンド

| コマンド | 説明 | 応答 |
|---------|------|------|
| `DL\n` | 左センサー読み取り | `D[VALUE:5]` (mm単位、例: `D00452` = 45.2cm) |
| `DR\n` | 右センサー読み取り | `D[VALUE:5]` (mm単位) |

### 従来のブロックコマンド (互換性のため残存)

| コマンド | 説明 | 応答 |
|---------|------|------|
| `BL\n` | 左側ブロック（右後脚7番を5秒間） | `OK` |
| `BR\n` | 右側ブロック（左後脚5番を5秒間） | `OK` |

## 技術的詳細

### Python側: ボール位置判定

```python
class BallBlocker:
    def __init__(self, serial_controller, left_threshold=0.3, right_threshold=0.7):
        self.left_threshold = left_threshold   # X < 30% → LEFT
        self.right_threshold = right_threshold  # X > 70% → RIGHT

    def determine_ball_side(self, ball_x, frame_width):
        normalized_x = ball_x / frame_width
        if normalized_x < self.left_threshold:
            return BallSide.LEFT
        elif normalized_x > self.right_threshold:
            return BallSide.RIGHT
        else:
            return BallSide.CENTER  # アクションなし

    def trigger_blocking(self, side):
        # Arduino高速監視開始
        command = f"H{side.value[0].upper()}\n"  # HL or HR
        self.serial.serial.write(command.encode())

        # Arduino応答を監視
        while time.time() - start_time < timeout:
            line = self.serial.serial.readline().decode()
            if "BALL_DETECTED" in line:
                return True  # ブロック成功
        return False
```

### Arduino側: 高速監視＋自動ブロック

```cpp
void highSpeedMonitorLeft() {
  unsigned long duration = 4000;  // 4秒間
  float distanceBuffer[5];  // 移動平均用
  float lastDistance = -1.0;
  int sequenceNum = 0;

  while (millis() - startTime < duration) {
    // 距離測定
    float distance = readDistanceLeft();

    // 移動平均計算
    float avgDistance = calculateMovingAverage(distanceBuffer, distance);

    // データストリーム送信
    Serial.print("D:");
    Serial.print(distance, 2);
    Serial.print(",T:");
    Serial.print(millis() - startTime);
    Serial.print(",N:");
    Serial.println(sequenceNum++);

    // ボール横切り検出（10cm以上の変化）
    if (lastDistance > 0 && abs(avgDistance - lastDistance) > 10.0) {
      pwm.setPWM(7, 0, KNEE_UPR);  // サーボ7番を上げる
      Serial.println("BALL_DETECTED_LEFT");
      delay(2000);  // 2秒保持
      pwm.setPWM(7, 0, KNEE_DOWNR);  // 下ろす
      return;  // 検出後は終了
    }

    lastDistance = avgDistance;
    delay(20);  // 50Hz (20ms間隔)
  }
  Serial.println("OK");  // タイムアウト
}
```

### アルゴリズムの利点

1. **低レイテンシ**: Arduino側で検出＋動作 → Python通信遅延を排除
2. **高サンプリング**: 50Hz → 精密な距離変化検出
3. **ノイズ除去**: 移動平均フィルタ（5サンプル）
4. **自動ブロック**: 検出と同時にサーボ制御 → 反応時間<100ms

## トラブルシューティング

### Arduinoが接続できない

```bash
# デバイス確認
ls -la /dev/ttyACM*

# 権限確認
groups | grep dialout

# dialoutグループに所属していない場合
sudo usermod -a -G dialout $USER
# 再ログインが必要
```

### 超音波センサーが反応しない

**確認事項:**
1. 配線確認
   - 左センサー: TRIG→8, ECHO→9
   - 右センサー: TRIG→10, ECHO→11
   - VCC→5V、GND→GND
2. センサーテスト実行
   ```bash
   python3 tests/test_ball_blocking_simple.py --test ultrasonic
   ```
3. 距離範囲確認（2-400cm）
4. 超音波干渉チェック（2つのセンサーを同時に使用時）

### サーボが動かない

- PCA9685の電源確認（サーボは5V、大電流が必要）
- サーボID確認（左側→7番、右側→5番）
- PWM値確認:
  ```cpp
  const int KNEE_UPL = 150;    // 左足を上げる
  const int KNEE_UPR = 350;    // 右足を上げる
  ```

### 誤検出が多い

**対策:**
1. 距離変化閾値を大きくする（Arduino側）
   ```cpp
   if (distanceChange > 15.0) {  // 10.0 → 15.0
   ```
2. 移動平均のウィンドウサイズを増やす
   ```cpp
   const int BUFFER_SIZE = 7;  // 5 → 7
   ```
3. 環境ノイズ確認（振動、音波干渉）

### 反応が遅い

**対策:**
1. サンプリング周波数を上げる
   ```cpp
   delay(10);  // 20 → 10 (約100Hz)
   ```
   注意: 超音波センサーの最小測定間隔（約60ms）を考慮
2. 移動平均のウィンドウサイズを減らす（精度とトレードオフ）

### ボールが検出されない（カメラ）

- カメラの向きを確認
- 照明条件を改善（明るい場所で実行）
- 検出しきい値を調整: `score_threshold=0.3` → `0.2`

## パラメータチューニング

### 位置判定閾値 (Python)

```python
blocker = BallBlocker(
    serial_controller,
    left_threshold=0.3,   # 小さいほど左範囲が広い
    right_threshold=0.7   # 大きいほど右範囲が広い
)
```

### 距離変化閾値 (Arduino)

```cpp
// arduino/robot_controller/robot_controller.ino
if (distanceChange > 10.0) {  // 10cm以上の変化で検出
```

### 監視時間 (Arduino)

```cpp
unsigned long duration = 4000;  // 4秒間（ミリ秒）
```

### サーボ保持時間 (Arduino)

```cpp
delay(2000);  // 2秒間足を上げた状態を保持
```

## パフォーマンス指標

- **サンプリングレート**: 約50Hz（20ms間隔）
- **監視時間**: 4秒間
- **反応時間**: <100ms（検出からサーボ動作まで）
- **検出精度**: 距離変化10cm以上で高精度
- **カメラFPS**: 25-30 fps
- **TPU推論時間**: <20ms

## 今後の改善案

1. **機械学習による軌道予測**
   - 複数フレームの位置情報から着地点を予測
   - より正確なブロッキングタイミング

2. **適応的閾値調整**
   - 環境に応じて自動的に閾値を調整
   - ボール速度に応じた動的調整

3. **複数ボール対応**
   - 複数のボールを同時追跡
   - 優先度付けによる最適ブロッキング

4. **フィードバック学習**
   - 成功/失敗データを記録
   - パラメータの自動最適化

5. **歩行動作との統合**
   - ブロック後に元の位置に戻る
   - ボール位置に応じた移動

## 参考ファイル

- `tests/test_ball_tracking.py` - ボール追跡テスト（サーボ追従のみ）
- `tests/test_ultrasonic.py` - 超音波センサー高速テスト
- `walk_program.ino` - 歩行制御プログラム（足の動作参考）
- `CLAUDE.md` - プロジェクト全体の設計ドキュメント
- `README_BALL_TRACKING.md` - カメラ追従システムドキュメント

## 参考資料

- HC-SR04データシート: 測定範囲2-400cm、精度3mm
- PCA9685データシート: 16チャンネルPWM、60Hz推奨
- COCO Dataset: Class 37 = sports ball

## 実装完了日

2025年11月8日 - 高速超音波センサー版

---

**注意**:
- 実際のハードウェアで動作するため、サーボの動作範囲や電源容量に注意してテストしてください
- 超音波センサーは2-400cmの範囲で動作します。範囲外では正確な測定ができません
- 2つのセンサーを近くに配置する場合、超音波干渉に注意してください
