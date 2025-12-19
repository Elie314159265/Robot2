# Hand Control System 動作確認手順書

## 目次
1. [システム概要](#システム概要)
2. [ハードウェア構成](#ハードウェア構成)
3. [事前準備](#事前準備)
4. [Arduinoセットアップ](#arduinoセットアップ)
5. [RaspberryPiセットアップ](#raspberrypiセットアップ)
6. [動作確認手順](#動作確認手順)
7. [トラブルシューティング](#トラブルシューティング)

---

## システム概要

### 機能
手の指の動きをカメラで検出し、ロボットの脚の動きにマッピングするシステム

### データフロー
```
カメラ → MediaPipe Hands → 指角度検出 → FingerMapper → サーボ角度変換 → Arduino → PCA9685 → サーボモータ
```

### 動作原理
- **指が開く (0°)**: ヒップは前、膝は上げる
- **指が閉じる (180°)**: ヒップは後ろ、膝は下ろす
- **中間 (90°)**: ニュートラル位置

### サーボマッピング（walk_program.ino準拠）
| 指 | チャンネル | 役割 | 備考 |
|----|----------|------|------|
| **左手・親指** | ch 0 | FL hip | Front Left ヒップ |
| **左手・人差し指** | ch 2 | FR hip | Front Right ヒップ |
| **左手・中指** | ch 8 | BL hip | Back Left ヒップ |
| **左手・薬指** | ch 6 | BR hip | Back Right ヒップ |
| **右手・親指** | ch 1 | FL knee | Front Left 膝 |
| **右手・人差し指** | ch 3 | FR knee | Front Right 膝 |
| **右手・中指** | ch 5 | BL knee | Back Left 膝 |
| **右手・薬指** | ch 7 | BR knee | Back Right 膝 |

---

## ハードウェア構成

### 必要な機器

#### RaspberryPi側
- RaspberryPi 4 (8GB推奨)
- RaspberryPi Camera Module 3
- USB Type-C電源（5V 3A以上）

#### Arduino側
- Arduino Uno
- PCA9685 16チャンネルサーボドライバ
- サーボモータ × 8台（最低限）
- 外部電源（6V 10A推奨）※サーボ用
- USB Type-B ケーブル（Arduino ↔ RaspberryPi接続用）

#### 配線
- PCA9685 → Arduino: I2C接続（SDA, SCL）
- Arduino → RaspberryPi: USBシリアル通信
- サーボ → PCA9685: PWM接続（ch 0-15）

### ⚠️ 重要な注意事項
1. **電源分離**: サーボ用電源とRaspberryPi電源は必ず分離する
2. **電源容量**: サーボが8台以上ある場合、10A以上の電源を使用
3. **初期位置**: サーボは必ずニュートラル位置から始める

---

## 事前準備

### 1. 必要なソフトウェア

#### RaspberryPi (Ubuntu Server)
- Python 3.8以上
- picamera2
- OpenCV
- MediaPipe
- numpy

#### Arduino IDE (開発マシン)
- Arduino IDE 1.8.x または 2.x
- Adafruit PWM Servo Driver Library

### 2. ライブラリインストール確認

#### RaspberryPi
```bash
# システムパッケージ
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-pip

# Pythonパッケージ
pip3 install mediapipe pyserial

# 確認
python3 -c "import cv2; import mediapipe; import picamera2; print('All packages OK')"
```

#### Arduino IDE
```
スケッチ → ライブラリをインクルード → ライブラリを管理
"Adafruit PWM Servo Driver" を検索してインストール
```

---

## Arduinoセットアップ

### 1. Arduino IDE設定

#### ステップ1: ボード設定
```
ツール → ボード → Arduino AVR Boards → Arduino Uno
```

#### ステップ2: シリアルポート設定
```
ツール → シリアルポート → /dev/ttyACM0 (RaspberryPiの場合)
                      → COM3, COM4等 (Windowsの場合)
```

#### ステップ3: ボードマネージャ確認
```
ツール → ボード → ボードマネージャ
"Arduino AVR Boards" がインストールされていることを確認
```

### 2. robot_controller.ino のコンパイル・アップロード

#### ステップ1: ファイルを開く
```
ファイル → 開く → Robot2/arduino/robot_controller/robot_controller.ino
```

#### ステップ2: コンパイル確認
```
スケッチ → 検証・コンパイル
```

**成功メッセージ例:**
```
コンパイルが完了しました。
最大32256バイトのフラッシュメモリのうち、スケッチが5432バイト（16%）を使っています。
最大2048バイトのRAMのうち、グローバル変数が324バイト（15%）を使っています。
```

#### ステップ3: Arduinoに接続
1. Arduino UnoをUSBケーブルで開発マシンに接続
2. `ツール → シリアルポート` で正しいポートを選択

#### ステップ4: アップロード
```
スケッチ → マイコンボードに書き込む
```

**成功メッセージ例:**
```
ボードへの書き込みが完了しました。
```

#### ステップ5: 動作確認
```
ツール → シリアルモニタ
```

**期待される出力:**
```
Arduino initialized
```

### 3. 配線確認

#### PCA9685 → Arduino (I2C接続)
| PCA9685 | Arduino Uno |
|---------|------------|
| VCC | 5V |
| GND | GND |
| SDA | A4 (SDA) |
| SCL | A5 (SCL) |

#### サーボ → PCA9685
| サーボ | PCA9685チャンネル | 役割 |
|-------|----------------|------|
| FL hip | 0 | 左前ヒップ |
| FL knee | 1 | 左前膝 |
| FR hip | 2 | 右前ヒップ |
| FR knee | 3 | 右前膝 |
| BL knee | 5 | 左後膝 |
| BR hip | 6 | 右後ヒップ |
| BR knee | 7 | 右後膝 |
| BL hip | 8 | 左後ヒップ |

#### 外部電源 → PCA9685
- V+ → 6V電源のプラス
- GND → 6V電源のマイナス & Arduino GND（共通GND必須）

---

## RaspberryPiセットアップ

### 1. プロジェクトのダウンロード

```bash
cd /home/user
git clone <repository_url> Robot2
cd Robot2
```

### 2. カメラ動作確認

```bash
# カメラデバイス確認
libcamera-hello --list-cameras

# 期待される出力:
# Available cameras
# -----------------
# 0 : imx708 [4608x2592] (/base/soc/i2c0mux/i2c@1/imx708@1a)
#     Modes: 'SRGGB10_CSI2P' : 1536x864 [120.13 fps - (768, 432)/3072/1728 crop]
#            'SRGGB10_CSI2P' : 2304x1296 [56.03 fps - (0, 0)/4608/2592 crop]
#            'SRGGB10_CSI2P' : 4608x2592 [14.35 fps - (0, 0)/4608/2592 crop]
```

### 3. カメラテスト実行

```bash
python3 tests/test_camera.py
```

**期待される出力:**
```
カメラ初期化成功
解像度: 640x480
フレームレート: 30 fps
```

### 4. Arduino接続確認

```bash
# シリアルポート確認
ls -l /dev/ttyACM*

# 期待される出力:
# crw-rw---- 1 root dialout 166, 0 Dec 19 10:30 /dev/ttyACM0
```

**権限設定（必要な場合）:**
```bash
sudo usermod -a -G dialout $USER
# 再ログインが必要
```

### 5. finger_mapper.py の検証

```bash
# 検証スクリプト実行
python3 tests/verify_finger_mapper_simple.py
```

**期待される出力:**
```
============================================================
総合判定
============================================================
✓ SERVO_CONFIGはwalk_program.inoと完全に一致
✓ SERVO_MAPPINGは正しくch 8を使用
✓ マッピングロジックは正常に動作
✓ クリープゲイト関数との互換性あり

結論: 実装は正しく、実機で動作する見込みです
============================================================
```

---

## 動作確認手順

### Phase 1: ハードウェアテスト（Arduinoのみ）

#### 1-1. Arduino単体動作確認

```bash
# Arduino IDEのシリアルモニタで以下のコマンドを送信
S0090  # ch 0 を 90度に設定
S0145  # ch 1 を 45度に設定
```

**確認項目:**
- [ ] サーボが指定角度に動く
- [ ] 全8チャンネルが正常に動作

#### 1-2. サーボ初期位置設定

すべてのサーボをニュートラル位置に設定:
```
S0045
S0145
S0245
S0345
S0545
S0645
S0745
S0845
```

### Phase 2: RaspberryPi - Arduino 通信テスト

#### 2-1. シリアル通信確認

```bash
cd /home/user/Robot2

# Pythonでシリアル通信テスト
python3 << EOF
from src.arduino.serial_controller import SerialController
serial = SerialController(port="/dev/ttyACM0", baudrate=9600)
if serial.connect():
    print("✓ Arduino接続成功")
    serial.send_servo_command(0, 90)  # ch 0 を 90度に
    print("✓ コマンド送信成功")
    serial.disconnect()
else:
    print("✗ Arduino接続失敗")
EOF
```

**期待される出力:**
```
✓ Arduino接続成功
✓ コマンド送信成功
```

### Phase 3: カメラ + 手検出テスト

#### 3-1. 手検出のみ（サーボ制御なし）

```bash
# test_hand_control.pyのコメントアウト版を使うか、
# Arduino接続部分をスキップしてカメラ・手検出のみテスト
python3 tests/test_hand_control.py
```

#### 3-2. ブラウザアクセス

RaspberryPiのIPアドレスを確認:
```bash
hostname -I
```

ブラウザで以下にアクセス:
```
http://<RaspberryPiのIPアドレス>:8000
```

**確認項目:**
- [ ] カメラ映像が表示される
- [ ] 手を映すと緑のランドマークが表示される
- [ ] FPSが表示される（目標: 9-10 FPS）
- [ ] 左手・右手が正しく認識される

### Phase 4: 統合テスト（全システム）

#### 4-1. システム起動

```bash
cd /home/user/Robot2
python3 tests/test_hand_control.py
```

**起動ログ確認:**
```
======================================================================
🖐️  手指検出・サーボ制御テスト
======================================================================
INFO - 🖐️  MediaPipe Hands初期化中（最適化モード）...
INFO - ✅ MediaPipe Hands初期化完了（軽量モデル、9-10 FPS目標）
INFO - 🎛️  FingerMapper初期化中...
INFO - ✅ FingerMapper初期化完了
INFO - 📷 カメラを初期化中（640x480 @ 30fps）...
INFO - ✅ カメラ初期化完了
INFO - 📡 Arduinoに接続中...
INFO - ✅ Arduino接続完了
======================================================================
🌐 手指検出ストリーミングサーバー起動！
======================================================================
```

#### 4-2. 動作確認

1. **ブラウザアクセス**
   ```
   http://<RaspberryPiのIPアドレス>:8000
   ```

2. **左手テスト（ヒップ制御）**
   - [ ] 親指を開く → FL hip が前に動く (ch 0 → 0°)
   - [ ] 親指を閉じる → FL hip が後ろに動く (ch 0 → 90°)
   - [ ] 人差し指を開く → FR hip が前に動く (ch 2 → 90°)
   - [ ] 人差し指を閉じる → FR hip が後ろに動く (ch 2 → 0°)
   - [ ] 中指を開く → BL hip が前に動く (ch 8 → 0°)
   - [ ] 中指を閉じる → BL hip が後ろに動く (ch 8 → 90°)
   - [ ] 薬指を開く → BR hip が前に動く (ch 6 → 90°)
   - [ ] 薬指を閉じる → BR hip が後ろに動く (ch 6 → 0°)

3. **右手テスト（膝制御）**
   - [ ] 親指を開く → FL knee が上がる (ch 1 → 0°)
   - [ ] 親指を閉じる → FL knee が下がる (ch 1 → 80°)
   - [ ] 人差し指を開く → FR knee が上がる (ch 3 → 80°)
   - [ ] 人差し指を閉じる → FR knee が下がる (ch 3 → 0°)
   - [ ] 中指を開く → BL knee が上がる (ch 5 → 0°)
   - [ ] 中指を閉じる → BL knee が下がる (ch 5 → 80°)
   - [ ] 薬指を開く → BR knee が上がる (ch 7 → 80°)
   - [ ] 薬指を閉じる → BR knee が下がる (ch 7 → 0°)

4. **両手同時テスト**
   - [ ] 両手を同時に開く → ヒップ前、膝上がる
   - [ ] 両手を同時に閉じる → ヒップ後ろ、膝下がる
   - [ ] 歩行動作のシミュレーション

#### 4-3. パフォーマンス確認

ブラウザのステータス表示で確認:
- **FPS**: 9-10 FPS（目標値）
- **検出時間**: 100-120 ms（目標値）
- **総検出回数**: 増加していること
- **サーボ角度**: リアルタイムで更新されること

### Phase 5: 実機歩行テスト（オプション）

#### 5-1. walk_program.ino との比較

walk_program.inoの動作と比較して、同等の動きができるか確認:

1. **クリープゲイト再現**
   - 指の開閉で歩行動作を再現
   - FL → BL → FL → BR の順に脚を動かす

2. **動作確認項目**
   - [ ] 脚が正しい順序で動く
   - [ ] ヒップと膝が連動する
   - [ ] ニュートラル位置が正しい（指90°）

---

## トラブルシューティング

### 問題1: Arduinoに接続できない

**症状:**
```
❌ Arduinoへの接続に失敗しました
```

**解決策:**
```bash
# 1. シリアルポート確認
ls -l /dev/ttyACM*
ls -l /dev/ttyUSB*

# 2. 権限確認
groups  # dialout が含まれているか確認

# 3. 権限追加（必要な場合）
sudo usermod -a -G dialout $USER
# 再ログインが必要

# 4. Arduino再接続
# USBケーブルを抜き差し

# 5. ポート名確認
python3 -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"
```

### 問題2: カメラが起動しない

**症状:**
```
❌ カメラの初期化に失敗しました
```

**解決策:**
```bash
# 1. カメラ接続確認
libcamera-hello --list-cameras

# 2. カメラモジュール有効化
sudo raspi-config
# Interface Options → Camera → Enable

# 3. 再起動
sudo reboot

# 4. 他のプロセスがカメラを使用していないか確認
sudo lsof | grep /dev/video
```

### 問題3: 手が検出されない

**症状:**
- カメラは動作するが、手のランドマークが表示されない

**解決策:**
1. **照明を改善**: 明るい場所で試す
2. **距離を調整**: カメラから30-60cm の距離
3. **手のひらを見せる**: 手のひらをカメラに向ける
4. **信頼度を下げる**: `test_hand_control.py` の `min_detection_confidence` を 0.5 に下げる

### 問題4: サーボが動かない

**症状:**
- Arduino接続は成功するが、サーボが動かない

**チェックリスト:**
- [ ] PCA9685 の電源は入っているか（LED点灯確認）
- [ ] サーボの外部電源は接続されているか（6V 10A）
- [ ] I2C配線は正しいか（SDA=A4, SCL=A5）
- [ ] 共通GND は接続されているか
- [ ] サーボケーブルは正しいチャンネルに接続されているか

**テスト方法:**
```bash
# Arduino IDEのシリアルモニタで直接テスト
S0090  # ch 0 を 90度に
```

### 問題5: サーボの動作方向が逆

**症状:**
- 指を開くと逆に動く

**解決策:**
`src/hand_control/finger_mapper.py` の `SERVO_CONFIG` で `open` と `close` の値を入れ替える:

```python
# 修正前
2: {'type': 'right_hip', 'open': 90, 'close': 0},

# 修正後
2: {'type': 'right_hip', 'open': 0, 'close': 90},
```

### 問題6: FPSが低い

**症状:**
- FPS が 5 未満

**解決策:**
1. **モデルを軽量化**: `test_hand_control.py` で `model_complexity=0` を確認
2. **解像度を下げる**: 640x480 → 320x240
3. **検出信頼度を上げる**: `min_detection_confidence=0.9`
4. **不要なプロセスを停止**:
   ```bash
   htop  # CPU使用率を確認
   ```

### 問題7: サーボがジッターする（小刻みに震える）

**原因:**
- 手の検出が不安定
- ノイズが多い

**解決策:**
1. **移動平均フィルタを追加**: 過去数フレームの平均を取る
2. **デッドゾーンを設定**: 小さな変化は無視する
3. **照明を改善**: 安定した明るさ

---

## 付録

### A. シリアルコマンド仕様

#### サーボ制御コマンド
```
フォーマット: S[ID:2桁][ANGLE:3桁]\n
例: S00090  # ch 0 を 90度に
    S01045  # ch 1 を 45度に
```

#### 距離センサ読み取りコマンド
```
フォーマット: D[SENSOR_ID]\n
例: DL  # 左センサー
    DR  # 右センサー
```

### B. サーボ角度範囲

| チャンネル | 役割 | 最小角度 | 最大角度 | ニュートラル |
|----------|------|---------|---------|------------|
| 0 (FL hip) | 左前ヒップ | 0° (前) | 90° (後ろ) | 45° |
| 1 (FL knee) | 左前膝 | 0° (上) | 80° (下) | 40° |
| 2 (FR hip) | 右前ヒップ | 0° (後ろ) | 90° (前) | 45° |
| 3 (FR knee) | 右前膝 | 0° (下) | 80° (上) | 40° |
| 5 (BL knee) | 左後膝 | 0° (上) | 80° (下) | 40° |
| 6 (BR hip) | 右後ヒップ | 0° (後ろ) | 90° (前) | 45° |
| 7 (BR knee) | 右後膝 | 0° (下) | 80° (上) | 40° |
| 8 (BL hip) | 左後ヒップ | 0° (前) | 90° (後ろ) | 45° |

### C. 参考ファイル

- **設定**: `src/hand_control/finger_mapper.py`
- **テスト**: `tests/test_hand_control.py`
- **検証**: `tests/verify_finger_mapper_simple.py`
- **Arduino**: `arduino/robot_controller/robot_controller.ino`
- **元のプログラム**: `walk_program.ino`

### D. よくある質問（FAQ）

**Q1: カメラの解像度は変更できますか？**
A: はい。`test_hand_control.py` の `CameraController(resolution=(640, 480))` を変更してください。ただし、解像度を上げるとFPSが下がります。

**Q2: サーボを16台すべて使えますか？**
A: はい。`SERVO_MAPPING` と `SERVO_CONFIG` を拡張することで16台すべて使用可能です。

**Q3: TPU版はありますか？**
A: はい。`tests/test_hand_control_tpu.py` でGoogle Coral TPUを使用した高速版が利用可能です（別途セットアップが必要）。

**Q4: ログファイルはどこに保存されますか？**
A: 現在はコンソール出力のみです。ログファイルに保存したい場合は、`logging.basicConfig()` で `filename` を指定してください。

---

## まとめ

この手順書に従って動作確認を実施してください。問題が発生した場合は、トラブルシューティングセクションを参照してください。

**動作確認完了チェックリスト:**
- [ ] Arduinoのコンパイル・アップロード成功
- [ ] カメラ動作確認完了
- [ ] Arduino-RaspberryPi通信確認完了
- [ ] 手検出動作確認完了
- [ ] 左手8指の動作確認完了（ヒップ制御）
- [ ] 右手8指の動作確認完了（膝制御）
- [ ] 両手同時制御確認完了
- [ ] FPS 9-10達成
- [ ] walk_program.inoとの互換性確認完了

すべてのチェックが完了したら、実機での歩行テストに進んでください！

---

**作成日**: 2025-12-19
**バージョン**: 1.0
**対象システム**: Hand Control System (walk_program.ino準拠)
