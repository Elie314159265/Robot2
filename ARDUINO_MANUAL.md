# Arduino セットアップ & ボール追跡テスト 手動実行マニュアル

このドキュメントは、Arduinoのファームウェアコンパイル・アップロードから、ボール追跡テストまでの手順を詳細に説明します。

---

## 📋 目次

1. [ハードウェア構成](#ハードウェア構成)
2. [使用ファイル一覧](#使用ファイル一覧)
3. [Arduino-CLIセットアップ](#arduino-cliセットアップ)
4. [Arduinoの接続確認](#arduinoの接続確認)
5. [ファームウェアのコンパイル](#ファームウェアのコンパイル)
6. [ファームウェアのアップロード](#ファームウェアのアップロード)
7. [ボール追跡テスト実行](#ボール追跡テスト実行)
8. [トラブルシューティング](#トラブルシューティング)

---

## ハードウェア構成

### 必要な機材

- **RaspberryPi 4** (8GB, Ubuntu OS)
- **Arduino Uno**
- **RaspberryPi Camera Module 3**
- **Google Coral TPU** (Edge TPU)
- **PCA9685 PWM Servo Driver** (I2C接続)
- **サーボモータ** (最低1個: パン軸用、サーボドライバの0番に接続)
- **HC-SR04 超音波距離センサ** (オプション)
- **USBケーブル** (RaspberryPi ⇔ Arduino接続用)

### 接続構成

```
RaspberryPi 4
├── USB → Arduino Uno (/dev/ttyACM0)
├── CSI → Camera Module 3
└── USB → Google Coral TPU

Arduino Uno
├── I2C (SDA/SCL) → PCA9685 Servo Driver
│                   └── Ch.0 → パン軸サーボモータ
├── Pin 9 → HC-SR04 TRIG
└── Pin 10 → HC-SR04 ECHO
```

---

## 使用ファイル一覧

### Arduinoファームウェア

| ファイル | 説明 |
|---------|------|
| `arduino/robot_controller/robot_controller.ino` | メインファームウェア（サーボ制御、距離センサ） |

**主な機能:**
- PCA9685経由でサーボモータ制御（16チャンネル対応）
- HC-SR04超音波距離センサ読み取り
- シリアル通信プロトコル（9600 baud）

**通信プロトコル:**
- サーボ制御: `S[ID:2桁][ANGLE:3桁]\n` (例: `S00090` = サーボ0を90度に設定)
- 距離読取: `D\n` → 応答: `D[VALUE:5桁]` (mm単位、例: `D00125` = 12.5cm)

### Python制御プログラム

| ファイル | 説明 |
|---------|------|
| `src/arduino/serial_controller.py` | Arduinoとのシリアル通信を管理 |
| `src/tracking/pid_controller.py` | PID制御アルゴリズム |
| `src/tracking/tracker.py` | ボール追跡ロジック（PID制御統合） |
| `src/camera/camera_controller_libcamera_cli.py` | カメラ制御（libcamera-vid使用） |
| `tests/test_ball_tracking.py` | 統合テストプログラム（Webストリーミング） |

### TPUモデル

| ファイル | 説明 |
|---------|------|
| `models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite` | Edge TPU用COCOモデル |
| `models/coco_labels.txt` | COCOラベルファイル（90クラス） |

---

## Arduino-CLIセットアップ

### 1. Arduino-CLIの場所確認

Arduino-CLIは既にインストール済みで、プロジェクトの`bin/`ディレクトリにあります。

```bash
ls -la /home/worker1/robot_pk/bin/arduino-cli
```

**期待される出力:**
```
-rwxr-xr-x  1 worker1 worker1 34429470 11月  2 21:29 /home/worker1/robot_pk/bin/arduino-cli
```

### 2. PATHを通す

**✅ 既に設定済み**: このプロジェクトでは `.bashrc` に既に追加されています。新しいターミナルを開くと自動的に有効になります。

**確認方法:**
```bash
which arduino-cli
# 出力: /home/worker1/robot_pk/bin/arduino-cli
```

**手動で追加する場合（既に実行済み）:**
```bash
echo 'export PATH="$HOME/robot_pk/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**一時的にPATHを通す場合:**
```bash
export PATH=$PATH:/home/worker1/robot_pk/bin
```

### 3. バージョン確認

```bash
arduino-cli version
```

**期待される出力:**
```
arduino-cli  Version: 1.3.1 Commit: 08ff7e2b Date: 2025-08-28T13:51:43Z
```

### 4. インストール済みボードとライブラリの確認

#### ボード（Core）確認

```bash
arduino-cli core list
```

**期待される出力:**
```
ID          インストール済 Latest Name
arduino:avr 1.8.6          1.8.6  Arduino AVR Boards
```

もし未インストールの場合:
```bash
arduino-cli core install arduino:avr
```

#### ライブラリ確認

```bash
arduino-cli lib list
```

**期待される出力:**
```
Name                              インストール済 Available    Location Description
Adafruit BusIO                    1.17.4         -            user     -
Adafruit PWM Servo Driver Library 3.0.2          -            user     -
```

もし未インストールの場合:
```bash
arduino-cli lib install "Adafruit PWM Servo Driver Library"
arduino-cli lib install "Adafruit BusIO"
```

---

## Arduinoの接続確認

### 1. USB接続確認

ArduinoをRaspberryPiにUSB接続し、認識されているか確認します:

```bash
arduino-cli board list
```

**期待される出力:**
```
シリアルポート      Protocol タイプ               Board Name  FQBN            Core
/dev/ttyACM0        serial   Serial Port (USB)    Arduino Uno arduino:avr:uno arduino:avr
```

**ポイント:**
- `シリアルポート` が `/dev/ttyACM0` であることを確認
- `Board Name` が `Arduino Uno` であることを確認
- `FQBN` が `arduino:avr:uno` であることを確認

### 2. シリアルポート権限確認

もしアクセス権限エラーが出る場合:

```bash
# 自分がdialoutグループに所属しているか確認
groups

# dialoutグループに追加（必要な場合のみ）
sudo usermod -a -G dialout $USER

# ログアウト→ログインで反映
```

---

## ファームウェアのコンパイル

### 1. プロジェクトディレクトリに移動

```bash
cd /home/worker1/robot_pk
```

### 2. コンパイル実行

```bash
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller
```

**オプション説明:**
- `--fqbn arduino:avr:uno`: Arduino Uno用にコンパイル
- `arduino/robot_controller`: スケッチのディレクトリパス（.inoファイルが含まれる）

**成功時の出力例:**
```
最大32256バイトのフラッシュメモリのうち、スケッチが10512バイト（32%）を使っています。
最大2048バイトのRAMのうち、グローバル変数が455バイト（22%）を使っていて、ローカル変数で1593バイト使うことができます。
```

**確認ポイント:**
- フラッシュメモリ使用率が100%未満
- RAM使用率が80%未満（目安）
- エラーメッセージが出ていない

### 3. コンパイルエラーが出た場合

**よくあるエラーと対処法:**

#### エラー: ライブラリが見つからない
```
fatal error: Adafruit_PWMServoDriver.h: No such file or directory
```

**対処法:**
```bash
arduino-cli lib install "Adafruit PWM Servo Driver Library"
arduino-cli lib install "Adafruit BusIO"
```

#### エラー: ボードが見つからない
```
Error: Unknown FQBN: arduino:avr:uno
```

**対処法:**
```bash
arduino-cli core install arduino:avr
```

---

## ファームウェアのアップロード

### 1. アップロード実行

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
```

**オプション説明:**
- `-p /dev/ttyACM0`: シリアルポート指定
- `--fqbn arduino:avr:uno`: Arduino Uno用
- `arduino/robot_controller`: スケッチディレクトリ

**成功時の出力例:**
```
New upload port: /dev/ttyACM0 (serial)
```

**確認ポイント:**
- エラーメッセージが出ていない
- Arduino本体のLEDが点滅（アップロード中）
- アップロード完了後、Arduinoがリセットされる

### 2. アップロード完了確認

Arduinoがリセットされ、シリアル通信が開始されます。確認するには:

```bash
# シリアルモニタで確認（Ctrl+Cで終了）
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=9600
```

**期待される出力:**
```
Arduino initialized
```

### 3. アップロードエラーが出た場合

**よくあるエラーと対処法:**

#### エラー: ポートが開けない
```
error opening serial port: Permission denied
```

**対処法:**
```bash
# dialoutグループに追加
sudo usermod -a -G dialout $USER
# ログアウト→ログインで反映
```

#### エラー: Arduinoが応答しない
```
avrdude: stk500_recv(): programmer is not responding
```

**対処法:**
1. USBケーブルを抜き差し
2. Arduinoのリセットボタンを押す
3. 別のUSBポートを試す
4. もう一度アップロードを実行

---

## ボール追跡テスト実行

### 1. 事前確認

以下が準備されているか確認:
- [ ] Arduinoにファームウェアがアップロード済み
- [ ] カメラがRaspberryPiに接続されている
- [ ] Google Coral TPUが接続されている
- [ ] サーボモータがPCA9685の0番チャンネルに接続されている
- [ ] TPUモデルファイルが `models/` にある

### 2. テストプログラム起動

```bash
cd /home/worker1/robot_pk
python3 tests/test_ball_tracking.py
```

### 3. 起動ログの確認

**正常起動時のログ:**
```
======================================================================
🎯 ボール追跡テスト - Phase 5
======================================================================
2025-11-07 19:43:22,935 - __main__ - INFO - 📦 TPUモデル読み込み: models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
2025-11-07 19:43:25,600 - __main__ - INFO - ✅ Edge TPU モデル読み込み完了
2025-11-07 19:43:25,601 - __main__ - INFO - 📝 ラベル読み込み: models/coco_labels.txt
2025-11-07 19:43:25,601 - __main__ - INFO - ✅ 90 ラベル読み込み完了
2025-11-07 19:43:25,601 - __main__ - INFO - 📷 カメラを初期化中...
2025-11-07 19:43:27,627 - __main__ - INFO - ✅ カメラ初期化完了
2025-11-07 19:43:29,630 - __main__ - INFO - 🎛️  PID制御器を初期化中...
2025-11-07 19:43:29,630 - __main__ - INFO - ✅ PID制御器初期化完了
2025-11-07 19:43:29,630 - __main__ - INFO - 🎯 ボールトラッカーを初期化中...
2025-11-07 19:43:29,631 - __main__ - INFO - ✅ ボールトラッカー初期化完了
2025-11-07 19:43:29,631 - __main__ - INFO - 📡 Arduinoに接続中...
2025-11-07 19:43:31,637 - __main__ - INFO - ✅ Arduino接続完了
======================================================================
🌐 ボール追跡ストリーミングサーバー起動！
======================================================================
ブラウザで以下のURLにアクセスしてください:
  http://<RaspberryPiのIPアドレス>:8000
======================================================================
機能:
  - カメラでボールを検出
  - PID制御で画面中央に追従
  - サーボモータをリアルタイム制御
======================================================================
終了するには Ctrl+C を押してください
======================================================================
```

### 4. RaspberryPiのIPアドレス確認

別のターミナルで:
```bash
hostname -I
```

**出力例:**
```
192.168.0.5
```

### 5. Webブラウザでアクセス

PCまたはスマートフォンのブラウザで以下のURLを開く:
```
http://192.168.0.5:8000
```
（IPアドレスは実際のRaspberryPiのものに置き換える）

### 6. 表示される情報

Webページには以下が表示されます:
- **リアルタイムカメラ映像** (検出されたボールに赤いバウンディングボックス)
- **FPS** (フレームレート、30 FPS目標)
- **推論時間** (TPU推論にかかる時間、<20ms目標)
- **ボール検出数** (累計)
- **追跡状態** (idle/tracking/lost)
- **サーボ角度** (Pan/Tilt)

### 7. 動作確認

1. **サッカーボールを画面に映す**
   - ボールが検出されると赤いボックスで囲まれる
   - 画面中央に黄色の十字マーカーが表示される

2. **ボールを左右に動かす**
   - サーボモータが追従してボールを画面中央に保つように動く
   - 追跡状態が `tracking` に変わる

3. **ボールを画面外に出す**
   - 数秒後に追跡状態が `lost` に変わる
   - サーボは最後の位置を保持

### 8. 終了方法

ターミナルで `Ctrl+C` を押す:
```
^C
🛑 停止中...
✅ システムを終了しました
```

---

## トラブルシューティング

### 問題1: Arduino-CLIが見つからない

**症状:**
```bash
$ arduino-cli version
bash: arduino-cli: command not found
```

**原因:**
新しいターミナルセッションでまだ `.bashrc` が読み込まれていない可能性があります。

**解決策:**

1. **新しいターミナルを開く（推奨）**
   - 既に `.bashrc` に設定済みなので、新しいターミナルを開くだけで有効になります

2. **現在のセッションで即座に有効化:**
   ```bash
   source ~/.bashrc

   # 確認
   which arduino-cli
   # 出力: /home/worker1/robot_pk/bin/arduino-cli
   ```

3. **一時的にPATHを通す:**
   ```bash
   export PATH=$PATH:/home/worker1/robot_pk/bin
   ```

**注意:** このプロジェクトでは既に `.bashrc` に以下が追加されています:
```bash
export PATH="$HOME/robot_pk/bin:$PATH"
```

---

### 問題2: Arduinoが認識されない

**症状:**
```bash
$ arduino-cli board list
シリアルポート      Protocol タイプ               Board Name  FQBN            Core
```
（何も表示されない）

**解決策:**

1. **物理的な接続確認**
   ```bash
   lsusb | grep Arduino
   ```
   Arduinoが表示されるか確認

2. **デバイスファイル確認**
   ```bash
   ls -la /dev/ttyACM*
   ls -la /dev/ttyUSB*
   ```

3. **dmesgでUSB接続ログ確認**
   ```bash
   dmesg | tail -20
   ```
   USBデバイスの接続/切断ログを確認

4. **USBケーブルを交換**
   - データ通信対応のUSBケーブルか確認（充電専用ケーブルはNG）

---

### 問題3: 権限エラー

**症状:**
```
error opening serial port: Permission denied
```

**解決策:**
```bash
# 現在のグループ確認
groups

# dialoutグループに追加
sudo usermod -a -G dialout $USER

# 再ログイン（SSHの場合は再接続）
exit
# ログインし直す

# 確認
groups | grep dialout
```

---

### 問題4: コンパイルエラー

**症状:**
```
fatal error: Adafruit_PWMServoDriver.h: No such file or directory
```

**解決策:**
```bash
# ライブラリ再インストール
arduino-cli lib install "Adafruit PWM Servo Driver Library"
arduino-cli lib install "Adafruit BusIO"

# 確認
arduino-cli lib list | grep Adafruit
```

---

### 問題5: アップロードが失敗する

**症状:**
```
avrdude: stk500_recv(): programmer is not responding
```

**解決策（順に試す）:**

1. **Arduinoのリセット**
   ```bash
   # リセットボタンを押してから、すぐにアップロード実行
   arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
   ```

2. **別のポートで試す**
   ```bash
   arduino-cli board list
   # 表示されたポートを使用（/dev/ttyUSB0など）
   ```

3. **他のプロセスがポートを使用していないか確認**
   ```bash
   lsof /dev/ttyACM0
   # 使用中のプロセスがあればkillする
   ```

4. **ブートローダー確認**
   ```bash
   # ブートローダーが壊れている可能性
   # Arduino IDEでブートローダーを書き込む
   ```

---

### 問題6: カメラが起動しない

**症状:**
```
❌ カメラの初期化に失敗しました
```

**解決策:**

1. **カメラ接続確認**
   ```bash
   libcamera-hello --list-cameras
   ```

2. **カメラが有効か確認**
   ```bash
   vcgencmd get_camera
   # 出力: supported=1 detected=1
   ```

3. **他のプロセスがカメラを使用していないか確認**
   ```bash
   ps aux | grep libcamera
   ps aux | grep rpicam
   # 使用中のプロセスがあればkillする
   ```

---

### 問題7: TPUモデルが読み込めない

**症状:**
```
❌ TPUモデルの読み込み失敗
```

**解決策:**

1. **モデルファイルの存在確認**
   ```bash
   ls -la models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
   ls -la models/coco_labels.txt
   ```

2. **TPUが認識されているか確認**
   ```bash
   lsusb | grep Google
   # 出力例: Bus 001 Device 004: ID 1a6e:089a Global Unichip Corp.
   ```

3. **TPUライブラリ確認**
   ```bash
   python3 -c "import pycoral; print('OK')"
   # 出力: OK
   ```

---

### 問題8: Webページが表示されない

**症状:**
ブラウザで `http://192.168.0.5:8000` にアクセスしても表示されない

**解決策:**

1. **サーバーが起動しているか確認**
   ```bash
   # test_ball_tracking.pyが動作しているか確認
   ps aux | grep test_ball_tracking
   ```

2. **ポート8000が使用されているか確認**
   ```bash
   netstat -tuln | grep 8000
   # または
   ss -tuln | grep 8000
   ```

3. **ファイアウォール確認**
   ```bash
   sudo ufw status
   # 必要に応じてポート8000を開放
   sudo ufw allow 8000
   ```

4. **同じネットワークにいるか確認**
   - RaspberryPiとPCが同じWi-Fiネットワークに接続されているか確認

5. **IPアドレスが正しいか確認**
   ```bash
   hostname -I
   # 表示されたIPアドレスを使用
   ```

---

### 問題9: サーボが動かない

**症状:**
ボールは検出されているが、サーボが動かない

**解決策:**

1. **シリアル通信確認**
   ```bash
   # Arduinoのシリアルモニタで確認
   arduino-cli monitor -p /dev/ttyACM0 -c baudrate=9600
   # サーボコマンド（Sから始まる）が送信されているか確認
   ```

2. **PCA9685の接続確認**
   - I2C接続（SDA/SCL）が正しいか確認
   - PCA9685の電源が入っているか確認

3. **サーボの接続確認**
   - サーボがPCA9685の0番チャンネルに接続されているか確認
   - サーボの電源が入っているか確認（サーボ専用電源推奨）

4. **I2Cアドレス確認**
   Arduino側で:
   ```cpp
   #define SERVO_DRIVER_ADDR 0x40
   ```
   PCA9685のアドレスが0x40か確認（ジャンパー設定）

---

## 📝 コマンドクイックリファレンス

### PATHを通す
```bash
export PATH=$PATH:/home/worker1/robot_pk/bin
```

### Arduino確認
```bash
arduino-cli board list
```

### コンパイル
```bash
cd /home/worker1/robot_pk
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller
```

### アップロード
```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
```

### テスト実行
```bash
python3 tests/test_ball_tracking.py
```

### IP確認
```bash
hostname -I
```

### シリアルモニタ
```bash
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=9600
```

---

## 📚 参考リンク

- **Arduino-CLI公式ドキュメント**: https://arduino.github.io/arduino-cli/
- **PyCoral (Edge TPU)**: https://coral.ai/docs/
- **PCA9685データシート**: https://www.adafruit.com/product/815
- **COCO Dataset**: https://cocodataset.org/

---

## ✅ チェックリスト

テスト実行前に以下を確認:

- [ ] Arduino-CLIがインストールされている (`arduino-cli version`)
- [ ] PATHが通っている (`which arduino-cli`)
- [ ] Arduino Unoが接続されている (`arduino-cli board list`)
- [ ] ライブラリがインストールされている (`arduino-cli lib list`)
- [ ] ファームウェアがコンパイルできる (`arduino-cli compile ...`)
- [ ] ファームウェアがアップロードできる (`arduino-cli upload ...`)
- [ ] カメラが認識されている (`libcamera-hello --list-cameras`)
- [ ] TPUが認識されている (`lsusb | grep Google`)
- [ ] モデルファイルが存在する (`ls models/*.tflite`)
- [ ] サーボがPCA9685の0番に接続されている
- [ ] サーボ電源が独立している（RaspberryPiと別電源推奨）

すべてOKなら:
```bash
python3 tests/test_ball_tracking.py
```

---

**最終更新**: 2025-11-07
**作成者**: Claude Code
**プロジェクト**: 4足歩行ゴールキーパーロボット Phase 5
