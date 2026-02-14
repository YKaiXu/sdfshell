#!/usr/bin/env bash
# SDFCOM 安装脚本

set -e

echo "=== SDFCOM Installation Script ==="

# 检查Python版本
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION"

# 创建虚拟环境
VENV_DIR="${HOME}/.sdfcom/venv"
echo "Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 安装依赖
echo "Installing dependencies..."
pip install --upgrade pip
pip install paramiko paramiko-expect pyte

# 安装sdfcom skill到nanobot
SKILL_DIR="${HOME}/.nanobot/skills/sdfcom"
echo "Installing skill to $SKILL_DIR..."
mkdir -p "$SKILL_DIR"
cp -r ./* "$SKILL_DIR/" 2>/dev/null || true

echo ""
echo "=== Installation Complete ==="
echo "Virtual environment: $VENV_DIR"
echo "Skill installed to: $SKILL_DIR"
echo ""
echo "To activate: source $VENV_DIR/bin/activate"
echo "To use with nanobot: restart nanobot gateway"
