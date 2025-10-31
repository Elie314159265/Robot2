# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

学校課題：4足歩行（カニ型）ゴールキーパーロボット
- 基本機能：歩行・回転・3cm段差登り
- PK課題：飛んでくるサッカーボールを検出・追跡してブロックする

**ハードウェア構成:**
- RaspberryPi 4 (8GB, Ubuntu OS) - カメラ/TPU処理
- Arduino Uno - サーボ/センサ制御
- RaspberryPi Camera Module 3
- Google Coral TPU (Edge TPU)
- サーボモータ + PCA9685ドライバ
- 超音波距離センサ
- DCモータ（歩行用）

## システムアーキテクチャ

### ボール追跡パイプライン
1. **検出**: RaspberryPiカメラで撮影 → TPUでCOCOモデル推論 → "sports ball"検出
2. **追跡**: PID制御でサーボを動かし、ボールを画面中央に追従
3. **位置推定**: サーボ角度(θ) + 超音波距離(d) → 2D座標変換: x=d·cos(θ), y=d·sin(θ)
4. **予測**: 軌道予測でボールの着地点を計算

### コンポーネント間通信
```
RaspberryPi (カメラ + TPU) ←→ Arduino (サーボ + センサ)
         ↓ シリアル通信              ↓
      ボール位置情報           モータ制御コマンド
```

### モジュール構成
```
src/
├── camera/          # picamera2によるカメラ制御、フレーム処理
├── detection/       # TPU推論エンジン、ボール検出
├── tracking/        # サーボ制御用PIDコントローラ
├── positioning/     # 座標変換、カルマンフィルタ
├── prediction/      # 軌道予測アルゴリズム
├── arduino/         # Arduinoとのシリアル通信
├── arm/             # ロボットアーム逆運動学
└── utils/           # ログ、設定管理
```

## 設計原則

1. **コンポーネント化**: 各ファイル200行以内、単一責任
2. **リアルタイム性**: 30 FPS目標、TPU推論時間<20ms
3. **段階的実装**: 各Phaseを完了・テストしてから次へ
4. **Git管理の徹底**: 動作確認毎にcommit

## 開発コマンド

### 環境セットアップ (Ubuntu Server)
```bash
# カメラセットアップ
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-pip

# TPUセットアップ
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt update
sudo apt install -y libedgetpu1-std python3-pycoral

# COCOモデルダウンロード
mkdir -p models
cd models
wget https://github.com/google-coral/test_data/raw/master/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite
wget https://github.com/google-coral/test_data/raw/master/coco_labels.txt
```

### テスト実行
```bash
# カメラテスト (Phase 1)
python3 tests/test_camera.py

# TPU検出テスト (Phase 2)
python3 tests/test_detection.py

# 追跡テスト (Phase 5)
python3 tests/test_tracking.py

# カメラデバイス確認
libcamera-hello --list-cameras
vcgencmd get_camera
```

### システム実行
```bash
# メインプログラム
python3 src/main.py

# デバッグモード
python3 src/main.py --debug
```

## 実装フェーズ

開発は以下の段階的フェーズで進行（詳細はblueprint.txt参照）:

1. **Phase 1**: カメラセットアップ（picamera2、30fps @ 640x480）
2. **Phase 2**: TPU動作確認（COCOモデルで"sports ball"検出、精度80%以上）
3. **Phase 3**: Arduino連携（シリアル通信、サーボ制御、超音波センサ）
4. **Phase 4**: リアルタイムボール検出テスト
5. **Phase 5**: カメラ追従制御（PID制御で画面中央に追従）
6. **Phase 6**: 2D位置マッピング（角度+距離→座標変換）
7. **Phase 7**: 軌道予測
8. **Phase 8**: 統合テスト

**現在のフェーズ**: Phase 1（カメラセットアップ）

## 機械学習モデル

- **使用モデル**: `ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite`
- **検出対象**: COCO class 37 ("sports ball")
- **成功基準**: 検出率80%以上、30 FPS
- **代替案**: 精度70%未満の場合、約500枚のボール画像でファインチューニング

## 重要な技術的注意点

### Ubuntu Serverでのカメラ使用
- `picamera2`ライブラリを使用（旧`picamera`は非推奨）
- libcameraベースの設定
- GUI不要（SSH経由で動作）

### リアルタイム制約
- Python GILがパフォーマンスに影響 → マルチプロセス/スレッド化
- TPUは別スレッドで動作させる
- 目標: エンドツーエンド30 FPS

### 電源管理
- **重要**: サーボとRaspberryPiの電源は必ず分離
- 最低10Aの電源推奨
- 複数サーボの同時駆動は電力不足に注意

### シリアル通信プロトコル (RaspberryPi ↔ Arduino)
- レイテンシ目標: <10ms
- プロトコル仕様は`src/arduino/serial_controller.py`と`arduino/robot_controller/robot_controller.ino`で定義

