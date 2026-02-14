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

---

## SDF Shell命令参考（用于"sh:"前缀）

当用户使用"sh:"前缀时，nanobot需要将自然语言翻译为正确的SDF命令。

### 信息查询命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 查看帮助/命令列表 | `help` 或 `commands` | 显示基本Unix命令 |
| 查看会员信息 | `arpa` | ARPA会员信息 |
| 查看MetaARPA信息 | `meta` | MetaARPA会员信息 |
| 查看DBA信息 | `dba` | 数据库会员信息 |
| 查看会员类型 | `how` | 会员类型概览 |
| 查看软件列表 | `software` | 各会员级别可用软件 |
| 查看FAQ | `faq` | 交互式FAQ浏览 |
| 查看编辑器列表 | `editors` | 可用文本编辑器 |
| 查看游戏列表 | `games` | 安装的游戏 |
| 查看最大用户数 | `maxusers` | 同时在线用户记录 |
| 查看停机原因 | `downtime` | 最近服务器停机原因 |

### 账户管理命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 修改密码/信息 | `maint` | 修改密码、shell、联系信息 |
| 查看磁盘使用 | `disk` | 显示home/mail/gopher/web空间使用 |
| 查看账户到期 | `expire` | 显示账户到期时间 |
| 查看会员费 | `dues` | 会员费详情 |
| 设置退格键 | `bksp` | 设置退格键 |
| 查看可用域名 | `domains` | 可用于webhosting的域名 |

### 社交通信命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 进入聊天室 | `com` | COM聊天系统 |
| 查看公告板 | `bboard` | SDF公告板系统 |
| 发送消息给用户 | `mesg` | 发送消息给其他用户 |
| 留言给用户 | `notes` | 给其他用户留言 |
| 查看用户信息 | `uinfo` | 用户加入日期和会员级别 |
| 查看用户网站 | `url 用户名` | 显示用户网站URL |
| 设置个人资料 | `profiles` | 设置个人资料 |
| 签名/查看留言板 | `guestbook` | SDF留言板 |
| 查看在线时间 | `online` | 用户今日在线时间 |
| 提交日志 | `happening` | 匿名日志条目 |

### 网站和Gopher命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 创建网站 | `mkhomepg` | 设置SDF网站 |
| 创建Gopher空间 | `mkgopher` | 设置Gopherspace |
| 发布网站 | `addlink` | 发布网站链接 |

### 数据库命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 设置MySQL | `startsql` | 创建MySQL数据库(DBA会员) |
| 修改MySQL密码 | `mypassword` | 修改MySQL密码 |
| 重置MySQL密码 | `reset-mysql` | 重置MySQL密码 |

### VPN和VPS命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 查看VPN信息 | `vpn` | VPN会员信息 |
| 配置VPN | `setvpn` | 配置PPTP VPN登录 |
| 查看VPN统计 | `vpnstats` | VPN使用统计 |

### 其他实用命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 缩短URL | `surl` | SDF URL缩短服务 |
| 上传文件 | `upload` | 上传文件(rz包装) |
| 查看随机名言 | `smj` | SDF管理员名言 |
| 查看股票价格 | `quote 股票代码` | 股票价格(可能不可用) |
| 捐款信息 | `address` | SDF地址和PayPal信息 |
| 查看Twenex软件 | `twenex` | /sys/sdf/bin软件摘要 |

### 常用Unix命令

| 用户可能说 | 正确命令 | 说明 |
|------------|----------|------|
| 列出文件 | `ls` 或 `ls -la` | 列出目录内容 |
| 查看当前目录 | `pwd` | 显示当前目录 |
| 切换目录 | `cd 目录名` | 切换目录 |
| 查看文件内容 | `cat 文件名` | 显示文件内容 |
| 查看文件(分页) | `more 文件名` 或 `less 文件名` | 分页查看 |
| 编辑文件 | `pico 文件名` 或 `vi 文件名` | 编辑文件 |
| 创建目录 | `mkdir 目录名` | 创建目录 |
| 删除文件 | `rm 文件名` | 删除文件 |
| 删除目录 | `rmdir 目录名` | 删除空目录 |
| 复制文件 | `cp 源 目标` | 复制文件 |
| 移动/重命名 | `mv 源 目标` | 移动或重命名 |
| 查找文件 | `find . -name "文件名"` | 查找文件 |
| 查看进程 | `ps` 或 `ps aux` | 显示进程 |
| 查看磁盘空间 | `df -h` | 磁盘空间 |
| 查看谁在线 | `who` 或 `w` | 在线用户 |

---

## nanobot操作指南

当用户请求以下操作时，nanobot应调用对应工具：

### COM聊天操作

| 用户请求 | 调用工具 | 示例 |
|----------|----------|------|
| 连接到SDF | `ssh_connect` | `ssh_connect("sdf.org", "user", "pass")` |
| 进入聊天室 | `com_login` | `com_login()` |
| 发送消息 | `com_send` | `com_send(" Hello")`（空格开头） |
| 读取消息 | `com_read` | `com_read(10)` |
| 查看用户 | `com_send` | `com_send("w")` |
| 列出房间 | `com_send` | `com_send("l")` |
| 进入房间 | `com_send` | `com_send("g spacebar")` |
| 查看历史 | `com_send` | `com_send("r")` |
| 退出聊天 | `com_logout` | `com_logout()` |
| 断开连接 | `ssh_disconnect` | `ssh_disconnect()` |

### SSH命令操作（sh:前缀）

| 用户请求 | 调用工具 | 示例 |
|----------|----------|------|
| 查看帮助 | `com_send` | `com_send("help")` |
| 查看磁盘 | `com_send` | `com_send("disk")` |
| 查看会员信息 | `com_send` | `com_send("arpa")` |
| 查看公告板 | `com_send` | `com_send("bboard")` |
| 修改密码 | `com_send` | `com_send("maint")` |
| 执行Unix命令 | `com_send` | `com_send("ls -la")` |

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

用户: sh: 查看磁盘使用
助手: [检测到sh:前缀，翻译为命令]
[调用 com_send("disk")]
Filesystem     Size  Used Avail Use%
/home/user      10G   2G   8G   20%

用户: sh: 列出文件
助手: [调用 com_send("ls -la")]
total 64
drwxr-xr-x  5 user user 4096 Jan 1 00:00 .
drwxr-xr-x  3 root root 4096 Jan 1 00:00 ..

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
7. "sh:"前缀用于执行SDF命令，nanobot需将自然语言翻译为正确命令
