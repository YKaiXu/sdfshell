#!/usr/bin/env bash
# SDFShell One-Click Installation Script
# Auto-creates virtual environment and installs all dependencies

set -e

echo "========================================"
echo "SDFShell Installation"
echo "========================================"

# Detect system
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python not found"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION"

# Set installation directory
SKILL_DIR="${HOME}/.nanobot/skills/sdfshell"
VENV_DIR="${HOME}/.nanobot/skills/sdfshell/venv"

# Create directories
echo "Creating directories..."
mkdir -p "${HOME}/.nanobot/skills"

# Clone or update repository
if [ -d "$SKILL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$SKILL_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "Cloning repository..."
    git clone https://github.com/YKaiXu/sdfshell.git "$SKILL_DIR"
    cd "$SKILL_DIR"
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON -m venv "$VENV_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing dependencies..."
pip install paramiko paramiko-expect pyte --quiet

# Install nanobot (optional)
pip install nanobot --quiet 2>/dev/null || echo "Note: nanobot not in PyPI, install manually"

# Deactivate
deactivate

echo ""
echo "========================================"
echo "✅ Installation Complete"
echo "========================================"
echo ""
echo "Skill installed to: $SKILL_DIR"
echo "Virtual environment: $VENV_DIR"
echo ""

# Restart nanobot gateway
echo "Restarting nanobot gateway..."

# Check if nanobot is installed
NANOBOT_PATH="$HOME/.local/bin/nanobot"
if [ ! -f "$NANOBOT_PATH" ]; then
    NANOBOT_PATH=$(which nanobot 2>/dev/null || echo "")
fi

if [ -n "$NANOBOT_PATH" ]; then
    # Try systemd user service first
    if systemctl --user status nanobot &>/dev/null; then
        echo "Using systemd user service..."
        systemctl --user restart nanobot
        echo "✓ Gateway restarted via systemd"
    # Try systemd system service
    elif systemctl status nanobot &>/dev/null; then
        echo "Using systemd system service..."
        sudo systemctl restart nanobot
        echo "✓ Gateway restarted via systemd"
    else
        # Manual restart
        echo "Manual restart..."
        pkill -f 'nanobot gateway' 2>/dev/null || true
        sleep 2
        nohup "$NANOBOT_PATH" gateway > "$HOME/.nanobot/gateway.log" 2>&1 &
        sleep 2
        if pgrep -f 'nanobot gateway' > /dev/null; then
            echo "✓ Gateway restarted successfully"
        else
            echo "⚠ Gateway restart may have failed"
            echo "  Please check: tail -f ~/.nanobot/gateway.log"
        fi
    fi
else
    echo "⚠ nanobot not found in PATH"
    echo "  Please restart gateway manually"
fi

echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo ""
echo "1. Configure SDF credentials:"
echo "   Say: 'Set SDF username to YOUR_USERNAME'"
echo "   Say: 'Set SDF password to YOUR_PASSWORD'"
echo ""
echo "2. Test connection:"
echo "   Say: 'Connect to SDF'"
echo ""
echo "3. Send message to COM:"
echo "   Say: 'com: Hello everyone!'"
echo ""
echo "Documentation: https://github.com/YKaiXu/sdfshell"
echo ""
