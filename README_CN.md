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

添加到 `~/.nanobot/config.yaml`：

```yaml
channels:
  sdfshell:
    enabled: true
    host: sdf.org
    port: 22
    username: your_username
    password: your_password
    monitor_interval: 3.0
    queue_type: nanobot
    reconnect_attempts: 3
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

- Python 3.10+
- paramiko >= 3.0.0
- paramiko-expect >= 0.3.5
- pyte >= 0.8.0
- SDF.org账号

## 作者

**YUKAIXU**
- 坐标: 中国湖北
- 邮箱: yukaixu@outlook.com
- GitHub: https://github.com/YKaiXu

## 许可证

MIT License
