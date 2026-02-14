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

### nanobot处理逻辑

```python
# nanobot Agent处理逻辑
def route_message(message: str) -> str:
    """消息路由"""
    
    # 检测com:前缀 - 发送到COM聊天室
    if message.startswith("com:"):
        content = message[4:].strip()
        # 调用LLM翻译为英文
        translated = llm_translate(content, target="en")
        # 发送到COM
        return com_send(translated)
    
    # 检测sh:前缀 - 执行SSH命令
    elif message.startswith("sh:"):
        command = message[3:].strip()
        return ssh_exec(command)
    
    # 无前缀 - 正常对话
    else:
        return "正常对话模式"
```

## 安装

```bash
pip install sdfshell
# 或
pip install paramiko-expect pyte
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
    queue_type: nanobot  # memory / redis / nanobot
    reconnect_attempts: 3
```

## 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `ssh_connect` | 连接SSH服务器 | host, username, password, port |
| `com_login` | 登录COM聊天室 | 无 |
| `com_send` | 发送消息 | message |
| `com_read` | 读取消息 | count |
| `com_logout` | 退出COM | 无 |
| `ssh_disconnect` | 断开SSH | 无 |
| `ssh_exec` | 执行SSH命令 | command |

## SDF.org COM命令参考

nanobot需要知悉以下COM命令，以便正确操作：

### 进入/退出命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `com` | 进入COM聊天室 | 在SSH终端输入 |
| `/q` | 退出COM | 返回Shell |
| `/quit` | 退出COM | 同/q |

### 用户管理命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/w` | 查看在线用户 | 显示所有在线用户 |
| `/i username` | 忽略用户 | `/i spammer` |
| `/u` | 取消忽略 | `/u spammer` |

### 消息命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/m username` | 私聊用户 | `/m john Hello` |
| `/r` | 回复最后私聊 | `/r Hello back` |
| `/me action` | 发送动作 | `/me waves` |

### 信息命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `/h` | 帮助 | 显示帮助信息 |
| `/t` | 时间 | 显示服务器时间 |
| `直接输入文字` | 发送消息 | 发送到公共聊天室 |

### nanobot操作指南

当用户请求以下操作时，nanobot应调用对应工具：

| 用户请求 | 调用工具 | 示例 |
|----------|----------|------|
| 连接到SDF | `ssh_connect` | `ssh_connect("sdf.org", "user", "pass")` |
| 进入聊天室 | `com_login` | `com_login()` |
| 发送消息 | `com_send` | `com_send("Hello")` |
| 读取消息 | `com_read` | `com_read(10)` |
| 查看用户 | `com_send` | `com_send("/w")` |
| 退出聊天 | `com_logout` | `com_logout()` |
| 断开连接 | `ssh_disconnect` | `ssh_disconnect()` |

## 使用示例

```
用户: com: 大家好
助手: [检测到com:前缀，翻译为英文并发送]
已发送: Hello everyone!

用户: sh: whoami
助手: [检测到sh:前缀，执行SSH命令]
yupeng

用户: 你好
助手: [无前缀，正常对话]
你好！有什么可以帮助你的？

用户: 连接到sdf.org
助手: [调用 ssh_connect(host="sdf.org", username="user", password="pass")]
已连接到sdf.org

用户: 登录COM
助手: [调用 com_login()]
已登录COM聊天室
```

## 注意事项

1. 需要Python 3.10+
2. 需要SDF.org账号
3. 消息会自动过滤ANSI控制字符
4. 系统消息会被过滤，只显示用户聊天内容
5. `com:`前缀的消息会自动翻译为英文后发送
