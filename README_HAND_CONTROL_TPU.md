# Hand Control with TPU

Google Coral TPUを使用した高速手指検出・サーボ制御システム

## 概要

このモジュールは、Google Coral TPUとhand_landmark_newモデルを使用して、人の手と指の動きをリアルタイムで検出し、サーボモータを制御します。

### 特徴

- **高速推論**: Google Coral TPUによる高速な手指検出（目標: <20ms/frame）
- **MediaPipe互換**: CPU版HandDetectorと同じインターフェース
- **リアルタイム**: 30 FPS対応
- **マルチハンド**: 左右の手を同時検出可能

## システム構成

```
RaspberryPi Camera → Google Coral TPU (hand_landmark_new)
                                ↓
                          21キーポイント検出
                                ↓
                          指の角度計算
                                ↓
                    PCA9685 Servo Driver → サーボモータ
```

## ハードウェア要件

- RaspberryPi 4 (8GB推奨)
- RaspberryPi Camera Module 3
- Google Coral USB Accelerator
- PCA9685 サーボドライバ（オプション）
- Arduino Uno（サーボ制御用、オプション）

## ソフトウェア要件

### 必須パッケージ

```bash
# Edge TPUランタイム
sudo apt install -y libedgetpu1-std python3-pycoral

# カメラ
sudo apt install -y python3-picamera2

# 画像処理
sudo apt install -y python3-opencv python3-numpy
```

### モデルファイル

TPU版hand_landmarkモデルが必要です：

```bash
# models/ディレクトリに配置
models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite
```

## 使い方

### 1. 簡易テスト（モデルロード確認）

```bash
# 白紙画像でTPUの動作確認
python3 scripts/test_hand_tpu_simple.py

# サンプル画像でテスト
python3 scripts/test_hand_tpu_simple.py path/to/hand_image.jpg
```

### 2. カメラ + TPU テスト

```bash
# カメラからリアルタイム検出（サーボなし）
python3 tests/test_hand_control_tpu.py
```

ブラウザで以下にアクセス：
```
http://<RaspberryPiのIPアドレス>:8000
```

### 3. 完全版（カメラ + TPU + サーボ制御）

Arduinoを接続してサーボ制御も有効化：

```bash
# Arduino接続を確認
ls /dev/ttyACM*

# テスト実行
python3 tests/test_hand_control_tpu.py
```

## サーボ割り当て

PCA9685サーボドライバのチャンネル割り当て：

| 手 | 指 | チャンネル |
|---|---|-----------|
| 左手 | 親指 | 0 |
| 右手 | 親指 | 1 |
| 左手 | 人差し指 | 2 |
| 右手 | 人差し指 | 3 |
| 左手 | 中指 | 4 |
| 右手 | 中指 | 5 |
| 左手 | 薬指 | 6 |
| 右手 | 薬指 | 7 |

## プログラムでの使用方法

### 基本的な使い方

```python
from src.hand_control import HandDetectorTPU, FingerMapper

# TPU検出器の初期化
detector = HandDetectorTPU(
    model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
    max_num_hands=1,
    min_detection_confidence=0.5
)

# 指→サーボ角度マッピング
mapper = FingerMapper(
    servo_min=0,
    servo_max=180,
    angle_min=0.0,
    angle_max=180.0
)

# 検出実行
frame = camera.capture_frame()  # RGB画像
hand_data = detector.detect(frame)

# サーボ角度にマッピング
servo_commands = mapper.map_hand_to_servos(hand_data)
# servo_commands = {0: 90, 2: 120, 4: 45, ...}
```

### CPU版との切り替え

```python
# CPU版（MediaPipe Hands）
from src.hand_control import HandDetector
detector = HandDetector(max_num_hands=2)

# TPU版（Google Coral TPU）
from src.hand_control import HandDetectorTPU
detector = HandDetectorTPU(
    model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite'
)

# 以降のコードは同じインターフェースで使用可能
hand_data = detector.detect(frame)
annotated = detector.draw_landmarks(frame)
```

## 検出結果の構造

```python
hand_data = {
    'left_hand': {
        'landmarks': [
            {'x': 0.5, 'y': 0.5, 'z': 0.0},  # 0: 手首
            {'x': 0.52, 'y': 0.48, 'z': 0.01},  # 1: 親指CMC
            # ... 21キーポイント
        ],
        'finger_angles': {
            'thumb': 45.0,   # 親指の角度
            'index': 30.0,   # 人差し指の角度
            'middle': 25.0,  # 中指の角度
            'ring': 35.0,    # 薬指の角度
            'pinky': 40.0    # 小指の角度
        }
    },
    'right_hand': None  # または同様の構造
}
```

## パフォーマンス

### 期待される性能

- **検出時間**: <20ms/frame（TPU使用時）
- **FPS**: 30 FPS以上
- **検出精度**: 80%以上（適切な照明条件下）

### ベンチマーク方法

```python
import time
import numpy as np

detection_times = []
for i in range(100):
    start = time.time()
    result = detector.detect(frame)
    detection_times.append((time.time() - start) * 1000)

print(f"平均検出時間: {np.mean(detection_times):.2f}ms")
print(f"最小: {np.min(detection_times):.2f}ms")
print(f"最大: {np.max(detection_times):.2f}ms")
```

## トラブルシューティング

### TPUが認識されない

```bash
# Edge TPUが接続されているか確認
lsusb | grep "Google"

# Edge TPUランタイムを再インストール
sudo apt remove libedgetpu1-std
sudo apt install libedgetpu1-std
```

### モデルファイルが見つからない

```bash
# モデルファイルの存在確認
ls -la models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite

# モデルファイルをダウンロード（Google Colabなどから）
# 正しいディレクトリに配置
```

### 検出精度が低い

- 照明を改善する（明るい環境）
- カメラの焦点を調整
- `min_detection_confidence`を調整（デフォルト: 0.5）

### FPSが低い

- TPUが正しく使用されているか確認（ログで"TPU"の表示を確認）
- カメラ解像度を下げる（640x480推奨）
- 他のプロセスがCPU/メモリを使用していないか確認

## ファイル構成

```
src/hand_control/
├── __init__.py                 # モジュールエクスポート
├── hand_detector.py            # CPU版（MediaPipe Hands）
├── hand_detector_tpu.py        # TPU版（Google Coral TPU）⭐ 新規
└── finger_mapper.py            # 指角度→サーボ角度マッピング

tests/
├── test_hand_control.py        # CPU版テスト
└── test_hand_control_tpu.py    # TPU版テスト ⭐ 新規

scripts/
└── test_hand_tpu_simple.py     # 簡易テストスクリプト ⭐ 新規

models/
└── hand_landmark_new_256x256_integer_quant_edgetpu.tflite  # TPUモデル
```

## 参考資料

- [Google Coral TPU Documentation](https://coral.ai/docs/)
- [PyCoral API Reference](https://coral.ai/docs/reference/py/)
- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
