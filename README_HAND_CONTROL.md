# 手指検出・サーボ制御システム

MediaPipe Handsを使用して人の手と指の角度を検出し、サーボモータにマッピングして制御するシステムです。

## システム概要

### 機能
- **手検出**: MediaPipe Handsで左右の手を同時検出（最大2手）
- **指角度計算**: 21キーポイントから各指（親指〜薬指）の曲がり角度を計算
- **サーボマッピング**: 指の角度をリアルタイムでサーボモータ角度に変換
- **Webストリーミング**: ブラウザで検出結果とサーボ状態を確認

### サーボ割り当て

| 手 | 指 | サーボチャンネル |
|----|----|--------------------|
| 左手 | 親指 | 0番 |
| 左手 | 人差し指 | 2番 |
| 左手 | 中指 | 4番 |
| 左手 | 薬指 | 6番 |
| 右手 | 親指 | 1番 |
| 右手 | 人差し指 | 3番 |
| 右手 | 中指 | 5番 |
| 右手 | 薬指 | 7番 |

### アーキテクチャ

```
RaspberryPi Camera Module 3
    ↓
カメラフレーム取得 (640x480 @ 30fps)
    ↓
MediaPipe Hands (CPU) - 手検出・21キーポイント抽出
    ↓
指角度計算 (0-180度)
    ↓
サーボ角度マッピング (0-180度)
    ↓
Arduino (シリアル通信)
    ↓
PCA9685サーボドライバ → サーボモータ8個
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
# MediaPipe Handsのインストール
pip3 install mediapipe

# または、以下のコマンドで一括インストール
pip3 install mediapipe opencv-python numpy
```

**注意**: MediaPipeはCPU版ですが、実測で9-10 FPS程度で動作します。手指制御には十分な速度です。

### 2. ハードウェア接続

#### 必要なハードウェア
- RaspberryPi 4 (8GB推奨)
- RaspberryPi Camera Module 3
- Arduino Uno
- PCA9685 16チャンネルサーボドライバ
- サーボモータ x8 (左右各4本)
- 電源（サーボ用、最低10A推奨）

#### 配線
1. **RaspberryPi ⟷ Arduino**: USBケーブル（/dev/ttyACM0）
2. **Arduino ⟷ PCA9685**: I2C通信（SDA/SCL）
3. **PCA9685 ⟷ サーボ**: 0,1,2,3,4,5,6,7番チャンネルに接続
4. **電源**: PCA9685に外部電源を接続（サーボ用）

**⚠️ 重要**: サーボとRaspberryPiの電源は必ず分離してください！

### 3. Arduino側のプログラム

Arduino側で以下のシリアルコマンドに対応している必要があります:

```
S[ID:2][ANGLE:3]\n  - サーボ制御
例: S00090\n → 0番サーボを90度に設定
例: S01120\n → 1番サーボを120度に設定
```

Arduinoスケッチ例は `arduino/robot_controller/robot_controller.ino` を参照してください。

## 使い方

### 基本的な実行

```bash
# テストプログラムを実行
python3 tests/test_hand_control.py
```

### ブラウザでアクセス

```
http://<RaspberryPiのIPアドレス>:8000
```

ブラウザで以下が確認できます:
- リアルタイムカメラ映像
- 手のランドマーク描画（21キーポイント）
- FPS、検出時間
- 各サーボの現在角度

### 実行例

```bash
$ python3 tests/test_hand_control.py

======================================================================
🖐️  手指検出・サーボ制御テスト
======================================================================
🖐️  MediaPipe Hands初期化中...
✅ MediaPipe Hands初期化完了
🎛️  FingerMapper初期化中...
✅ FingerMapper初期化完了
📷 カメラを初期化中...
✅ カメラ初期化完了
📡 Arduinoに接続中...
✅ Arduino接続完了
======================================================================
🌐 手指検出ストリーミングサーバー起動！
======================================================================
ブラウザで以下のURLにアクセスしてください:
  http://<RaspberryPiのIPアドレス>:8000
======================================================================
機能:
  - カメラで手と指を検出
  - 左手: 親指(0), 人差し指(2), 中指(4), 薬指(6)
  - 右手: 親指(1), 人差し指(3), 中指(5), 薬指(7)
======================================================================
終了するには Ctrl+C を押してください
======================================================================
```

### 動作確認

1. **手をカメラに向けて提示**
   - 左手を出すと、サーボ0,2,4,6番が動作
   - 右手を出すと、サーボ1,3,5,7番が動作
   - 両手を出すと、全8サーボが動作

2. **指を曲げる**
   - 指を伸ばす → サーボ角度が小さくなる（0度方向）
   - 指を曲げる → サーボ角度が大きくなる（180度方向）

3. **ブラウザで確認**
   - 各サーボの角度がリアルタイムで更新される
   - 検出状態（LEFT/RIGHT/NONE）が表示される

## モジュール構成

### src/hand_control/

```
src/hand_control/
├── __init__.py          - モジュール初期化
├── hand_detector.py     - MediaPipe Hands手検出エンジン
└── finger_mapper.py     - 指角度→サーボ角度マッピング
```

### hand_detector.py

**HandDetectorクラス**
- `detect(frame)`: RGB画像から手を検出
- `draw_landmarks(frame)`: ランドマークを描画
- `_calculate_finger_angles()`: 各指の角度を計算

**検出結果の形式**:
```python
{
    'left_hand': {
        'landmarks': [...],  # 21キーポイント
        'finger_angles': {
            'thumb': 45.0,
            'index': 30.0,
            'middle': 25.0,
            'ring': 40.0,
            'pinky': 50.0
        }
    },
    'right_hand': { ... }
}
```

### finger_mapper.py

**FingerMapperクラス**
- `map_finger_to_servo(angle)`: 1本の指の角度をサーボ角度に変換
- `map_hand_to_servos(hand_data)`: 手全体をサーボコマンドに変換
- `get_servo_channel(hand, finger)`: サーボチャンネル番号を取得

**マッピングの仕様**:
- 入力: 指の角度 0-180度（0度=伸びた状態、180度=曲がった状態）
- 出力: サーボ角度 0-180度
- `invert_mapping=True` で反転可能

## パフォーマンス

### 処理速度

| 項目 | 値 |
|------|-----|
| 検出FPS | 9-10 FPS (実測値、軽量モデル使用) |
| 検出時間 | 100-110 ms/frame |
| 解像度 | 640x480 |
| モデル | model_complexity=0 (軽量・高速) |

**注意**: 手指制御には9-10 FPSで十分です。より高速化が必要な場合は、解像度を下げる（320x240など）か、フレームスキップを実装してください。

### メモリ使用量

- MediaPipe Hands: 約200-300 MB
- カメラバッファ: 約10 MB
- 合計: 約500 MB（RaspberryPi 4の8GBで十分動作）

## トラブルシューティング

### MediaPipeがインストールできない

```bash
# pipをアップグレード
pip3 install --upgrade pip

# 再度インストール
pip3 install mediapipe
```

### 手が検出されない

1. **照明を確認**: 明るい環境で実行してください
2. **カメラ距離**: カメラから50cm-1m程度の距離で手を提示
3. **信頼度閾値を下げる**:
   ```python
   hand_detector = HandDetector(
       min_detection_confidence=0.5,  # 0.7 → 0.5に下げる
       min_tracking_confidence=0.3    # 0.5 → 0.3に下げる
   )
   ```

### サーボが動かない

1. **Arduino接続確認**:
   ```bash
   ls -l /dev/ttyACM0
   # 存在しない場合は /dev/ttyUSB0 などを確認
   ```

2. **シリアル通信ログ確認**:
   ```python
   # serial_controller.pyのログレベルをDEBUGに変更
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **サーボ電源確認**: PCA9685の外部電源が接続されているか確認

### FPSが低い

1. **解像度を下げる**:
   ```python
   camera = CameraController(resolution=(320, 240), framerate=30)
   ```

2. **検出頻度を下げる**:
   ```python
   # フレームスキップ実装例
   if frame_count % 2 == 0:  # 2フレームに1回検出
       hand_data = detector.detect(frame)
   ```

## 今後の拡張

- [ ] **両手ジェスチャー認識**: 特定のジェスチャーでコマンド実行
- [ ] **軌道記録・再生**: 手の動きを記録して再生
- [ ] **小指対応**: 小指もサーボに割り当て（現在は親指〜薬指のみ）
- [ ] **リアルタイムチューニング**: Web UIからマッピングパラメータを調整

## TPU版について

### TPU版の制限（実装検証結果）

Google Coral TPUでの手指検出を試みましたが、以下の制限により**CPU版（MediaPipe）を推奨**します：

#### 技術的な課題
1. **2段階パイプラインの複雑さ**
   - Palm Detection（CPU） → Hand Landmark（TPU）の連携が必要
   - Palm Detectionが遅く、FPS向上の効果が限定的（約5 FPS）

2. **ROI切り抜きの精度問題**
   - Hand Landmarkモデルは手が画面いっぱいに写っている画像を期待
   - Palm Detectionの切り抜き精度が不十分で検出失敗が多発
   - 両手の同時検出が困難

3. **開発コスト**
   - MediaPipeの最適化済みパイプラインを再実装する必要がある
   - ROI調整、座標変換、後処理の実装に時間がかかる

#### 実装ファイル
参考までに、TPU版の実装は以下に残されています：
- `src/hand_control/hand_detector_tpu.py` - TPU版Hand Detector（Palm + Hand Landmark）
- `tests/test_hand_control_tpu.py` - TPU版テストスクリプト

#### 推奨事項
- **手指制御**: CPU版MediaPipe Hands（9-10 FPS、確実な両手検出）
- **TPUリソース**: ボール検出など他の高速化が必要なタスクに割り当てるべき

## 参考リンク

- [MediaPipe Hands公式ドキュメント](https://google.github.io/mediapipe/solutions/hands.html)
- [Google Coral TPU](https://coral.ai/docs/)
- [PCA9685 サーボドライバ](https://www.adafruit.com/product/815)

## ライセンス

このプロジェクトは学校課題として作成されています。

---

**Created**: 2025-12-08
**Author**: Claude Code Assistant
