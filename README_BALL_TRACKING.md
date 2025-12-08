# ボール追跡システム 実行ガイド

Phase 5で実装したカメラ+TPU+サーボ制御によるボール追跡システムの実行手順です。

## 📋 目次

1. [システム構成](#システム構成)
2. [必要なファイル](#必要なファイル)
3. [事前準備](#事前準備)
4. [実行手順](#実行手順)
5. [動作確認](#動作確認)
6. [トラブルシューティング](#トラブルシューティング)
7. [パラメータ調整](#パラメータ調整)

---

## システム構成

### ハードウェア
- **RaspberryPi 4** (8GB, Ubuntu OS)
- **RaspberryPi Camera Module 3** (IMX708)
- **Google Coral USB Accelerator** (Edge TPU)
- **Arduino Uno**
- **PCA9685 サーボドライバ**
- **サーボモータ** (水平方向用、サーボドライバ0番に接続)
- **超音波距離センサー** (HC-SR04)

### ソフトウェア
- Python 3.9+
- picamera2
- OpenCV
- PyCoral (Edge TPU)
- pyserial

---

## 必要なファイル

### プログラムファイル

```
robot_pk/
├── tests/
│   └── test_ball_tracking.py          # メインプログラム
├── src/
│   ├── camera/
│   │   └── camera_controller.py       # カメラ制御
│   ├── tracking/
│   │   ├── pid_controller.py          # PID制御器
│   │   └── tracker.py                 # ボール追跡ロジック
│   └── arduino/
│       └── serial_controller.py       # Arduino通信
├── arduino/
│   └── robot_controller/
│       └── robot_controller.ino       # Arduinoプログラム
└── models/
    ├── ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
    └── coco_labels.txt
```

### モデルファイル

TPUモデルは以下からダウンロード済み：
- `models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite`
- `models/coco_labels.txt`

---

## 事前準備

### 1. Arduinoプログラムのアップロード

Arduinoにサーボ制御プログラムをアップロードします。

```bash
# arduino-cliを使用する場合
cd /home/worker1/robot_pk
/home/worker1/robot_pk/bin/arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller
/home/worker1/robot_pk/bin/arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/robot_controller
```

または、Arduino IDEで以下を開いてアップロード：
- ファイル: `arduino/robot_controller/robot_controller.ino`
- ボード: Arduino Uno
- ポート: /dev/ttyACM0

### 2. ハードウェア接続確認

#### カメラ
```bash
# カメラが認識されているか確認
libcamera-hello --list-cameras
```

#### Edge TPU
```bash
# TPUが認識されているか確認
lsusb | grep "Google"
```

#### Arduino
```bash
# Arduinoが接続されているか確認
ls /dev/ttyACM*
# 出力例: /dev/ttyACM0
```

#### サーボモータ
- PCA9685のチャンネル0にパンサーボを接続
- 電源は必ずRaspberryPiと分離（重要！）

---

## 実行手順

### 基本的な実行

```bash
cd /home/worker1/robot_pk
python3 tests/test_ball_tracking.py
```

### 起動ログ確認

正常に起動すると以下のようなログが表示されます：

```
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

### プログラムの停止

```bash
# Ctrl+C を押す
# または別のターミナルから
pkill -f test_ball_tracking
```

---

## 動作確認

### 1. Webインターフェースにアクセス

ブラウザで以下のURLを開く：
```
http://<RaspberryPiのIPアドレス>:8000
```

例：
```
http://192.168.1.100:8000
```

### 2. 表示される情報

- **カメラ映像**: リアルタイムストリーミング
- **FPS**: フレームレート（目標30 FPS）
- **推論時間**: TPU推論時間（15-20ms）
- **ボール検出数**: 累計検出回数
- **追跡状態**: idle / tracking / lost
- **パンサーボ**: 現在のサーボ角度（0-180度）
- **チルトサーボ**: 固定（90度）

### 3. 動作テスト

1. **ボールを用意**: サッカーボールまたは丸いオブジェクト
2. **カメラの前に表示**: ボールがカメラに映るように配置
3. **検出確認**: 赤い枠でボールが検出される
4. **追従確認**: ボールを左右に動かすとサーボが追従

**期待される動作:**
- ボールを右に動かす → サーボが左に回転
- ボールを左に動かす → サーボが右に回転
- ボールが画面中央に来るように自動調整

---

## トラブルシューティング

### カメラが起動しない

```bash
# カメラのステータス確認
vcgencmd get_camera
# 出力: supported=1 detected=1

# カメラが使用中か確認
sudo fuser /dev/video0
```

### TPUが認識されない

```bash
# TPUデバイス確認
ls /dev/apex_0
# なければTPUドライバをインストール
```

### Arduinoが接続できない

```bash
# シリアルポート確認
ls -l /dev/ttyACM*

# 権限確認
sudo chmod 666 /dev/ttyACM0
```

### サーボが動かない

1. **電源確認**: サーボの電源が供給されているか
2. **配線確認**: PCA9685のチャンネル0に接続されているか
3. **プログラム確認**: Arduinoプログラムがアップロードされているか

### FPSが低い

1. **他のプロセス確認**:
```bash
top
# CPUを大量に使っているプロセスを確認
```

2. **カメラ解像度を下げる**:
tests/test_ball_tracking.pyの以下を変更：
```python
camera = CameraController(resolution=(320, 240), framerate=30, debug=False)
```

### 追跡が不安定

PIDパラメータを調整してください（次のセクション参照）

---

## パラメータ調整

### PIDゲインの調整

`tests/test_ball_tracking.py` の557行目付近：

```python
pid_pan = PIDController(kp=2.0, ki=0.15, kd=0.3, servo_min=-25, servo_max=25)
```

#### kp（比例ゲイン）: 現在 2.0
- **大きくする**: 応答が速くなるが振動しやすい
- **小さくする**: 応答が遅くなるが安定
- **推奨範囲**: 1.0 - 3.0

#### ki（積分ゲイン）: 現在 0.15
- **大きくする**: 定常偏差が減るが不安定になりやすい
- **小さくする**: 安定するが中央に来にくい
- **推奨範囲**: 0.05 - 0.3

#### kd（微分ゲイン）: 現在 0.3
- **大きくする**: 振動を抑える（ただしノイズに敏感）
- **小さくする**: ノイズに強いが振動しやすい
- **推奨範囲**: 0.1 - 0.5

#### servo_min/max: 現在 ±25度
- 1回の更新での最大調整量
- **推奨範囲**: ±15 - ±30

### 推奨設定例

#### 安定重視（振動を抑える）
```python
pid_pan = PIDController(kp=1.5, ki=0.1, kd=0.5, servo_min=-20, servo_max=20)
```

#### 高速応答重視（素早い追従）
```python
pid_pan = PIDController(kp=2.5, ki=0.2, kd=0.3, servo_min=-30, servo_max=30)
```

#### バランス型（現在の設定）
```python
pid_pan = PIDController(kp=2.0, ki=0.15, kd=0.3, servo_min=-25, servo_max=25)
```

---

## システム性能

### 現在の性能

- **カメラ**: 640x480 @ 30 FPS
- **TPU検出**: 40+ FPS
- **推論時間**: 平均15-20ms
- **サーボ更新**: 毎フレーム（30Hz）
- **制御遅延**: <100ms
- **追従精度**: ±50ピクセル以内

### 最適化履歴

**初期設定:**
- kp=1.0, ki=0.1, kd=0.2
- サーボ更新: 3フレームごと
- ログレベル: DEBUG

**最適化後:**
- kp=2.0, ki=0.15, kd=0.3（応答速度2倍）
- サーボ更新: 毎フレーム（遅延最小化）
- ログレベル: INFO（CPU負荷軽減）

---

## 関連ドキュメント

- [CLAUDE.md](CLAUDE.md) - プロジェクト全体の概要
- [2025-11-02-changes.txt](2025-11-02-changes.txt) - 本日の開発記録
- [blueprint.txt](blueprint.txt) - 開発計画

---

## お問い合わせ

質問や問題が発生した場合は、以下を確認してください：

1. ログ出力（エラーメッセージ）
2. ハードウェア接続状態
3. システムリソース（CPU、メモリ）

---

**更新日**: 2025-11-02
**バージョン**: Phase 5 完成版
**作成者**: Claude Code
