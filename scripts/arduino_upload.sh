#!/bin/bash
# Arduino ファームウェア コンパイル & アップロード スクリプト
# 使い方: ./scripts/arduino_upload.sh

set -e  # エラーが発生したら即座に終了

# 色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}Arduino Firmware Upload Script${NC}"
echo -e "${BLUE}======================================================================${NC}"

# プロジェクトルートディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}プロジェクトディレクトリ: ${PROJECT_ROOT}${NC}"

# PATHにarduino-cliを追加
export PATH=$PATH:$PROJECT_ROOT/bin

# Step 1: Arduino-CLI確認
echo -e "\n${YELLOW}[1/5] Arduino-CLI確認中...${NC}"
if ! command -v arduino-cli &> /dev/null; then
    echo -e "${RED}❌ arduino-cli が見つかりません${NC}"
    echo -e "${YELLOW}bin/arduino-cli が存在するか確認してください${NC}"
    exit 1
fi

ARDUINO_VERSION=$(arduino-cli version | head -n 1)
echo -e "${GREEN}✅ ${ARDUINO_VERSION}${NC}"

# Step 2: ボード接続確認
echo -e "\n${YELLOW}[2/5] Arduino接続確認中...${NC}"
BOARD_INFO=$(arduino-cli board list | grep -i "arduino")

if [ -z "$BOARD_INFO" ]; then
    echo -e "${RED}❌ Arduinoが見つかりません${NC}"
    echo -e "${YELLOW}USB接続を確認してください${NC}"
    exit 1
fi

# ポート自動検出
PORT=$(arduino-cli board list | grep -i "arduino" | awk '{print $1}')
BOARD_NAME=$(arduino-cli board list | grep -i "arduino" | awk '{print $4,$5}')

echo -e "${GREEN}✅ 検出: ${BOARD_NAME} @ ${PORT}${NC}"

# Step 3: 必要なライブラリ確認
echo -e "\n${YELLOW}[3/5] ライブラリ確認中...${NC}"

check_library() {
    local LIB_NAME=$1
    if arduino-cli lib list | grep -q "$LIB_NAME"; then
        echo -e "${GREEN}  ✅ ${LIB_NAME}${NC}"
        return 0
    else
        echo -e "${YELLOW}  ⚠️  ${LIB_NAME} が見つかりません（インストール中...）${NC}"
        arduino-cli lib install "$LIB_NAME"
        echo -e "${GREEN}  ✅ ${LIB_NAME} インストール完了${NC}"
        return 0
    fi
}

check_library "Adafruit PWM Servo Driver Library"
check_library "Adafruit BusIO"

# Step 4: コンパイル
echo -e "\n${YELLOW}[4/5] コンパイル中...${NC}"
arduino-cli compile --fqbn arduino:avr:uno arduino/robot_controller

echo -e "${GREEN}✅ コンパイル成功${NC}"

# Step 5: アップロード
echo -e "\n${YELLOW}[5/5] アップロード中...${NC}"
echo -e "${BLUE}ポート: ${PORT}${NC}"
echo -e "${BLUE}ボード: arduino:avr:uno${NC}"

arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno arduino/robot_controller

echo -e "${GREEN}✅ アップロード成功${NC}"

# 完了メッセージ
echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${GREEN}✅ Arduino ファームウェア アップロード完了！${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo -e "${YELLOW}次のステップ:${NC}"
echo -e "  1. シリアルモニタで動作確認:"
echo -e "     ${BLUE}arduino-cli monitor -p ${PORT} -c baudrate=9600${NC}"
echo -e "  2. ボール追跡テスト実行:"
echo -e "     ${BLUE}python3 tests/test_ball_tracking.py${NC}"
echo -e "${BLUE}======================================================================${NC}"
