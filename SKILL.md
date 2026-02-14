# SDFShell - SDF.org COM Chat Channel for nanobot

SDF.org COM聊天室的nanobot通道，实现双向消息传递。

## 核心技术

| 组件 | 技术 | 作用 |
|------|------|------|
| SSH连接 | paramiko-expect | 交互式SSH会话，自动密码输入 |
| 终端解析 | pyte | 解析ncurses输出，提取聊天消息 |
| 消息队列 | nanobot.bus.Queue | 可靠的消息传递机制 |

## 消息路由规则

### 从飞书发送消息

nanobot需要根据消息前缀判断如何处理：

| 前缀 | 功能 | 示例 |
|------|------|------|
| `com:` | 向COM聊天室发送消息 | `com: Hello everyone!` |
| `sh:` | 执行SSH命令 | `sh: ls -la` |
| 无前缀 | 普通对话，不发送到COM | `你好` |

### 消息流向

```
【COM → 飞书】
COM聊天室 → pyte解析 → Queue → Agent(LLM翻译) → 飞书

【飞书 → COM】
飞书消息 → 检测前缀 → 
  - "com:" → 翻译为英文 → SSH发送 → COM聊天室
  - "sh:" → 执行SSH命令 → 返回结果
  - 无前缀 → 正常对话
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
    queue_type: nanobot
    reconnect_attempts: 3
```

## COM聊天室完整命令参考

**重要：COM有两种模式 - 命令模式和输入模式**

### 模式切换

| 操作 | 说明 |
|------|------|
| 默认进入命令模式 | 启动COM后默认为命令模式 |
| 输入空格 | 进入输入模式（发送消息） |
| 发送消息后 | 自动返回命令模式 |

### 命令模式命令

#### 房间管理

| 命令 | 功能 | 示例 |
|------|------|------|
| `l` | 列出所有房间 | 显示房间名、人数、主题 |
| `g` | 进入房间（goto） | `g spacebar` |
| `w` | 查看当前房间用户 | 显示用户列表 |
| `q` | 退出COM | 显示"Unlinking TTY..." |

#### 消息历史

| 命令 | 功能 | 说明 |
|------|------|------|
| `r` | 查看最近18行历史 | 快速回顾 |
| `R` | 查看指定行数历史 | 输入行数后回车 |

### 输入模式

| 操作 | 说明 |
|------|------|
| 输入空格 | 进入输入模式，显示用户名提示符 |
| 输入消息 + 回车 | 发送消息到当前房间 |
| 消息格式 | `[username] 你的消息` |

### 默认房间

| 房间 | 说明 |
|------|------|
| `lobby` | 默认进入的欢迎房间 |
| `spacebar` | 活跃的聊天房间 |
| `anonradio` | 电台相关房间 |

## nanobot操作指南

当用户请求以下操作时，nanobot应调用对应工具：

| 用户请求 | 调用工具 | 示例 |
|----------|----------|------|
| 连接到SDF | `ssh_connect` | `ssh_connect("sdf.org", "user", "pass")` |
| 进入聊天室 | `com_login` | `com_login()` |
| 发送消息 | `com_send` | `com_send(" Hello")`（空格开头进入输入模式） |
| 读取消息 | `com_read` | `com_read(10)` |
| 查看用户 | `com_send` | `com_send("w")` |
| 列出房间 | `com_send` | `com_send("l")` |
| 进入房间 | `com_send` | `com_send("g spacebar")` |
| 查看历史 | `com_send` | `com_send("r")` |
| 退出聊天 | `com_logout` | `com_logout()` |
| 断开连接 | `ssh_disconnect` | `ssh_disconnect()` |

## 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `ssh_connect` | 连接SSH服务器 | host, username, password, port |
| `com_login` | 登录COM聊天室 | 无 |
| `com_send` | 发送命令/消息 | message |
| `com_read` | 读取消息 | count |
| `com_logout` | 退出COM | 无 |
| `ssh_disconnect` | 断开SSH | 无 |

## 使用示例

```
用户: 连接到sdf.org，用户名user，密码pass
助手: [调用 ssh_connect(host="sdf.org", username="user", password="pass")]
已连接到sdf.org

用户: 进入聊天室
助手: [调用 com_login()]
已登录COM聊天室，当前在lobby房间

用户: 列出房间
助手: [调用 com_send("l")]
房间列表:
- spacebar (16人): there is life out there
- lobby (1人): SDF's Welcoming Room

用户: 进入spacebar房间
助手: [调用 com_send("g spacebar")]
已进入spacebar房间

用户: com: 大家好
助手: [检测到com:前缀，翻译为英文并发送]
已发送: Hello everyone!

用户: 查看用户
助手: [调用 com_send("w")]
当前房间用户:
- user1@iceland
- user2@sverige

用户: 退出
助手: [调用 com_logout() 和 ssh_disconnect()]
已退出
```

## 注意事项

1. 需要Python 3.10+
2. 需要SDF.org账号
3. COM命令模式下无提示符，只有光标
4. 发送消息需先输入空格进入输入模式
5. 消息会自动过滤ANSI控制字符
6. 默认使用nanobot消息队列，无需额外部署
