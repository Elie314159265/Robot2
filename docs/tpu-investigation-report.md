# Edge TPU 動作確認調査報告書

**日付**: 2025年11月1日
**システム**: Raspberry Pi 4 (8GB) + Google Coral USB Accelerator
**OS**: Raspberry Pi OS (Debian Trixie, 64-bit)
**Python**: 3.13.5

---

## 問題の概要

Google Coral Edge TPU がTensorFlow 2.20 + Python 3.13環境で正常に動作しない問題が発生。

### 症状

```python
# Edge TPU delegateの読み込みに失敗
ValueError: Failed to load delegate from libedgetpu.so.1

# TPUコンパイル済みモデルの実行に失敗
RuntimeError: Encountered unresolved custom op: edgetpu-custom-op
```

---

## 調査結果

### 1. 根本原因の特定

#### 1.1 Python 3.13 の互換性問題

- **PyCoral**: Python 3.9までしか対応していない
- **公式配布**: PyPI wheelはPython 3.6-3.9用のみ
- **apt-get版**: `python3-pycoral`はpython3 (< 3.10)に依存

参考:
- GitHub Issue: [Python 3.10 and 3.11 support? · Issue #85](https://github.com/google-coral/pycoral/issues/85)
- GitHub Issue: [Update pycoral for Python 3.11 · Issue #137](https://github.com/google-coral/pycoral/issues/137)

#### 1.2 TensorFlow 2.20 の変更

- **非推奨化**: `tf.lite.Interpreter`が非推奨になり、TF 2.20で削除予定
- **LiteRT移行**: 新しい`ai-edge-litert`パッケージへの移行を推奨
- **ARM64未対応**: `ai-edge-litert`のPython 3.13対応ARM64 wheelが未リリース

公式警告メッセージ:
```
Warning: tf.lite.Interpreter is deprecated and is scheduled for deletion in
TF 2.20. Please use the LiteRT interpreter from the ai_edge_litert package.
```

参考:
- [LiteRT Migration Guide](https://ai.google.dev/edge/litert/migration)
- [ai-edge-litert PyPI](https://pypi.org/project/ai-edge-litert/)

#### 1.3 libedgetpu.so.1 の状態

✅ **正常動作を確認**:

```bash
$ ldconfig -p | grep edgetpu
libedgetpu.so.1 (libc6,AArch64) => /lib/aarch64-linux-gnu/libedgetpu.so.1

$ python3 -c "from ctypes.util import find_library; print(find_library('edgetpu'))"
libedgetpu.so.1

$ dpkg -l | grep edgetpu
ii  libedgetpu1-std:arm64  16.0  arm64  Support library for Edge TPU
```

**シンボル確認**:
```python
import ctypes
lib = ctypes.CDLL('libedgetpu.so.1')
lib.tflite_plugin_create_delegate  # ✅ 存在確認
```

### 2. 問題の構造

```
┌─────────────────────────────────────────────────────────────┐
│  Python 3.13.5                                              │
│  └─ TensorFlow 2.20.0                                       │
│      └─ tf.lite.Interpreter (DEPRECATED)                    │
│          └─ experimental.load_delegate('libedgetpu.so.1')   │
│              └─ ❌ ValueError: Failed to load delegate       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Python 3.13.5                                              │
│  └─ PyCoral (NOT AVAILABLE)                                 │
│      └─ ❌ pip: No matching distribution found               │
│      └─ ❌ apt: Depends: python3 (< 3.10)                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ai-edge-litert (NEW API)                                   │
│  └─ ❌ No ARM64 wheel for Python 3.13                        │
└─────────────────────────────────────────────────────────────┘
```

### 3. 技術的詳細

#### 3.1 Edge TPU Delegate の仕組み

Edge TPUでモデルを実行するには、TensorFlow Liteインタプリタに**delegate**を渡す必要があります。

正常な使用方法（Python 3.9 + PyCoral）:
```python
from pycoral.utils import edgetpu
interpreter = edgetpu.make_interpreter('model_edgetpu.tflite')
interpreter.allocate_tensors()
```

または（TensorFlow Lite API）:
```python
import tflite_runtime.interpreter as tflite
interpreter = tflite.Interpreter(
    model_path='model_edgetpu.tflite',
    experimental_delegates=[tflite.load_delegate('libedgetpu.so.1')]
)
```

#### 3.2 TPUコンパイル済みモデルの制約

Edge TPUコンパイラで生成されたモデル（`*_edgetpu.tflite`）には、カスタムオペレーター`edgetpu-custom-op`が含まれています。

このオペレーターはEdge TPU delegate**なしでは実行できません**:

```python
# TPUモデルをCPUで実行しようとすると失敗
interpreter = tf.lite.Interpreter('model_edgetpu.tflite')
interpreter.allocate_tensors()
# RuntimeError: Encountered unresolved custom op: edgetpu-custom-op
```

---

## 解決策の選択肢

### オプション 1: Python 3.9環境の構築（推奨）⭐

**方法**: pyenvまたはDockerでPython 3.9環境を作成し、PyCoralをインストール

#### pyenv方式

```bash
# 1. pyenvのインストール
curl https://pyenv.run | bash

# 2. Python 3.9.16のインストール
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.9.16

# 3. プロジェクト用Python設定
cd /home/worker1/robot_pk
pyenv local 3.9.16

# 4. PyCoralのインストール
pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
```

**メリット**:
- ✅ 公式サポートの方法
- ✅ PyCoral APIが使える（高レベルAPI、簡単）
- ✅ 完全なTPU加速が可能
- ✅ ドキュメント・サンプルが豊富

**デメリット**:
- ⚠️ pyenvのビルドに時間がかかる（30分〜1時間）
- ⚠️ Python環境の管理が複雑化

#### Docker方式

```bash
# Debian 10ベースのコンテナでPython 3.9を使用
docker run -it --privileged \
  --device /dev/bus/usb \
  -v /home/worker1/robot_pk:/workspace \
  debian:buster-slim
```

---

### オプション 2: CPU版モデルで継続（暫定対策）🔧

**方法**: TPU版ではなくCPU版モデル（`ssd_mobilenet_v2_coco_quant_postprocess.tflite`）を使用

```python
import tensorflow as tf

model_path = "models/ssd_mobilenet_v2_coco_quant_postprocess.tflite"  # CPU版
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()
# ✅ 動作する
```

**メリット**:
- ✅ 現在の環境で即座に動作
- ✅ 追加インストール不要
- ✅ コード変更最小

**デメリット**:
- ❌ 推論時間: 160ms/frame（目標: <20ms）
- ❌ FPS: 6-15（目標: 30+）
- ❌ 動くボールの検出が困難

**適用シナリオ**:
- プロトタイプ開発
- アルゴリズムのテスト
- 静止物体の検出

---

### オプション 3: TensorFlow 2.5へのダウングレード（非推奨）⚠️

**方法**: TensorFlow 2.5.0とtflite-runtime 2.5.0を使用

```bash
pip uninstall tensorflow
pip install tensorflow==2.5.0
```

**メリット**:
- ✅ Edge TPU delegateが動作する可能性

**デメリット**:
- ❌ ARM64版のTensorFlow 2.5 wheelが利用不可
- ❌ Python 3.13非対応
- ❌ セキュリティアップデート無し
- ❌ 他のパッケージとの互換性問題

**結論**: **実用的ではない**

---

### オプション 4: カスタムビルド（上級者向け）🔨

**方法**: TensorFlow LiteまたはLiteRTをソースからビルド

```bash
# LiteRTをソースからビルド
git clone https://github.com/google-ai-edge/LiteRT.git
cd LiteRT
# ... ビルド手順（複雑）
```

**メリット**:
- ✅ 最新Python対応
- ✅ 最適化オプション調整可能

**デメリット**:
- ❌ ビルド時間: 数時間
- ❌ 複雑な依存関係
- ❌ メンテナンスコスト高
- ❌ 専門知識が必要

---

## 推奨アクション

### フェーズ1: 短期（即時対応）

✅ **CPU版モデルで開発継続**

```python
# src/detection/edgetpu_detector.py を使用
from src.detection.edgetpu_detector import EdgeTPUDetector

detector = EdgeTPUDetector(
    model_path='models/ssd_mobilenet_v2_coco_quant_postprocess.tflite',
    labels_path='models/coco_labels.txt',
    threshold=0.6
)

# 自動的にCPUモードにフォールバック
detections = detector.detect_balls(frame)
```

**期待される性能**:
- FPS: 15前後（検出頻度調整あり）
- 静止ボール検出: ✅ 可能
- 動くボール検出: ⚠️ 困難

### フェーズ2: 中期（1-2日後）

⭐ **Python 3.9環境構築 + PyCoral**

```bash
# pyenv セットアップスクリプト実行
./scripts/setup_python39_pycoral.sh
```

期待される改善:
- 推論時間: 160ms → <20ms (8倍高速化)
- FPS: 15 → 30+ (2倍向上)
- 動くボール検出: ✅ 可能

### フェーズ3: 長期（将来）

🔮 **LiteRT正式対応待ち**

- `ai-edge-litert`のPython 3.13 + ARM64対応版リリース待ち
- Google公式のアップデートを監視

---

## 実装済みの対策

### EdgeTPUDetector クラス

自動フォールバック機能を持つ検出器を実装しました:

**src/detection/edgetpu_detector.py**

```python
class EdgeTPUDetector:
    """
    自動的にPyCoral → TensorFlow Lite CPU にフォールバックする検出器
    """

    def __init__(self, model_path, labels_path, threshold=0.6):
        # 1. PyCoralが利用可能ならそれを使う（Python 3.9環境）
        try:
            from pycoral.utils import edgetpu
            self.interpreter = edgetpu.make_interpreter(model_path)
            self.use_pycoral = True
            print("✅ Using PyCoral API (TPU accelerated)")

        # 2. PyCoralが使えなければTensorFlow Lite CPU版
        except ImportError:
            import tensorflow as tf
            cpu_model_path = model_path.replace('_edgetpu.tflite', '.tflite')
            self.interpreter = tf.lite.Interpreter(model_path=cpu_model_path)
            self.use_pycoral = False
            print("✅ Using TensorFlow Lite (CPU mode)")
```

**使用例**:

```python
# Python 3.13環境
detector = EdgeTPUDetector(
    'models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite',
    'models/coco_labels.txt'
)
# → "Using TensorFlow Lite (CPU mode)"

# Python 3.9環境（pyenv）
detector = EdgeTPUDetector(
    'models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite',
    'models/coco_labels.txt'
)
# → "Using PyCoral API (TPU accelerated)"
```

---

## パフォーマンス比較

| モード | 推論時間 | FPS | 動くボール検出 | 備考 |
|--------|----------|-----|----------------|------|
| **CPU版（現状）** | 160ms | 6-15 | ❌ 困難 | Python 3.13 |
| **TPU版（目標）** | <20ms | 30+ | ✅ 可能 | Python 3.9 + PyCoral |
| **改善率** | **8倍** | **2倍** | - | - |

---

## 参考資料

### 公式ドキュメント

- [Run inference on the Edge TPU with Python | Coral](https://gweb-coral-full.uc.r.appspot.com/docs/edgetpu/tflite-python/)
- [LiteRT Migration Guide](https://ai.google.dev/edge/litert/migration)
- [Get started with the USB Accelerator | Coral](https://gweb-coral-full.uc.r.appspot.com/docs/accelerator/get-started)

### GitHubリソース

- [google-coral/pycoral - Python 3.10/3.11 support issue](https://github.com/google-coral/pycoral/issues/85)
- [google-ai-edge/LiteRT - 新しいランタイム](https://github.com/google-ai-edge/LiteRT)

### コミュニティ解決策

- [Installing PyCoral on Raspberry Pi 5 (bret.dk)](https://bret.dk/installing-pycoral-for-google-coral-on-raspberry-pi-5/)
- [Stack Overflow: PyCoral installation issues](https://stackoverflow.com/questions/77897444/pycoral-but-it-is-not-going-to-be-installed)

---

## まとめ

### 現状の理解

✅ **判明したこと**:
1. libedgetpu.so.1は正常にインストールされている
2. Python 3.13 + TensorFlow 2.20ではdelegateが読み込めない
3. PyCoralはPython 3.9までしか対応していない
4. CPU版モデルは現環境で動作する

❌ **動作しない理由**:
1. TensorFlow 2.20のAPIが大幅に変更された
2. LiteRTへの移行期で、ARM64 + Python 3.13対応版が未リリース
3. PyCoralのメンテナンスが遅れている

### 推奨される対応

**短期（今日）**:
- ✅ CPU版モデルで開発継続
- ✅ EdgeTPUDetectorクラスを使用
- ✅ アルゴリズム開発に集中

**中期（1-2日後）**:
- ⭐ Python 3.9環境をpyenvで構築
- ⭐ PyCoralをインストール
- ⭐ TPU加速を有効化

**長期（将来）**:
- 🔮 LiteRT正式対応を待つ
- 🔮 Python 3.13環境でTPU使用

---

**報告者**: Claude Code
**作成日**: 2025年11月1日
**バージョン**: 1.0
