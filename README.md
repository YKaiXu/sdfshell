# SDFShell - SDF.org COM Chat Channel for nanobot

SDF.org COM聊天室的nanobot通道，实现双向消息传递。

## 核心技术

| 组件 | 技术 | 作用 |
|------|------|------|
| SSH连接 | paramiko-expect | 交互式SSH会话，自动密码输入 |
| 终端解析 | pyte | 解析ncurses输出，提取聊天消息 |
| 消息队列 | nanobot.bus.Queue | 可靠的消息传递机制 |

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    nanobot Agent                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ FeishuChannel│  │SDFShellChannel│  │ OtherChannel │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘      │
│         │                 │                                 │
│         ▼                 ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              nanobot.bus.Queue                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Agent + LLM (消息处理+翻译)               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   SDFShell Channel                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ SSHSession  │  │ COMSession  │  │ TerminalEmu │         │
│  │(paramiko-   │  │             │  │ (pyte)      │         │
│  │ expect)     │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 消息流向

```
【COM → 飞书】
COM聊天室 → pyte解析 → Queue → Agent(LLM翻译) → 飞书

【飞书 → COM】
飞书消息 → Queue → Agent(LLM翻译) → SSH发送 → COM
```

## 安装

```bash
pip install sdfshell
```

## 配置

在nanobot的`config.yaml`中添加：

```yaml
channels:
  sdfshell:
    enabled: true
    host: sdf.org
    port: 22
    username: your_username
    password: your_password
    monitor_interval: 3.0
```

## SDF.org COM命令参考

| 命令 | 功能 | 示例 |
|------|------|------|
| `com` | 进入COM聊天室 | 直接输入 `com` |
| `/q` | 退出COM | `/q` |
| `/w` | 查看在线用户 | `/w` |
| `/h` | 帮助 | `/h` |
| `/i username` | 忽略用户 | `/i spammer` |
| `/m username` | 私聊 | `/m john` |
| 直接输入 | 发送消息 | `Hello everyone!` |

## 使用示例

```
用户: 连接到sdf.org
助手: [调用 ssh_connect(host="sdf.org", username="user", password="pass")]
已连接到sdf.org

用户: 登录COM
助手: [调用 com_login()]
已登录COM聊天室

用户: 发送消息"Hello"
助手: [调用 com_send(message="Hello")]
消息已发送

用户: 读取消息
助手: [调用 com_read(count=10)]
最新消息:
- user1: Hi
- user2: Hello

用户: 退出
助手: [调用 com_logout() 和 ssh_disconnect()]
已退出
```

## 依赖

- Python >= 3.10
- paramiko >= 3.0.0
- paramiko-expect >= 0.3.5
- pyte >= 0.8.0
- nanobot >= 0.1.0 (可选)

## 许可证

MIT License

## 作者

YKaiXu (yukaixu@outlook.com)
