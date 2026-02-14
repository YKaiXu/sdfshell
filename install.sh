#!/usr/bin/env bash
# SDFShell One-Click Installation Script / SDFShell一键安装脚本
# Auto-creates virtual environment and installs all dependencies / 自动创建虚拟环境并安装所有依赖

set -e

echo "========================================"
echo "SDFShell Installation / SDFShell安装"
echo "========================================"

# Detect system / 检测系统
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python not found / 错误: 未找到Python"
    exit 1
fi

# Check Python version / 检查Python版本
PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION / 错误: 需要Python $REQUIRED_VERSION+，当前版本 $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION / Python版本: $PYTHON_VERSION"

# Set installation directory / 设置安装目录
SKILL_DIR="${HOME}/.nanobot/skills/sdfshell"
VENV_DIR="${HOME}/.nanobot/skills/sdfshell/venv"

# Create directories / 创建目录
echo "Creating directories / 创建目录..."
mkdir -p "${HOME}/.nanobot/skills"

# Clone or update repository / 克隆或更新仓库
if [ -d "$SKILL_DIR" ]; then
    echo "Updating existing installation / 更新现有安装..."
    cd "$SKILL_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "Cloning repository / 克隆仓库..."
    git clone https://github.com/YKaiXu/sdfshell.git "$SKILL_DIR"
    cd "$SKILL_DIR"
fi

# Create virtual environment / 创建虚拟环境
echo "Creating virtual environment / 创建虚拟环境..."
$PYTHON -m venv "$VENV_DIR"

# Activate virtual environment / 激活虚拟环境
source "$VENV_DIR/bin/activate"

# Upgrade pip / 升级pip
echo "Upgrading pip / 升级pip..."
pip install --upgrade pip --quiet

# Install dependencies / 安装依赖
echo "Installing dependencies / 安装依赖..."
pip install paramiko paramiko-expect pyte --quiet

# Install nanobot (optional) / 安装nanobot（可选）
pip install nanobot --quiet 2>/dev/null || echo "Note: nanobot not in PyPI, install manually / 注意: nanobot不在PyPI，需手动安装"

# Deactivate / 退出虚拟环境
deactivate

echo ""
echo "========================================"
echo "✅ Installation Complete / 安装完成"
echo "========================================"
echo ""
echo "Skill installed to / Skill安装位置: $SKILL_DIR"
echo "Virtual environment / 虚拟环境: $VENV_DIR"
echo ""
echo "Next steps / 下一步:"
echo "1. Restart nanobot gateway / 重启nanobot gateway"
echo "2. Send message: 'com: Hello' to test / 发送消息: 'com: Hello' 测试"
echo ""
echo "Documentation / 文档: https://github.com/YKaiXu/sdfshell"
echo ""
