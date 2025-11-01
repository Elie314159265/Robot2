# Edge TPU セットアップガイド

このドキュメントは、RaspberryPi 4でGoogle Coral Edge TPU (USB Accelerator)を使用してカメラのFPSを向上させる手順をまとめたものです。

## 問題の背景

### 元の問題
- **Python 3.13環境**: PyCoralがPython 3.9までしか対応していない
- **TensorFlow 2.20**: Edge TPU delegateが非推奨、LiteRTへの移行期
- **CPU推論の性能**: 推論時間160ms、FPS 6-15程度

### 解決策
Python 3.9環境を構築してPyCoralを使用することで、Edge TPUを有効化

## セットアップ手順

### 自動セットアップ（推奨）

```bash
./scripts/setup_python39_tpu.sh
```

このスクリプトは以下を自動的に実行します:
1. ビルド依存関係のインストール
2. pyenvのインストール
3. Python 3.9.16のビルドとインストール
4. PyCoralと必要なライブラリのインストール
5. 動作確認

**所要時間**: 約30-60分（Python 3.9のビルドに時間がかかります）

### 手動セットアップ

#### 1. 依存関係のインストール

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev libcap-dev
```

#### 2. pyenvのインストール

```bash
curl https://pyenv.run | bash
```

`.bashrc`に以下を追加:

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

シェルを再起動:

```bash
source ~/.bashrc
```

#### 3. Python 3.9.16のインストール

```bash
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.9.16
cd /home/worker1/robot_pk
pyenv local 3.9.16
```

#### 4. PyCoralのインストール

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
python -m pip install "numpy<2.0"  # NumPy 2.0互換性問題の回避
python -m pip install picamera2 pyserial
```

## 動作確認

### 1. TPU基本テスト

```bash
python tests/test_tpu_basic.py
```

**期待される出力**:
```
✅ PASS: PyCoral Import
✅ PASS: TPU Detection
✅ PASS: Model Loading
✅ PASS: Inference Speed

Inference Speed Test Results:
   Average: 14.92ms
   Min:     14.13ms
   Max:     16.79ms
   Expected FPS: 67.0
   ✅ PASS: Inference time < 20ms (target met)
```

### 2. カメラ+TPU統合テスト

```bash
# モックカメラモードでテスト
MOCK_CAMERA=1 python tests/test_camera_tpu_fps.py
```

**期待される結果**:
```
Metric               CPU             TPU             Improvement
-----------------------------------------------------------------
FPS                  6.04            26.37           436.5%
Avg Inference (ms)   144.27          16.72           8.6x faster
```

### 3. 実カメラでのテスト

```bash
# カメラが接続されている場合
python tests/test_camera_tpu_fps.py
```

## パフォーマンス比較

| 指標 | CPU版 (Python 3.13) | TPU版 (Python 3.9) | 改善率 |
|------|---------------------|-------------------|--------|
| **推論時間** | 144.27 ms | 16.72 ms | **8.6倍高速化** |
| **FPS** | 6.04 | 26.37 | **4.4倍向上** |
| **目標達成** | ❌ 不達 | ✅ ほぼ達成 |

### 目標値との比較

| 指標 | 目標 | CPU版 | TPU版 | 達成状況 |
|------|------|-------|-------|----------|
| 推論時間 | < 20ms | 144.27ms | 16.72ms | ✅ 達成 |
| FPS | 30 | 6.04 | 26.37 | ⚠️ ほぼ達成 |

**注**: モックカメラでのテスト結果。実カメラでは性能が異なる可能性があります。

## トラブルシューティング

### PyCoralのインポートエラー

```python
AttributeError: _ARRAY_API not found
```

**原因**: NumPy 2.0との互換性問題

**解決策**:
```bash
python -m pip install "numpy<2.0"
```

### Edge TPUが検出されない

```bash
lsusb | grep "Global Unichip"
```

- デバイスが表示されない場合、USBケーブルを接続し直す
- 別のUSBポートを試す
- `sudo apt install libedgetpu1-std`を実行

### Python環境の切り替え

```bash
# 現在のPythonバージョン確認
python --version

# pyenvで利用可能なバージョン確認
pyenv versions

# プロジェクト用のPythonバージョン確認
cat .python-version

# 環境変数を再読み込み
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

## 技術詳細

### アーキテクチャ

```
┌─────────────────────────────────────────┐
│ Application Layer                       │
│  ├─ Camera Controller (picamera2)       │
│  └─ Detection Loop                      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Python 3.9 + PyCoral                    │
│  └─ pycoral.utils.edgetpu               │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ TensorFlow Lite Runtime 2.5.0           │
│  └─ Edge TPU Delegate                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ libedgetpu.so.1 (C++ Library)           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│ Google Coral USB Accelerator            │
│  (Edge TPU Hardware)                    │
└─────────────────────────────────────────┘
```

### 使用モデル

- **モデル**: SSD MobileNet V2 (COCO)
- **量子化**: INT8
- **入力サイズ**: 300x300x3
- **出力**: 検出ボックス、クラス、スコア
- **対象クラス**: `sports ball` (COCO class 37)

### 参考資料

- [PyCoral Documentation](https://coral.ai/docs/reference/py/)
- [Edge TPU Investigation Report](./tpu-investigation-report.md)
- [Coral Get Started Guide](https://coral.ai/docs/accelerator/get-started/)

## まとめ

Edge TPUの有効化により、以下の改善が達成されました:

✅ **推論時間**: 144ms → 17ms (8.6倍高速化)
✅ **FPS**: 6 → 26 (4.4倍向上)
✅ **リアルタイム検出**: ほぼ目標達成（30 FPS目標に対し26 FPS）

この性能向上により、動くボールの検出・追跡が実用レベルで可能になりました。
