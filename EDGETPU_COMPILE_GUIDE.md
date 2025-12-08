# EdgeTPU コンパイルガイド

Hand LandmarkモデルをEdgeTPU用にコンパイルする詳細手順

## 🎯 概要

**エラー**: `Error opening file for reading: hand_landmark_256x256_integer_quant.tflite`

**原因**: ファイルがColabにアップロードされていない

**所要時間**: 10-15分

## 📋 必要なもの

1. Googleアカウント（Colab用）
2. `hand_landmark_new_256x256_integer_quant.tflite` ファイル（2.4MB）
   - ローカルに既にダウンロード済み: `/tmp/hand_landmark_new_256x256_integer_quant.tflite`

## 🚀 手順

### ステップ1: モデルをローカルPCにコピー

RaspberryPiから自分のPCにモデルファイルをコピーします：

```bash
# RaspberryPi上で実行
# 方法1: scpコマンド（別のPCから実行）
scp worker1@192.168.0.12:/tmp/hand_landmark_new_256x256_integer_quant.tflite ~/Downloads/

# 方法2: HTTPサーバーを起動してブラウザからダウンロード
cd /tmp
python3 -m http.server 8888
# ブラウザで http://192.168.0.12:8888 にアクセスしてダウンロード
```

### ステップ2: Google Colabを開く

1. ブラウザで https://colab.research.google.com/ にアクセス
2. 新しいノートブックを作成（「ファイル」→「ノートブックを新規作成」）

### ステップ3: EdgeTPUコンパイラをインストール

Colabの最初のセルに以下をコピー＆ペーストして実行（Shift+Enter）：

```python
# EdgeTPUコンパイラのインストール
!curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
!echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
!sudo apt-get update
!sudo apt-get install -y edgetpu-compiler

# バージョン確認
!edgetpu_compiler --version
```

**期待される出力**:
```
Edge TPU Compiler version 16.0.384591198
```

### ステップ4: モデルファイルをアップロード

新しいセルで実行：

```python
# ファイルアップロード
from google.colab import files
uploaded = files.upload()

# アップロードされたファイルを確認
!ls -lh *.tflite
```

1. 「ファイルを選択」ボタンが表示される
2. ステップ1でダウンロードした `hand_landmark_new_256x256_integer_quant.tflite` を選択
3. アップロード完了まで待つ（2.4MB、数秒）

### ステップ5: EdgeTPU用にコンパイル

新しいセルで実行：

```python
# コンパイル実行（5-30秒かかる）
!edgetpu_compiler hand_landmark_new_256x256_integer_quant.tflite

# 結果確認
!ls -lh *_edgetpu.tflite
```

**成功時の出力例**:
```
Operator                       Count      Status

FULLY_CONNECTED                7          Mapped to Edge TPU
RESHAPE                        4          Operation is working on non-4D tensor
...

Edge TPU Compiler version 16.0.384591198
Model compiled successfully in 2034 ms.

Input model: hand_landmark_new_256x256_integer_quant.tflite
Input size: 2.39MiB
Output model: hand_landmark_new_256x256_integer_quant_edgetpu.tflite
Output size: 2.63MiB
On-chip memory used for caching model parameters: 2.39MiB
```

### ステップ6: コンパイル結果を確認

新しいセルで実行：

```python
# コンパイルログを確認
!cat hand_landmark_new_256x256_integer_quant_edgetpu.log
```

**重要な確認項目**:
- `Mapped to Edge TPU` の数が多いほど良い（TPU上で実行される演算）
- `Operation is working on non-4D tensor` などは問題なし

### ステップ7: コンパイル済みモデルをダウンロード

新しいセルで実行：

```python
# ダウンロード
from google.colab import files
files.download('hand_landmark_new_256x256_integer_quant_edgetpu.tflite')
```

ブラウザのダウンロードフォルダに保存されます。

### ステップ8: RaspberryPiにコピー

PCからRaspberryPiにモデルをコピー：

```bash
# 自分のPCから実行
scp ~/Downloads/hand_landmark_new_256x256_integer_quant_edgetpu.tflite worker1@192.168.0.12:/home/worker1/robot_pk/models/
```

または、HTTPサーバー経由：

```bash
# PC側でHTTPサーバーを起動
cd ~/Downloads
python3 -m http.server 8889

# RaspberryPi側でダウンロード
cd /home/worker1/robot_pk/models/
wget http://<PCのIPアドレス>:8889/hand_landmark_new_256x256_integer_quant_edgetpu.tflite
```

## ✅ 完了

以下のファイルが作成されました：

- `hand_landmark_new_256x256_integer_quant_edgetpu.tflite` (約2.6MB)
- `hand_landmark_new_256x256_integer_quant_edgetpu.log` (コンパイルログ)

## 🎬 より簡単な方法：Jupyter Notebookを使用

`scripts/compile_hand_landmark_edgetpu.ipynb` を使用する場合：

1. ノートブックをGoogle Colabにアップロード
2. 各セルを順番に実行
3. 自動的にモデルがダウンロードされる

## 🔧 トラブルシューティング

### エラー1: "Error opening file for reading"

**原因**: ファイルがアップロードされていない

**解決策**:
```python
# ファイルの存在を確認
import os
print(os.listdir('.'))

# ファイルが無い場合、再度アップロード
from google.colab import files
uploaded = files.upload()
```

### エラー2: "Model is not fully quantized"

**原因**: Integer量子化されていないモデルを使用している

**解決策**: 正しいファイル名を確認
- ✅ 正: `hand_landmark_new_256x256_integer_quant.tflite`
- ❌ 誤: `hand_landmark_256x256.tflite` (量子化なし)

### エラー3: "Internal compiler error"

**原因**: モデルの構造がEdgeTPUに対応していない

**解決策**: PINTO_model_zooの別のバージョンを試す、または既存のEdgeTPU版モデルを使用

## 📊 性能比較

| モデル | TPU対応 | 検出時間 | FPS |
|--------|---------|----------|-----|
| MediaPipe Hands (CPU) | ❌ | 125ms | 8 |
| Integer量子化版 (部分TPU) | ⚠️ | 40-60ms | 16-25 |
| **EdgeTPU版** | ✅ | **10-20ms** | **50-100** |

コンパイル後、**5-10倍の高速化**が期待できます！

## 📚 参考リンク

- [Edge TPU Compiler公式](https://www.coral.ai/docs/edgetpu/compiler)
- [Google Colab EdgeTPUチュートリアル](https://colab.research.google.com/github/google-coral/tutorials/blob/master/compile_for_edgetpu.ipynb)
- [PINTO_model_zoo](https://github.com/PINTO0309/PINTO_model_zoo/tree/main/033_Hand_Detection_and_Tracking)

## 💡 ヒント

- コンパイルは一度だけ実行すればOK（永久に使用可能）
- ログファイルで各演算のTPUマッピング状況を確認できる
- モデルファイルサイズが若干増える（2.4MB → 2.6MB）のは正常

---

**作成日**: 2025-12-08
**対象**: PINTO_model_zoo Model #033 Hand Landmark
