# PK課題セットアップガイド

PK課題（ボールブロッキング）のArduinoコンパイル・アップロードおよびPythonスクリプト実行手順です。

## 前提条件

- RaspberryPi 4 (Ubuntu Server)
- Arduino Uno（USB接続）
- arduino-cli インストール済み
- Google Coral TPU 接続済み

---

## 1. Arduino CLIセットアップ（初回のみ）

### arduino-cliのインストール

```bash
# arduino-cliをダウンロード
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# PATHに追加（~/.bashrcに追記）
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 確認
arduino-cli version
```

### Arduino Unoボード設定

```bash
# コアインデックスを更新
arduino-cli core update-index

# Arduino AVRコアをインストール
arduino-cli core install arduino:avr

# インストール確認
arduino-cli core list
```

### 必要ライブラリのインストール

```bash
# Adafruit PWM Servo Driverライブラリ
arduino-cli lib install "Adafruit PWM Servo Driver Library"

# Wireライブラリ（通常はコアに含まれている）
```

---

## 2. PK用Arduinoファームウェアのコンパイル・アップロード

### Arduinoポートの確認

```bash
# 接続されているArduinoを確認
arduino-cli board list
```

出力例：
```
Port         Protocol Type              Board Name  FQBN            Core
/dev/ttyACM0 serial   Serial Port (USB) Arduino Uno arduino:avr:uno arduino:avr
```

### コンパイル

```bash
cd /home/user/Robot2

# PK用ファームウェアをコンパイル
arduino-cli compile --fqbn arduino:avr:uno arduino/pk_controller/pk_controller.ino
```

成功時の出力：
```
Sketch uses XXXX bytes (XX%) of program storage space.
Global variables use XXX bytes (XX%) of dynamic memory.
```

### アップロード

```bash
# Arduinoにアップロード（ポートは環境に合わせて変更）
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/pk_controller/pk_controller.ino
```

成功時の出力：
```
avrdude: AVR device initialized and ready to accept instructions
...
avrdude done.  Thank you.
```

### ワンライナー（コンパイル＆アップロード）

```bash
arduino-cli compile --fqbn arduino:avr:uno arduino/pk_controller/pk_controller.ino && \
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/pk_controller/pk_controller.ino
```

---

## 3. シリアル通信テスト

アップロード後、Arduinoが正しく動作しているか確認します。

```bash
# シリアルモニターで確認（Ctrl+Cで終了）
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=9600
```

起動メッセージ `PK Controller initialized` が表示されれば成功です。

### 手動コマンドテスト

シリアルモニターで以下のコマンドを送信してテスト：

| コマンド | 説明 | 期待される応答 |
|---------|------|---------------|
| `I` | 全脚を初期位置に | `OK` |
| `DL` | 左超音波センサー読み取り | `D00XXX`（距離mm） |
| `DR` | 右超音波センサー読み取り | `D00XXX`（距離mm） |
| `BL` | 左側ブロック（5秒間） | `OK` |
| `BR` | 右側ブロック（5秒間） | `OK` |

---

## 4. Pythonスクリプト実行

### 依存パッケージの確認

```bash
# 必要なパッケージがインストールされているか確認
python3 -c "import serial; import cv2; import numpy; print('OK')"
```

### PK課題テスト実行

```bash
cd /home/user/Robot2

# ボールブロッキングテスト実行
python3 tests/test_ball_blocking.py
```

### ブラウザでアクセス

スクリプト実行後、以下のURLにアクセス：

```
http://<RaspberryPiのIPアドレス>:8000
```

IPアドレスの確認：
```bash
hostname -I
```

---

## 5. PWM値一覧（参考）

`walk_program_refactored_20260109.ino`準拠のPWM値：

### サーボチャンネル

| 脚 | 腰(HIP) | 膝(KNEE) |
|----|---------|----------|
| FL（左前） | 0 | 1 |
| FR（右前） | 2 | 3 |
| BL（左後） | 8 | 5 |
| BR（右後） | 6 | 7 |

### ボールブロック用PWM値

| 脚 | チャンネル | UP（上げる） | DOWN（下ろす） |
|----|-----------|-------------|---------------|
| BL膝 | 5 | 150 | 300 |
| BR膝 | 7 | 380 | 250 |

---

## 6. トラブルシューティング

### Arduino が認識されない

```bash
# デバイス確認
ls -la /dev/ttyACM*

# 権限確認・追加
sudo usermod -a -G dialout $USER
# 再ログインが必要
```

### コンパイルエラー

```bash
# ライブラリが不足している場合
arduino-cli lib install "Adafruit PWM Servo Driver Library"

# コアが不足している場合
arduino-cli core install arduino:avr
```

### Python実行エラー

```bash
# serialモジュールがない場合
pip3 install pyserial

# OpenCVがない場合
sudo apt install python3-opencv
```

### サーボが動かない

1. PCA9685の電源確認（外部電源が必要）
2. I2C接続確認：
   ```bash
   sudo i2cdetect -y 1
   ```
   アドレス `0x40` が表示されるはず

---

## 7. ファイル構成

```
Robot2/
├── arduino/
│   ├── pk_controller/           # PK課題専用
│   │   └── pk_controller.ino
│   └── robot_controller/        # ハンドコントロール用
│       └── robot_controller.ino
├── src/
│   └── arduino/
│       ├── pk_serial_controller.py   # PK専用
│       └── serial_controller.py      # ハンドコントロール用
├── tests/
│   └── test_ball_blocking.py    # PK課題テスト
└── docs/
    └── PK_SETUP_GUIDE.md        # このファイル
```

---

## クイックスタート

```bash
# 1. Arduinoにアップロード
arduino-cli compile --fqbn arduino:avr:uno arduino/pk_controller/pk_controller.ino && \
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/pk_controller/pk_controller.ino

# 2. Pythonスクリプト実行
python3 tests/test_ball_blocking.py

# 3. ブラウザでアクセス
# http://<RaspberryPiのIP>:8000
```
