# Hand Control with TPU (実験的実装)

Google Coral TPUを使用した手指検出の実験的実装

⚠️ **注意**: この実装は技術的な制限により、**CPU版（MediaPipe）の使用を推奨**します。

## 概要

Google Coral TPUでhand_landmark_newモデルを使用した手指検出を試みた実験的実装です。

### 実装検証結果

❌ **実用性が低い理由**:
- Palm Detection（CPU）がボトルネックでFPS向上なし（約5 FPS）
- ROI切り抜き精度が不十分で検出失敗が多発
- 両手の同時検出が困難
- MediaPipeの最適化パイプラインに劣る

✅ **推奨**: CPU版MediaPipe Hands（9-10 FPS、確実な両手検出）

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

TPU版hand_landmarkモデルとpalm detectionモデルが必要です：

```bash
# models/ディレクトリに配置
models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite
models/palm_detection_builtin_256_integer_quant.tflite
```

## 使い方

### 1. 簡易テスト（モデルロード確認）

```bash
# ダミー画像でTPUの動作確認
python3 scripts/test_tpu_hand_detector.py
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
    palm_model_path='models/palm_detection_builtin_256_integer_quant.tflite',
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_palm_confidence=0.5
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
    model_path='models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite',
    palm_model_path='models/palm_detection_builtin_256_integer_quant.tflite'
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

## 実測パフォーマンス

### 実際の性能（検証結果）

- **検出時間**: 約200ms/frame（Palm Detection + Hand Landmark）
- **FPS**: 約5 FPS（目標の30 FPSに未達）
- **検出成功率**: 低い（ROI切り抜き精度の問題）

### 問題点の詳細

1. **Palm Detection（CPU）がボトルネック**
   - TFLite CPUモデルで約150ms/frame
   - TPU化してもFPS向上しない主原因

2. **Hand Landmark（TPU）の入力要件**
   - 手が画面いっぱいに写っている必要がある
   - Palm Detectionの切り抜きが小さすぎる
   - マージン調整しても精度不十分

3. **両手検出の困難さ**
   - 各手を正確にクロップできない
   - confidence scoreが低い（0.0-0.3程度）

### CPU版との比較

| 項目 | TPU版 | CPU版（MediaPipe） |
|------|-------|-------------------|
| FPS | 約5 | 9-10 |
| 検出成功率 | 低い | 高い |
| 両手検出 | 困難 | 確実 |
| 実装複雑度 | 高い | 低い |
| **推奨度** | ❌ | ✅ |

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
└── test_tpu_hand_detector.py   # 簡易テストスクリプト ⭐ 新規

models/
├── hand_landmark_new_256x256_integer_quant_edgetpu.tflite  # Hand landmark TPUモデル
└── palm_detection_builtin_256_integer_quant.tflite  # Palm detection モデル
```

## 結論と推奨事項

### なぜCPU版を推奨するか

1. **実測FPS**: CPU版（9-10 FPS） > TPU版（5 FPS）
2. **検出精度**: MediaPipeの最適化されたパイプラインが優秀
3. **開発コスト**: TPU版の改善に時間をかけるよりCPU版で十分
4. **リソース配分**: TPUはボール検出など他のタスクに使うべき

### 今後の方向性

- ✅ **手指制御**: CPU版MediaPipe Hands
- ✅ **ボール検出**: Google Coral TPU（COCO SSD MobileNet）
- ✅ **リソース最適化**: 適材適所でCPU/TPUを使い分け

### この実装の価値

この実験的実装は、以下の学習価値があります：
- TPUモデルの入力要件の理解
- 2段階パイプラインの実装経験
- CPU vs TPUのベンチマーク
- 技術選択の判断基準

## 参考資料

- [MediaPipe Hands公式ドキュメント](https://google.github.io/mediapipe/solutions/hands.html)
- [Google Coral TPU Documentation](https://coral.ai/docs/)
- [PyCoral API Reference](https://coral.ai/docs/reference/py/)

## ライセンス

このプロジェクトは学校課題として作成されています。

---

**最終更新**: 2025-12-09
**結論**: CPU版MediaPipe Handsを推奨（TPU版は実験的実装として保存）
