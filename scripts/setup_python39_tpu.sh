#!/bin/bash
# Python 3.9 + PyCoral環境セットアップスクリプト
# Edge TPU (Google Coral)を使用するための環境構築

set -e  # エラー時に停止

echo "=================================================="
echo "Python 3.9 + PyCoral Setup Script"
echo "=================================================="

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 依存関係のインストール
echo -e "\n${YELLOW}Step 1: Installing build dependencies...${NC}"
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev libcap-dev

echo -e "${GREEN}✓ Dependencies installed${NC}"

# 2. pyenvのインストール確認
if [ ! -d "$HOME/.pyenv" ]; then
    echo -e "\n${YELLOW}Step 2: Installing pyenv...${NC}"
    curl https://pyenv.run | bash

    # bashrcに設定を追加
    if ! grep -q "PYENV_ROOT" ~/.bashrc; then
        echo '' >> ~/.bashrc
        echo '# pyenv configuration' >> ~/.bashrc
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
        echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
        echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
    fi

    echo -e "${GREEN}✓ pyenv installed${NC}"
else
    echo -e "\n${GREEN}Step 2: pyenv already installed${NC}"
fi

# pyenv環境変数を設定
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"

# 3. Python 3.9.16のインストール
if ! pyenv versions | grep -q "3.9.16"; then
    echo -e "\n${YELLOW}Step 3: Installing Python 3.9.16...${NC}"
    echo -e "${YELLOW}This may take 30-60 minutes...${NC}"
    env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.9.16
    echo -e "${GREEN}✓ Python 3.9.16 installed${NC}"
else
    echo -e "\n${GREEN}Step 3: Python 3.9.16 already installed${NC}"
fi

# 4. プロジェクトでPython 3.9を設定
echo -e "\n${YELLOW}Step 4: Setting Python 3.9.16 for this project...${NC}"
cd "$(dirname "$0")/.."
pyenv local 3.9.16
echo -e "${GREEN}✓ Python 3.9.16 set as local version${NC}"

# 5. pipのアップグレード
echo -e "\n${YELLOW}Step 5: Upgrading pip...${NC}"
python -m pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ pip upgraded${NC}"

# 6. PyCoralのインストール
echo -e "\n${YELLOW}Step 6: Installing PyCoral...${NC}"
python -m pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
echo -e "${GREEN}✓ PyCoral installed${NC}"

# 7. NumPyのダウングレード（互換性のため）
echo -e "\n${YELLOW}Step 7: Installing compatible NumPy version...${NC}"
python -m pip install "numpy<2.0"
echo -e "${GREEN}✓ NumPy 1.x installed${NC}"

# 8. その他の依存関係のインストール
echo -e "\n${YELLOW}Step 8: Installing other dependencies...${NC}"
python -m pip install picamera2 pyserial
echo -e "${GREEN}✓ Additional dependencies installed${NC}"

# 9. 動作確認
echo -e "\n${YELLOW}Step 9: Verifying installation...${NC}"
python --version
python -c "from pycoral.utils import edgetpu; print('PyCoral version:', edgetpu.get_runtime_version())" 2>/dev/null && \
    echo -e "${GREEN}✓ PyCoral working${NC}" || \
    echo -e "${RED}✗ PyCoral not working${NC}"

# Edge TPUデバイスの確認
if lsusb | grep -q "Global Unichip"; then
    echo -e "${GREEN}✓ Edge TPU device detected${NC}"
else
    echo -e "${YELLOW}⚠ Edge TPU device not detected (make sure it's connected)${NC}"
fi

echo -e "\n${GREEN}=================================================="
echo -e "Setup Complete!"
echo -e "==================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart your shell or run: source ~/.bashrc"
echo "  2. Verify setup: python tests/test_tpu_basic.py"
echo "  3. Run performance test: python tests/test_camera_tpu_fps.py"
echo ""
echo "Environment details:"
echo "  Python: $(python --version)"
echo "  Location: $(which python)"
echo "  Project: $(pwd)"
