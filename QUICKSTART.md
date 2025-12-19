# Hand Control System - クイックスタートガイド

このガイドでは、最短で手指制御システムを起動する手順を説明します。

詳細な手順は [docs/HAND_CONTROL_SETUP.md](docs/HAND_CONTROL_SETUP.md) を参照してください。

---

## 前提条件

- RaspberryPi 4 + Camera Module 3 (セットアップ済み)
- Arduino Uno + PCA9685 + サーボモータ (配線済み)
- 必要なライブラリがインストール済み

---

## 5ステップで起動

### ステップ1: Arduinoのプログラムをアップロード

```bash
# Arduino IDE で以下のファイルを開く
arduino/robot_controller/robot_controller.ino

# コンパイルしてArduinoにアップロード
# ツール → マイコンボードに書き込む
```

### ステップ2: RaspberryPiでプロジェクトに移動

```bash
cd /home/user/Robot2
```

### ステップ3: 検証スクリプトを実行（オプション）

```bash
# walk_program.inoとの互換性を確認
python3 tests/verify_finger_mapper_simple.py
```

期待される出力:
```
✓ SERVO_CONFIGはwalk_program.inoと完全に一致
✓ SERVO_MAPPINGは正しくch 8を使用
結論: 実装は正しく、実機で動作する見込みです
```

### ステップ4: システムを起動

```bash
python3 tests/test_hand_control.py
```

起動ログを確認:
```
✅ MediaPipe Hands初期化完了
✅ FingerMapper初期化完了
✅ カメラ初期化完了
✅ Arduino接続完了
🌐 手指検出ストリーミングサーバー起動！
```

### ステップ5: ブラウザでアクセス

```bash
# RaspberryPiのIPアドレスを確認
hostname -I
```

ブラウザで以下にアクセス:
```
http://<RaspberryPiのIPアドレス>:8000
```

---

## 動作確認

### 左手テスト（ヒップ制御）

| 指 | 動作 | 期待される結果 |
|----|------|--------------|
| 親指を開く | 指 0° | FL hip が前 (0°) |
| 親指を閉じる | 指 180° | FL hip が後ろ (90°) |
| 人差し指を開く | 指 0° | FR hip が前 (90°) |
| 人差し指を閉じる | 指 180° | FR hip が後ろ (0°) |
| 中指を開く | 指 0° | BL hip が前 (0°) |
| 中指を閉じる | 指 180° | BL hip が後ろ (90°) |
| 薬指を開く | 指 0° | BR hip が前 (90°) |
| 薬指を閉じる | 指 180° | BR hip が後ろ (0°) |

### 右手テスト（膝制御）

| 指 | 動作 | 期待される結果 |
|----|------|--------------|
| 親指を開く | 指 0° | FL knee が上 (0°) |
| 親指を閉じる | 指 180° | FL knee が下 (80°) |
| 人差し指を開く | 指 0° | FR knee が上 (80°) |
| 人差し指を閉じる | 指 180° | FR knee が下 (0°) |
| 中指を開く | 指 0° | BL knee が上 (0°) |
| 中指を閉じる | 指 180° | BL knee が下 (80°) |
| 薬指を開く | 指 0° | BR knee が上 (80°) |
| 薬指を閉じる | 指 180° | BR knee が下 (0°) |

---

## トラブルシューティング

### Arduino接続エラー

```bash
# シリアルポート確認
ls -l /dev/ttyACM*

# 権限追加
sudo usermod -a -G dialout $USER
# 再ログイン
```

### カメラエラー

```bash
# カメラ確認
libcamera-hello --list-cameras

# カメラ有効化
sudo raspi-config
# Interface Options → Camera → Enable
```

### 手が検出されない

- 明るい場所で試す
- カメラから30-60cm の距離
- 手のひらをカメラに向ける

### サーボが動かない

- PCA9685 の電源確認（LED点灯）
- サーボ外部電源確認（6V 10A）
- I2C配線確認（SDA=A4, SCL=A5）
- 共通GND確認

---

## サーボチャンネルマッピング

### 左手（ヒップ制御）
- 親指 → ch 0 (FL hip)
- 人差し指 → ch 2 (FR hip)
- 中指 → **ch 8** (BL hip) ※重要: ch 4ではなくch 8
- 薬指 → ch 6 (BR hip)

### 右手（膝制御）
- 親指 → ch 1 (FL knee)
- 人差し指 → ch 3 (FR knee)
- 中指 → ch 5 (BL knee)
- 薬指 → ch 7 (BR knee)

---

## 次のステップ

1. **動作確認完了後**: walk_program.inoの歩行動作を手指で再現
2. **パフォーマンス調整**: FPSが低い場合は解像度を下げる
3. **実機テスト**: ロボットを床に置いて歩行テスト

---

## 参考リンク

- 詳細手順: [docs/HAND_CONTROL_SETUP.md](docs/HAND_CONTROL_SETUP.md)
- 検証スクリプト: [tests/verify_finger_mapper_simple.py](tests/verify_finger_mapper_simple.py)
- メインテスト: [tests/test_hand_control.py](tests/test_hand_control.py)
- 実装コード: [src/hand_control/finger_mapper.py](src/hand_control/finger_mapper.py)
- 元のプログラム: [walk_program.ino](walk_program.ino)

---

**終了するには**: `Ctrl+C`

**質問や問題**: [docs/HAND_CONTROL_SETUP.md](docs/HAND_CONTROL_SETUP.md) のトラブルシューティングセクションを参照
