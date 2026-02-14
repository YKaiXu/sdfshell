#!/usr/bin/env bash
# SDFShell One-Click Installation Script
# Auto-creates virtual environment, installs dependencies, and configures nanobot

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

# Set installation directories
# NOTE: nanobot loads skills from both locations:
# 1. workspace/skills/ (SkillsLoader)
# 2. ~/.nanobot/skills/ (some commands check here)
# We install to workspace/skills/ and create symlink
WORKSPACE_DIR="${HOME}/.nanobot/workspace"
SKILL_DIR="${WORKSPACE_DIR}/skills/sdfshell"
VENV_DIR="${SKILL_DIR}/venv"
LOG_DIR="${HOME}/.nanobot/logs"

# Create directories
echo "Creating directories..."
mkdir -p "${WORKSPACE_DIR}/skills"
mkdir -p "${HOME}/.nanobot/skills"
mkdir -p "$LOG_DIR"

# Clone or update repository
if [ -d "$SKILL_DIR" ]; then
    echo "Removing old installation..."
    rm -rf "$SKILL_DIR"
fi

echo "Cloning repository..."
git clone https://github.com/YKaiXu/sdfshell.git "$SKILL_DIR"
cd "$SKILL_DIR"

# Verify clone
if [ ! -f "sdfshell.py" ]; then
    echo "Error: Clone failed - sdfshell.py not found"
    exit 1
fi

if [ ! -f "SKILL.md" ]; then
    echo "Error: Clone failed - SKILL.md not found"
    exit 1
fi

echo "✓ Repository cloned successfully"

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

# Deactivate
deactivate

echo ""
echo "========================================"
echo "✅ Installation Complete"
echo "========================================"
echo ""
echo "Skill installed to: $SKILL_DIR"
echo "Virtual environment: $VENV_DIR"
echo "Log directory: $LOG_DIR"
echo ""

# Verify installation
echo "Verifying installation..."
if [ -f "$SKILL_DIR/sdfshell.py" ]; then
    LINES=$(wc -l < "$SKILL_DIR/sdfshell.py")
    echo "✓ sdfshell.py ($LINES lines)"
else
    echo "✗ sdfshell.py not found"
fi

if [ -f "$SKILL_DIR/SKILL.md" ]; then
    SIZE=$(wc -c < "$SKILL_DIR/SKILL.md")
    echo "✓ SKILL.md ($SIZE bytes)"
else
    echo "✗ SKILL.md not found"
fi

if [ -f "$SKILL_DIR/__init__.py" ]; then
    echo "✓ __init__.py"
else
    echo "✗ __init__.py not found"
fi

if [ -f "$VENV_DIR/bin/python" ]; then
    echo "✓ Virtual environment"
else
    echo "✗ Virtual environment not found"
fi

# Create symlink for nanobot to find the skill
echo ""
echo "Creating symlink..."
ln -sf "$SKILL_DIR" "${HOME}/.nanobot/skills/sdfshell"
if [ -L "${HOME}/.nanobot/skills/sdfshell" ]; then
    echo "✓ Symlink created: ~/.nanobot/skills/sdfshell -> $SKILL_DIR"
else
    echo "⚠ Symlink creation failed"
fi

# Update nanobot config
echo ""
echo "========================================"
echo "Configuring nanobot"
echo "========================================"

if [ -f "$CONFIG_FILE" ]; then
    echo "Updating config.json..."
    
    # Use Python to update JSON config
    $PYTHON << 'PYEOF'
import json
import os

config_file = os.path.expanduser("~/.nanobot/config.json")

try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except:
    config = {}

# Ensure channels section exists
if 'channels' not in config:
    config['channels'] = {}

# Add sdfshell channel config
config['channels']['sdfshell'] = {
    'enabled': True,
    'host': 'sdf.org',
    'port': 22,
    'username': '',
    'password': '',
    'monitor_interval': 3.0,
    'queue_type': 'nanobot',
    'reconnect_attempts': 3
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("✓ Config updated: sdfshell channel added")
print(f"  Channels: {list(config['channels'].keys())}")
PYEOF

else
    echo "⚠ Config file not found at $CONFIG_FILE"
    echo "  Please configure manually after nanobot setup"
fi

# Restart nanobot gateway (no sudo required)
echo ""
echo "========================================"
echo "Restarting nanobot gateway"
echo "========================================"

# Check if nanobot is installed
NANOBOT_PATH="$HOME/.local/bin/nanobot"
if [ ! -f "$NANOBOT_PATH" ]; then
    NANOBOT_PATH=$(which nanobot 2>/dev/null || echo "")
fi

if [ -n "$NANOBOT_PATH" ]; then
    # Kill existing gateway processes
    echo "Stopping existing gateway..."
    pkill -f 'nanobot gateway' 2>/dev/null || true
    sleep 2
    
    # Start new gateway
    echo "Starting gateway..."
    nohup "$NANOBOT_PATH" gateway > "$HOME/.nanobot/gateway.log" 2>&1 &
    sleep 3
    
    # Verify
    if pgrep -f 'nanobot gateway' > /dev/null; then
        echo "✓ Gateway started successfully"
        echo "  PID: $(pgrep -f 'nanobot gateway')"
    else
        echo "⚠ Gateway may have failed to start"
        echo "  Check log: tail -f ~/.nanobot/gateway.log"
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
echo "Logs: $LOG_DIR/sdfshell.log"
echo ""
