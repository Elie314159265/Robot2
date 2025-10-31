# カメラセットアップガイド

## 概要

本ドキュメントは、RaspberryPi 4でCamera Module 3を動作させるためのセットアップ手順を説明します。

Ubuntu Nobleを使用している場合、libcameraをソースからビルドする必要があります。

## 動作確認環境

- **OS**: Ubuntu Server 24.04 LTS (Noble, ARM64)
- **RaspberryPi**: 4 (8GB RAM)
- **Python**: 3.12
- **Camera**: RaspberryPi Camera Module 3

## セットアップ手順

### 1. ビルド依存ライブラリのインストール

```bash
sudo apt update
sudo apt install -y git meson ninja-build build-essential cmake \
  libboost-dev libdrm-dev libexif-dev libjpeg-dev libtiff5-dev \
  libpng-dev libcamera-dev libboost-program-options-dev
```

### 2. Pythonユーティリティのインストール

```bash
python3 -m pip install ply --break-system-packages
```

### 3. libcameraのビルドとインストール

```bash
# ソースコードをクローン
cd /tmp
git clone https://github.com/raspberrypi/libcamera.git
cd libcamera

# Mesonビルドセットアップ
meson setup build

# ビルド（CPUコア数に応じて時間がかかります）
ninja -C build

# システムにインストール
sudo ninja -C build install

# ldconfigを更新
sudo ldconfig
```

### 4. libcameraPythonバインディングの確認

```bash
ldconfig -p | grep libcamera
```

出力例:
```
libcamera.so.0.5 => /usr/local/lib/aarch64-linux-gnu/libcamera.so.0.5
libcamera.so => /usr/local/lib/aarch64-linux-gnu/libcamera.so
```

### 5. picamera2のインストール

```bash
python3 -m pip install picamera2 --break-system-packages
```

### 6. Pythonライブラリパスの設定

Ubuntu Nobleの場合、picamera2がシステムlibcameraパスを認識するために、以下の設定が必要な場合があります:

```bash
# ~/.bashrc に追加
export LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
export PKG_CONFIG_PATH=/usr/local/lib/aarch64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH
```

その後、シェルを再起動:
```bash
source ~/.bashrc
```

### 7. カメラの有効化

ブートコンフィグでカメラを有効化:

```bash
sudo nano /boot/firmware/config.txt
```

以下の行を確認/追加:
```ini
camera_auto_detect=1
dtoverlay=imx708
```

その後、再起動:
```bash
sudo reboot
```

### 8. カメラの確認

ビルドしたlibcameraツールを使用:

```bash
libcamera-hello --list-cameras
```

または、picamera2テストを実行:
```bash
python3 tests/test_camera.py
```

## トラブルシューティング

### エラー: "Module not found: pykms"

**原因**: picamera2がGUIプレビュー機能を初期化しようとしているが、pykmsがインストールされていない。

**解決策**:
- 本プロジェクトではモックカメラにフォールバックします
- または、GUI環境が必要な場合は、Raspberry Pi OSを使用してください

### エラー: "libcamera not found"

**原因**: ldconfigがキャッシュを更新していない

**解決策**:
```bash
sudo ldconfig
```

その後、Pythonプロセスを再起動

### エラー: "Camera not detected"

**原因**: カメラが無効化されている

**解決策**:
```bash
vcgencmd get_camera
# 出力: supported=0 detected=0 の場合は無効

# /boot/firmware/config.txt を編集
sudo nano /boot/firmware/config.txt
# camera_auto_detect=1 に変更

sudo reboot
```

## テスト実行

Phase 1カメラテストを実行:

```bash
python3 tests/test_camera.py
```

期待される出力:
```
PHASE 1: CAMERA SETUP TEST SUITE
======================================================================

✓ Initialization: PASSED
✓ Start/Stop: PASSED
✓ Frame Capture: PASSED (30+ FPS)
✓ Context Manager: PASSED
✓ Camera Info: PASSED

Total: 5 passed, 0 failed
```

## パフォーマンス

- **フレームレート**: 30+ FPS @ 640x480
- **推論遅延**: < 50ms
- **メモリ使用量**: ~200MB (基本動作)

## 注意事項

### 電源管理
- カメラモジュールの電流消費は最小限
- サーボモータなどの外部デバイスを接続する場合は、**独立した電源を使用**してください
- RaspberryPiの電源は10A以上を推奨

### libcameraバージョン
- ビルドしたlibcamera 0.5を使用
- システム標準のlibcamera 0.2とは非互換

### picamera2互換性
- picamera2 0.3.31以上を推奨
- ビルドしたlibcameraはpicamera2 0.3.31で動作確認済み

## 参考資料

- [RaspberryPi libcamera公式](https://github.com/raspberrypi/libcamera)
- [picamera2ドキュメント](https://github.com/raspberrypi/picamera2)
- [Ubuntu on RaspberryPi](https://ubuntu.com/download/raspberry-pi)

## サポート

トラブルが発生した場合:

1. ログを確認: `dmesg | tail -20`
2. カメラ接続を確認
3. ldconfigキャッシュを更新: `sudo ldconfig`
4. Pythonプロセスを再起動
5. RaspberryPiを再起動
