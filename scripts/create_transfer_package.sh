#!/bin/bash
# 画像をローカルPCに転送するためのZIPパッケージを作成

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TRAINING_DATA_DIR="$PROJECT_ROOT/training_data"

echo "=== 画像転送パッケージ作成 ==="
echo "プロジェクトルート: $PROJECT_ROOT"
echo

# 1. 画像数確認
IMAGE_COUNT=$(find "$TRAINING_DATA_DIR/soccer_ball" -type f \( -name "*.jpg" -o -name "*.png" \) | wc -l)
echo "画像数: $IMAGE_COUNT 枚"

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "エラー: 画像が見つかりません"
    exit 1
fi

# 2. ZIPファイル作成
cd "$TRAINING_DATA_DIR"
ZIP_FILE="soccer_ball_images.zip"

echo "ZIP作成中..."
zip -r "$ZIP_FILE" soccer_ball/ -x "*.git*" "*.DS_Store"

echo
echo "=== 作成完了 ==="
echo "ZIPファイル: $TRAINING_DATA_DIR/$ZIP_FILE"
echo "サイズ: $(du -h "$ZIP_FILE" | cut -f1)"
echo

# 3. 転送方法を表示
HOSTNAME=$(hostname -I | awk '{print $1}')
USERNAME=$(whoami)

echo "=== 転送方法 ==="
echo
echo "▼ ローカルPCで以下のコマンドを実行してください:"
echo
echo "# ダウンロード"
echo "scp $USERNAME@$HOSTNAME:$TRAINING_DATA_DIR/$ZIP_FILE ./"
echo
echo "# 解凍"
echo "unzip $ZIP_FILE"
echo
echo "=== アノテーション後のアップロード方法 ==="
echo
echo "# annotationsフォルダをZIP化（ローカルPCで）"
echo "zip -r annotations.zip annotations/"
echo
echo "# ラズパイにアップロード（ローカルPCで）"
echo "scp annotations.zip $USERNAME@$HOSTNAME:$TRAINING_DATA_DIR/"
echo
echo "# ラズパイ上で解凍（SSH接続中に）"
echo "cd $TRAINING_DATA_DIR"
echo "unzip annotations.zip"
echo

exit 0
