# SDFShell - SDF.org COM Chat Channel for nanobot

SDF.org COM聊天室的nanobot通道，实现双向消息传递。

## 核心技术

| 组件 | 技术 | 作用 |
|------|------|------|
| SSH连接 | paramiko-expect | 交互式SSH会话，自动密码输入 |
| 终端解析 | pyte | 解析ncurses输出，提取聊天消息 |
| 消息队列 | nanobot.bus.Queue | 可靠的消息传递机制 |

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
```

## 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| ssh_connect | 连接SSH服务器 | host, username, password, port |
| com_login | 登录COM聊天室 | 无 |
| com_send | 发送消息 | message |
| com_read | 读取消息 | count |
| com_logout | 退出COM | 无 |
| ssh_disconnect | 断开SSH | 无 |

## 消息流向

```
【COM → 飞书】
COM聊天室 → pyte解析 → Queue → Agent(LLM翻译) → 飞书

【飞书 → COM】
飞书消息 → Queue → Agent(LLM翻译) → SSH发送 → COM
```

## SDF.org COM命令

| 命令 | 功能 |
|------|------|
| `com` | 进入COM聊天室 |
| `/q` | 退出COM |
| `/w` | 查看在线用户 |
| `/h` | 帮助 |
| `/i` | 忽略用户 |
| `/m` | 私聊 |

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

## 注意事项

1. 需要Python 3.10+
2. 需要SDF.org账号
3. 消息会自动过滤ANSI控制字符
4. 系统消息会被过滤，只显示用户聊天内容
