# ボールブロッキングシステム - クイックスタートガイド

このガイドでは、ボールブロッキングシステムを手作業でコンパイル・実行する方法を説明します。

## 目次

1. [事前準備](#事前準備)
2. [Arduinoファームウェアのコンパイル＆アップロード](#arduinoファームウェアのコンパイルアップロード)
3. [テスト実行](#テスト実行)
4. [トラブルシューティング](#トラブルシューティング)

---

## 事前準備

### ハードウェア確認

1. **超音波センサー × 2** (HC-SR04)
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

2. **Arduino Uno** → RaspberryPi (USB: /dev/ttyACM0)

3. **PCA9685サーボドライバ** → Arduino (I2C)
   - サーボ5番: 左後脚
   - サーボ7番: 右後脚

4. **RaspberryPi Camera Module 3**

5. **Google Coral TPU**

### ソフトウェア確認

```bash
# Arduino CLIがインストールされているか確認
which arduino-cli

# Pythonライブラリの確認
python3 -c "import serial; import picamera2; import pycoral; print('All libraries OK')"
```

---

## Arduinoファームウェアのコンパイル＆アップロード

### ステップ1: プロジェクトディレクトリに移動

```bash
cd /home/worker1/robot_pk
```

### ステップ2: PATHの設定

```bash
export PATH=$PATH:/home/worker1/robot_pk/bin
```

### ステップ3: コンパイル

```bash
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller
```

**期待される出力:**
```
最大32256バイトのフラッシュメモリのうち、スケッチが12768バイト（39%）を使っています。
最大2048バイトのRAMのうち、グローバル変数が517バイト（25%）を使っていて、ローカル変数で1531バイト使うことができます。
```

### ステップ4: Arduinoに接続確認

```bash
# Arduinoが接続されているか確認
ls -la /dev/ttyACM*
```

**期待される出力:**
```
crw-rw---- 1 root dialout 166, 0 11月  8 01:30 /dev/ttyACM0
```

もし権限エラーが出る場合:
```bash
sudo usermod -a -G dialout $USER
# その後、ログアウト・ログインが必要
```

### ステップ5: アップロード

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
```

**期待される出力:**
```
New upload port: /dev/ttyACM0 (serial)
```

✅ アップロード成功！

---

## テスト実行

### テスト1: 超音波センサーテスト

左右のセンサーが正しく動作するか確認します。

```bash
python3 tests/test_ball_blocking_simple.py --test ultrasonic
```

**何をテストするか:**
- 左センサー（ピン8,9）の距離測定
- 右センサー（ピン10,11）の距離測定
- 各センサーの前で手を動かして距離が変化することを確認

**期待される出力:**
```
[ 1] Left (8,9):   70.3 cm | Right (10,11):   34.4 cm
[ 2] Left (8,9):   70.3 cm | Right (10,11):   34.4 cm
...
```

**終了方法:** `Ctrl+C`

---

### テスト2: 位置判定ロジックテスト

カメラ座標から左/右/中央の判定が正しく動作するか確認します。

```bash
python3 tests/test_ball_blocking_simple.py --test sides
```

**何をテストするか:**
- X座標 < 30% → LEFT
- X座標 > 70% → RIGHT
- その他 → CENTER

**期待される出力:**
```
✓ X= 50px (0.078) -> LEFT   (expected: LEFT)
✓ X=150px (0.234) -> LEFT   (expected: LEFT)
✓ X=320px (0.500) -> CENTER (expected: CENTER)
✓ X=500px (0.781) -> RIGHT  (expected: RIGHT)
```

---

### テスト3: 手動トリガーテスト（自動版）

高速監視モードを自動的にテストします。

```bash
python3 tests/test_ball_blocking_auto.py
```

**何をテストするか:**
1. 左センサー監視（4秒間）
   - プロンプト表示後、**左センサーの前で手を振る**
   - ボール横切り検出 → サーボ7番が上がる

2. 右センサー監視（4秒間）
   - プロンプト表示後、**右センサーの前で手を振る**
   - ボール横切り検出 → サーボ5番が上がる

**期待される出力（成功時）:**
```
Testing LEFT side (pins 8,9 sensor -> servo 7)
Arduino will monitor for 4 seconds...
>>> WAVE YOUR HAND IN FRONT OF THE LEFT SENSOR NOW! <<<

Monitoring completed in 5.4 seconds
✅ SUCCESS! Ball crossing detected on LEFT side!
   Servo 7 was raised for 2 seconds
```

**重要:** プロンプトが表示されたら、すぐに該当センサーの前で手を振ってください！

---

### テスト4: カメラ統合テスト

実際のカメラでボールを検出し、ブロッキングを行います。

```bash
python3 tests/test_ball_blocking.py
```

**何をテストするか:**
- カメラでボール検出（TPU使用）
- ボールの位置判定（左/右）
- 旧バージョンのブロッキング（従来のBLコマンド使用）

**Webインターフェース:**

サーバー起動後、ブラウザで以下にアクセス:
```
http://192.168.0.5:8000
```

**期待される出力:**
```
======================================================================
🌐 ボールブロッキングストリーミングサーバー起動！
======================================================================
ブラウザで以下のURLにアクセスしてください:
  http://<RaspberryPiのIPアドレス>:8000
======================================================================
機能:
  - カメラでボールを検出
  - 左側検出 → 右後脚(7番)を5秒間上げる
  - 右側検出 → 左後脚(5番)を5秒間上げる
======================================================================
終了するには Ctrl+C を押してください
```

**Web UIで確認できる情報:**
- リアルタイムカメラストリーム
- ボール検出バウンディングボックス
- FPS
- 推論時間
- ボール検出回数
- ブロック回数

**終了方法:** `Ctrl+C`

---

### テスト5: 完全ワークフローテスト

カメラ検出からブロッキングまでの完全なフローをテストします。

```bash
python3 tests/test_ball_blocking_simple.py --test workflow
```

**何をテストするか:**
1. カメラ位置（X座標）をシミュレート
2. 左/右判定
3. Arduino高速監視トリガー
4. センサー前で手を振る
5. ブロッキング実行

**重要:** プロンプトが表示されたら、該当センサーの前で手を振ってください！

---

## 全テストを一度に実行

```bash
# すべてのテストを順番に実行
python3 tests/test_ball_blocking_simple.py --test all
```

**注意:**
- `--test all` は対話的テスト（manual）を含みません
- 実行されるテスト: sides, ultrasonic, workflow

---

## コマンドリファレンス

### Arduinoファームウェア

```bash
# コンパイルのみ
export PATH=$PATH:/home/worker1/robot_pk/bin
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller

# アップロードのみ
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller

# コンパイル＆アップロード（一度に）
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller && \
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
```

### Pythonテスト

```bash
# 超音波センサーテスト
python3 tests/test_ball_blocking_simple.py --test ultrasonic

# 位置判定テスト
python3 tests/test_ball_blocking_simple.py --test sides

# 手動トリガーテスト（対話的）
python3 tests/test_ball_blocking_simple.py --test manual

# 完全ワークフローテスト
python3 tests/test_ball_blocking_simple.py --test workflow

# すべて実行
python3 tests/test_ball_blocking_simple.py --test all

# 自動テスト（推奨）
python3 tests/test_ball_blocking_auto.py

# カメラ統合テスト
python3 tests/test_ball_blocking.py
```

---

## トラブルシューティング

### 問題1: Arduinoが見つからない

```bash
# デバイス確認
ls -la /dev/ttyACM*

# USBデバイス確認
lsusb | grep Arduino

# 別のポートを試す
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno arduino/robot_controller
```

### 問題2: 権限エラー

```bash
# dialoutグループに追加
sudo usermod -a -G dialout $USER

# 確認
groups

# 再ログインが必要
exit
# SSHで再接続
```

### 問題3: 超音波センサーが反応しない

**確認事項:**
1. 配線確認
   - VCC → 5V（3.3Vではない）
   - GND → GND
   - TRIG, ECHO が正しいピンに接続

2. センサーテスト実行
   ```bash
   python3 tests/test_ball_blocking_simple.py --test ultrasonic
   ```

3. センサーの前で手を動かす（2-400cmの範囲）

### 問題4: サーボが動かない

**確認事項:**
1. PCA9685の電源（サーボは大電流が必要）
2. サーボID確認（5番と7番）
3. I2C接続確認
   ```bash
   i2cdetect -y 1
   # 0x40にPCA9685が表示されるはず
   ```

### 問題5: カメラが起動しない

```bash
# カメラ確認
libcamera-hello --list-cameras

# カメラ有効化確認
vcgencmd get_camera

# 期待される出力:
# supported=1 detected=1
```

### 問題6: TPUが認識されない

```bash
# TPU確認
lsusb | grep Google

# 期待される出力:
# Bus 001 Device 004: ID 1a6e:089a Global Unichip Corp.
```

---

## よくある質問（FAQ）

### Q1: テスト中にエラーが出たらどうすればいい？

**A:** まず以下を確認してください:
1. Arduino接続: `ls -la /dev/ttyACM0`
2. ファームウェア: 最新版がアップロードされているか
3. 配線: 超音波センサーの配線が正しいか

### Q2: ボールが検出されない

**A:**
- 照明条件を改善（明るい場所）
- ボールの色とサイズを確認（標準的なサッカーボール）
- 検出しきい値を調整（test_ball_blocking.py内の`score_threshold`）

### Q3: 反応が遅い

**A:**
- Arduino側のサンプリング周波数を上げる（`delay(20)` → `delay(10)`）
- ただし、超音波センサーの最小測定間隔（約60ms）を考慮

### Q4: 誤検出が多い

**A:**
- 距離変化閾値を大きくする（`10.0` → `15.0` cm）
- 移動平均のウィンドウサイズを増やす（`BUFFER_SIZE = 5` → `7`）

---

## パラメータチューニング

### Arduino側 (robot_controller.ino)

```cpp
// 監視時間（ミリ秒）
unsigned long duration = 4000;  // デフォルト: 4秒

// 距離変化閾値（cm）
if (distanceChange > 10.0) {    // デフォルト: 10cm

// サンプリング間隔（ミリ秒）
delay(20);  // デフォルト: 20ms (約50Hz)

// サーボ保持時間（ミリ秒）
delay(2000);  // デフォルト: 2秒

// 移動平均のウィンドウサイズ
const int BUFFER_SIZE = 5;  // デフォルト: 5サンプル
```

### Python側 (ball_blocker.py)

```python
# 位置判定閾値（0.0-1.0）
blocker = BallBlocker(
    serial_controller,
    left_threshold=0.3,   # デフォルト: 0.3 (30%)
    right_threshold=0.7   # デフォルト: 0.7 (70%)
)
```

---

## システム動作フロー（おさらい）

```
1. カメラでボール検出（TPU推論）
   ↓
2. ボールのX座標取得
   ↓
3. 位置判定（左/右/中央）
   ↓
4. Arduino高速監視コマンド送信（HL or HR）
   ↓
5. Arduino側で4秒間、50Hzサンプリング
   ↓
6. 移動平均フィルタでノイズ除去
   ↓
7. 距離変化検出（>10cm）
   ↓
8. サーボ即座に上げる（<100ms）
   ↓
9. 2秒保持
   ↓
10. サーボを下ろす
```

---

## 参考ドキュメント

- **README_BALL_BLOCKING.md**: 詳細な技術ドキュメント
- **BALL_DETECTING_AND_BLOCKING.md**: 実装ログとテスト結果
- **CLAUDE.md**: プロジェクト全体の設計

---

## サポート

問題が解決しない場合は、以下の情報を収集してください:

```bash
# システム情報
uname -a
python3 --version

# Arduino接続状態
ls -la /dev/ttyACM*
arduino-cli board list

# シリアルポートテスト
python3 -c "import serial; s = serial.Serial('/dev/ttyACM0', 9600, timeout=1); print('Connection OK')"
```

---

**作成日**: 2025年11月8日
**最終更新日**: 2025年11月8日
