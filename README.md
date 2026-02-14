# SDFShell - SDF.org COM Chat Channel for nanobot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

SDF.org COM chat room nanobot channel for bidirectional message passing with auto-translation support.

## Features

- **paramiko-expect** - Interactive SSH session with auto password input
- **pyte** - Terminal emulator for parsing ncurses output
- **nanobot Queue** - Reliable message passing mechanism
- **Auto-reconnect** - Automatic SSH reconnection on disconnect
- **Bidirectional Translation** - Auto-translate messages between languages
- **Multi-Platform Support** - Works with Feishu, WeChat, Telegram, Discord, Slack, etc.

## Multi-Platform Support

SDFShell works with **ALL** nanobot-connected chat platforms:

| Platform | Support | Platform | Support |
|----------|---------|----------|---------|
| Feishu (飞书) | ✅ | WeChat (微信) | ✅ |
| Telegram | ✅ | Discord | ✅ |
| Slack | ✅ | Any other | ✅ |

**Any user from any platform can:**
- Send messages to SDF.org COM chat room
- Receive COM messages (with auto-translation)
- Execute SDF shell commands

## One-Click Install

**Copy this command and send to nanobot:**

```
Execute in bash: curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash
```

After execution, nanobot will:
- ✅ Auto-install SDFShell with virtual environment
- ✅ Learn all `com:` and `sh:` prefix rules
- ✅ Master all COM chat room commands
- ✅ Master all SDF shell commands
- ✅ Support bidirectional auto-translation

Or run manually:

```bash
curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash
```

## Message Routing

| Prefix | Purpose | Description |
|--------|---------|-------------|
| `com:` | Send chat message | Auto-translate to English, send to COM |
| `sh:` | Execute command | Execute SSH/SDF command (no translation) |
| No prefix | Normal chat | Chat with nanobot |

## Configuration

Add to `~/.nanobot/config.json`:

```json
{
  "channels": {
    "sdfshell": {
      "enabled": true,
      "host": "sdf.org",
      "port": 22,
      "username": "your_username",
      "password": "your_password",
      "monitor_interval": 3.0,
      "queue_type": "nanobot",
      "reconnect_attempts": 3
    }
  }
}
```

## COM Commands

| Command | Function |
|---------|----------|
| `l` | List rooms |
| `g room` | Go to room |
| `w` | Who is online |
| `r` | Review history |
| `q` | Quit COM |
| `space + message` | Send message |

## Tools

| Tool | Description |
|------|-------------|
| `ssh_connect` | Connect to SSH server |
| `com_login` | Login to COM chat |
| `com_send` | Send command/message |
| `com_read` | Read messages |
| `com_logout` | Logout from COM |
| `ssh_disconnect` | Disconnect SSH |

## Usage Example

```
User: Connect to sdf.org, username user, password pass
Assistant: [ssh_connect("sdf.org", "user", "pass")]
Connected to sdf.org

User: com: Hello everyone
Assistant: [Translate and send]
Sent: Hello everyone!

User: sh: View disk usage
Assistant: [com_send("disk")]
Filesystem     Size  Used Avail Use%
/home/user      10G   2G   8G   20%
```

## Requirements

### System Requirements

- Python 3.10+
- Git
- pip (Python package manager)
- SDF.org account

### Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3.10 python3-pip python3-venv git
```

**CentOS/RHEL/Fedora:**
```bash
# CentOS/RHEL
sudo yum install -y python3 python3-pip python3-venv git

# Fedora
sudo dnf install -y python3 python3-pip python3-venv git
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.10 git
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip python-virtualenv git
```

### Python Dependencies

These are installed automatically by the install script:
- paramiko >= 3.0.0
- paramiko-expect >= 0.3.5
- pyte >= 0.8.0

### Verify Installation

```bash
# Check Python version (must be 3.10+)
python3 --version

# Check pip
pip3 --version

# Check git
git --version

# Check venv module
python3 -m venv --help
```

## Author

**YUKAIXU**
- Location: Hubei, China
- Email: yukaixu@outlook.com
- GitHub: https://github.com/YKaiXu

## License

MIT License
