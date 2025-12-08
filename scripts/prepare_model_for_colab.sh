#!/bin/bash
# Hand LandmarkモデルをGoogle Colabコンパイル用に準備するスクリプト

set -e

echo "=========================================="
echo "Hand Landmark モデル準備スクリプト"
echo "=========================================="
echo ""

# モデルファイルのパス
MODEL_FILE="/tmp/hand_landmark_new_256x256_integer_quant.tflite"

# ファイルの存在確認
if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ エラー: モデルファイルが見つかりません: $MODEL_FILE"
    echo ""
    echo "まず、PINTO_model_zooからモデルをダウンロードしてください:"
    echo "  cd /tmp"
    echo "  wget https://raw.githubusercontent.com/PINTO0309/PINTO_model_zoo/main/033_Hand_Detection_and_Tracking/download.sh"
    echo "  bash download.sh"
    echo ""
    exit 1
fi

echo "✅ モデルファイルが見つかりました"
echo "   ファイル: $MODEL_FILE"
echo "   サイズ: $(du -h $MODEL_FILE | cut -f1)"
echo ""

# RaspberryPiのIPアドレスを取得
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo "=========================================="
echo "ステップ1: HTTPサーバーを起動"
echo "=========================================="
echo ""
echo "以下のコマンドでHTTPサーバーを起動します:"
echo "  python3 -m http.server 8888"
echo ""
echo "その後、PCのブラウザで以下のURLにアクセスしてダウンロードしてください:"
echo "  http://$IP_ADDRESS:8888/hand_landmark_new_256x256_integer_quant.tflite"
echo ""
echo "ダウンロード完了後、Ctrl+C でサーバーを停止してください。"
echo ""

read -p "HTTPサーバーを起動しますか? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd /tmp
    python3 -m http.server 8888
fi

echo ""
echo "=========================================="
echo "ステップ2: Google Colabでコンパイル"
echo "=========================================="
echo ""
echo "1. https://colab.research.google.com/ にアクセス"
echo "2. 新しいノートブックを作成"
echo "3. 以下のコマンドを順番に実行:"
echo ""
echo "# セル1: EdgeTPUコンパイラをインストール"
echo "!curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -"
echo "!echo \"deb https://packages.cloud.google.com/apt coral-edgetpu-stable main\" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list"
echo "!sudo apt-get update"
echo "!sudo apt-get install -y edgetpu-compiler"
echo ""
echo "# セル2: モデルファイルをアップロード"
echo "from google.colab import files"
echo "uploaded = files.upload()"
echo "# ダウンロードしたファイルを選択"
echo ""
echo "# セル3: コンパイル"
echo "!edgetpu_compiler hand_landmark_new_256x256_integer_quant.tflite"
echo "!ls -lh *_edgetpu.tflite"
echo ""
echo "# セル4: ダウンロード"
echo "from google.colab import files"
echo "files.download('hand_landmark_new_256x256_integer_quant_edgetpu.tflite')"
echo ""
echo "=========================================="
echo "ステップ3: RaspberryPiに戻す"
echo "=========================================="
echo ""
echo "コンパイル済みモデルをRaspberryPiに戻す方法:"
echo ""
echo "方法1: scpコマンド（PCから実行）"
echo "  scp ~/Downloads/hand_landmark_new_256x256_integer_quant_edgetpu.tflite worker1@$IP_ADDRESS:/home/worker1/robot_pk/models/"
echo ""
echo "方法2: HTTPサーバー経由"
echo "  # PC側で実行"
echo "  cd ~/Downloads"
echo "  python3 -m http.server 8889"
echo ""
echo "  # RaspberryPi側で実行"
echo "  cd /home/worker1/robot_pk/models/"
echo "  wget http://<PCのIP>:8889/hand_landmark_new_256x256_integer_quant_edgetpu.tflite"
echo ""
echo "=========================================="
echo "完了後の確認"
echo "=========================================="
echo ""
echo "以下のファイルが作成されているはずです:"
echo "  /home/worker1/robot_pk/models/hand_landmark_new_256x256_integer_quant_edgetpu.tflite"
echo ""
echo "詳細なガイドは EDGETPU_COMPILE_GUIDE.md を参照してください。"
echo ""
