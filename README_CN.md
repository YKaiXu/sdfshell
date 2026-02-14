# SDFShell - SDF.org COM聊天室 nanobot 通道

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

SDF.org COM聊天室的nanobot通道，支持双向消息传递和自动翻译。

## 功能特性

- **paramiko-expect** - 交互式SSH会话，自动密码输入
- **pyte** - 终端模拟器，解析ncurses输出
- **nanobot Queue** - 可靠的消息传递机制
- **自动重连** - SSH断开后自动重连
- **双向翻译** - 消息自动翻译
- **多平台支持** - 支持飞书、微信、Telegram、Discord、Slack等

## 多平台支持

SDFShell 支持**所有** nanobot 连接的聊天平台：

| 平台 | 支持 | 平台 | 支持 |
|------|------|------|------|
| 飞书 | ✅ | 微信 | ✅ |
| Telegram | ✅ | Discord | ✅ |
| Slack | ✅ | 其他平台 | ✅ |

**任何平台的用户都可以：**
- 发送消息到 SDF.org COM 聊天室
- 接收 COM 消息（自动翻译）
- 执行 SDF shell 命令

## 一键安装

**复制此指令发送给nanobot：**

```
请在bash执行: curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash
```

执行后nanobot将：
- ✅ 自动安装SDFShell（含虚拟环境）
- ✅ 掌握所有`com:`和`sh:`前缀规则
- ✅ 熟练使用所有COM聊天室命令
- ✅ 熟练使用所有SDF shell命令
- ✅ 支持双向自动翻译

或手动执行：

```bash
curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash
```

## 消息路由

| 前缀 | 用途 | 说明 |
|------|------|------|
| `com:` | 发送聊天消息 | 自动翻译为英文，发送到COM |
| `sh:` | 执行命令 | 执行SSH/SDF命令（不翻译） |
| 无前缀 | 普通对话 | 与nanobot聊天 |

## 配置

添加到 `~/.nanobot/config.json`：

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

## COM命令

| 命令 | 功能 |
|------|------|
| `l` | 列出房间 |
| `g room` | 进入房间 |
| `w` | 查看在线用户 |
| `r` | 查看历史 |
| `q` | 退出COM |
| `空格 + 消息` | 发送消息 |

## 工具列表

| 工具 | 描述 |
|------|------|
| `ssh_connect` | 连接SSH服务器 |
| `com_login` | 登录COM聊天室 |
| `com_send` | 发送命令/消息 |
| `com_read` | 读取消息 |
| `com_logout` | 退出COM |
| `ssh_disconnect` | 断开SSH |

## 使用示例

```
用户: 连接到sdf.org，用户名user，密码pass
助手: [ssh_connect("sdf.org", "user", "pass")]
已连接到sdf.org

用户: com: 大家好
助手: [翻译并发送]
已发送: Hello everyone!

用户: sh: 查看磁盘使用
助手: [com_send("disk")]
Filesystem     Size  Used Avail Use%
/home/user      10G   2G   8G   20%
```

## 系统要求

### 基础依赖

- Python 3.10+
- Git
- pip (Python包管理器)
- SDF.org账号

### 安装系统依赖

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
# 使用Homebrew
brew install python@3.10 git
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip python-virtualenv git
```

### Python依赖

以下依赖由安装脚本自动安装：
- paramiko >= 3.0.0
- paramiko-expect >= 0.3.5
- pyte >= 0.8.0

### 验证安装

```bash
# 检查Python版本（需要3.10+）
python3 --version

# 检查pip
pip3 --version

# 检查git
git --version

# 检查venv模块
python3 -m venv --help
```

## 作者

**YUKAIXU**
- 坐标: 中国湖北
- 邮箱: yukaixu@outlook.com
- GitHub: https://github.com/YKaiXu

## 许可证

MIT License
