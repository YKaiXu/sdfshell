# Nanobot Skill Development Guide

This document records important notes and best practices for developing skills for nanobot.

## Table of Contents

1. [Skills vs Channels](#skills-vs-channels)
2. [Installation Directory](#installation-directory)
3. [Required Files](#required-files)
4. [Configuration](#configuration)
5. [Message Queue Integration](#message-queue-integration)
6. [Common Pitfalls](#common-pitfalls)
7. [Best Practices](#best-practices)

---

## Skills vs Channels

### Skills
- **Definition**: Skills are extension modules placed in `~/.nanobot/workspace/skills/`
- **Purpose**: Extend nanobot's capabilities with tools and functionality
- **Components**: 
  - `SKILL.md` - Documentation that teaches nanobot how to use the skill
  - `__init__.py` - Python module exports
  - Implementation files (`.py`)
  - `venv/` - Virtual environment (recommended)

### Channels
- **Definition**: Channels are message interfaces for external systems
- **Purpose**: Handle message passing between nanobot and external platforms
- **Built-in**: Feishu (飞书) is built-in and connects directly via WebSocket
- **Custom**: Skills can provide custom Channel classes

### Key Distinction
- **Feishu connection**: Handled directly by nanobot via WebSocket, NOT by skills
- **Skills**: Provide tools and optional Channel classes for other services
- **Message flow**: External platform → nanobot Channel → Agent → Tools → Response

---

## Installation Directory

### CRITICAL: Correct Installation Path

```
WRONG: ~/.nanobot/skills/sdfshell/
RIGHT: ~/.nanobot/workspace/skills/sdfshell/
```

nanobot's `SkillsLoader` looks for skills in:
1. `workspace/skills/` (highest priority)
2. `builtin_skills/` (built-in skills)

### Directory Structure

```
~/.nanobot/workspace/skills/
└── your_skill/
    ├── SKILL.md          # REQUIRED: Skill documentation
    ├── __init__.py       # REQUIRED: Module exports
    ├── main.py           # Implementation
    ├── requirements.txt  # Dependencies
    ├── pyproject.toml    # Package config
    └── venv/             # Virtual environment
```

---

## Required Files

### 1. SKILL.md

The `SKILL.md` file teaches nanobot how to use the skill. It should include:

```markdown
# Skill Name - Brief Description

## Core Technologies
| Component | Technology | Function |
|-----------|------------|----------|
| ... | ... | ... |

## Tools Available
List all tools and their usage.

## Usage Examples
Provide clear examples for nanobot to learn from.
```

### 2. __init__.py

Must export all tools and the Channel class (if any):

```python
from .main import (
    YourChannel,
    tool_function_1,
    tool_function_2,
    TOOLS,
    HAS_NANOBOT,
)

__all__ = [
    "YourChannel",
    "tool_function_1",
    "tool_function_2",
    "TOOLS",
    "HAS_NANOBOT",
]

__version__ = "1.0.0"
```

### 3. TOOLS Definition

Define tools in OpenAI function format:

```python
TOOLS = [
    {
        "name": "tool_name",
        "description": "Tool description",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"},
            },
            "required": ["param1"]
        }
    }
]
```

---

## Configuration

### Main Config File

Location: `~/.nanobot/config.json` (JSON format, NOT YAML!)

```json
{
  "providers": { ... },
  "agents": { ... },
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "...",
      "appSecret": "..."
    },
    "your_skill": {
      "enabled": true,
      "host": "example.com",
      "port": 22,
      "username": "",
      "password": ""
    }
  }
}
```

### Skill-Level Config

Location: `~/.nanobot/workspace/skills/your_skill/config.json`

```python
CONFIG_FILE = os.path.expanduser("~/.nanobot/workspace/skills/your_skill/config.json")

def load_config() -> dict:
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}
```

### Config Priority

```
config.json parameter > saved config > environment variable > default value
```

---

## Message Queue Integration

### How Skills Connect to nanobot

Skills do NOT connect to nanobot via API. Instead, they use:

1. **nanobot's Message Queue**: `nanobot.bus.queue.Queue`
2. **BaseChannel Interface**: Inherit from `nanobot.channels.base.BaseChannel`

### BaseChannel Implementation

```python
try:
    from nanobot.channels.base import BaseChannel
    from nanobot.bus.queue import Queue as NanobotQueue
    from nanobot.bus.events import Event
    HAS_NANOBOT = True
except ImportError:
    HAS_NANOBOT = False
    class BaseChannel:
        def __init__(self, config: dict): self.config = config
        async def start(self): pass
        async def stop(self): pass
        async def send(self, message: dict): pass
```

### Required Methods

```python
class YourChannel(BaseChannel):
    def __init__(self, config: dict):
        super().__init__(config)
        # Initialize with config
    
    async def start(self) -> None:
        # Start the channel
        pass
    
    async def stop(self) -> None:
        # Stop the channel
        pass
    
    async def send(self, message: dict) -> None:
        # Send message to external system
        pass
    
    async def receive(self) -> AsyncGenerator[dict, None]:
        # Receive messages (optional)
        pass
```

### Message Flow

```
External System (e.g., SDF.org)
        │
        ▼
   YourChannel
        │
        ▼
  nanobot Queue
        │
        ▼
  nanobot Agent
        │
        ▼
   Tool Functions
        │
        ▼
    Response
        │
        ▼
  Feishu Channel (built-in)
        │
        ▼
    Feishu App
```

---

## Common Pitfalls

### 1. Wrong Installation Directory

```
❌ ~/.nanobot/skills/
✅ ~/.nanobot/workspace/skills/
```

### 2. Config File Format

```
❌ YAML format (config.yaml)
✅ JSON format (config.json)
```

### 3. Using sudo in Install Script

```
❌ sudo systemctl restart nanobot  # Requires password
✅ pkill -f 'nanobot gateway' && nohup nanobot gateway &
```

### 4. Empty SKILL.md

Always verify clone was successful:
```bash
if [ ! -f "SKILL.md" ]; then
    echo "Error: Clone failed - SKILL.md not found"
    exit 1
fi
```

### 5. Missing __init__.py Exports

Ensure all tools are exported:
```python
__all__ = ["YourChannel", "TOOLS", "tool_function_1", ...]
```

---

## Best Practices

### 1. Installation Script

Include in install.sh:
- Python version check
- Directory creation
- Clone verification
- Virtual environment setup
- Config file update
- Gateway restart

### 2. Logging

Use consistent log location:
```python
DEFAULT_LOG_FILE = os.path.expanduser("~/.nanobot/logs/your_skill.log")
```

### 3. Dependency Check

```python
try:
    import required_package
    HAS_PACKAGE = True
except ImportError:
    HAS_PACKAGE = False
```

### 4. Graceful Fallback

```python
if not HAS_NANOBOT:
    # Provide fallback implementation
    pass
```

### 5. Configuration via Conversation

Allow users to configure through natural language:
```python
def set_config(host: str = None, username: str = None, password: str = None):
    """Set configuration via conversation"""
    config = load_config()
    if host: config["host"] = host
    if username: config["username"] = username
    if password: config["password"] = password
    save_config(config)
```

### 6. Welcome Message

Provide a welcome message after installation:
```python
def get_welcome_message() -> str:
    return """🎉 Skill installed!

Here's how to use:
1. Configure: 'Set username to YOUR_NAME'
2. Connect: 'Connect to service'
3. Use: 'Send message to ...'
"""
```

---

## File Locations Summary

| File | Location |
|------|----------|
| Skills directory | `~/.nanobot/workspace/skills/` |
| Main config | `~/.nanobot/config.json` |
| Skill config | `~/.nanobot/workspace/skills/<skill>/config.json` |
| Logs | `~/.nanobot/logs/` |
| Gateway log | `~/.nanobot/gateway.log` |
| Workspace | `~/.nanobot/workspace/` |

---

## Debugging

### Check if skill is loaded

```bash
# Check skills directory
ls -la ~/.nanobot/workspace/skills/

# Check SKILL.md content
head -20 ~/.nanobot/workspace/skills/your_skill/SKILL.md

# Check gateway log
tail -f ~/.nanobot/gateway.log

# Test import
cd ~/.nanobot/workspace/skills/your_skill
source venv/bin/activate
python -c "from your_skill import TOOLS; print(len(TOOLS))"
```

### Restart gateway

```bash
pkill -f 'nanobot gateway'
nohup ~/.local/bin/nanobot gateway > ~/.nanobot/gateway.log 2>&1 &
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-02-15 | Initial documentation |

---

## References

- [nanobot GitHub](https://github.com/nanobot-ai/nanobot)
- [SDFShell Example](https://github.com/YKaiXu/sdfshell)
