# SDFShell - SDF.org COM Chat Channel for nanobot
# SDFShell - SDF.org COM聊天室 nanobot 通道

SDF.org COM chat room nanobot channel for bidirectional message passing.
SDF.org COM聊天室的nanobot通道，实现双向消息传递。

## Core Technologies / 核心技术

| Component 组件 | Technology 技术 | Function 作用 |
|----------------|-----------------|---------------|
| SSH Connection SSH连接 | paramiko-expect | Interactive SSH session, auto password input 交互式SSH会话，自动密码输入 |
| Terminal Parsing 终端解析 | pyte | Parse ncurses output, extract chat messages 解析ncurses输出，提取聊天消息 |
| Message Queue 消息队列 | nanobot.bus.Queue | Reliable message passing mechanism 可靠的消息传递机制 |

## Message Routing Rules / 消息路由规则

### Sending Messages from Feishu / 从飞书发送消息

nanobot needs to determine how to handle messages based on prefix:
nanobot需要根据消息前缀判断如何处理：

| Prefix 前缀 | Function 功能 | Example 示例 |
|-------------|---------------|--------------|
| `com:` | Send message to COM chat room 向COM聊天室发送消息 | `com: Hello everyone!` |
| `sh:` | Execute SSH command 执行SSH命令 | `sh: ls -la` |
| No prefix 无前缀 | Normal conversation, not sent to COM 普通对话，不发送到COM | `你好` |

### Message Flow / 消息流向

```
【COM → Feishu / COM → 飞书】
COM Chat Room 聊天室 → pyte Parse 解析 → Queue 队列 → Agent(LLM Translate 翻译) → Feishu 飞书

【Feishu → COM / 飞书 → COM】
Feishu Message 飞书消息 → Detect Prefix 检测前缀 → 
  - "com:" → Translate to English 翻译为英文 → SSH Send 发送 → COM Chat Room 聊天室
  - "sh:" → Execute SSH Command 执行SSH命令 → Return Result 返回结果
  - No prefix 无前缀 → Normal Conversation 正常对话
```

## Installation / 安装

```bash
pip install sdfshell
```

## Configuration / 配置

Add to nanobot's `config.yaml`:
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

## COM Chat Room Complete Command Reference / COM聊天室完整命令参考

**Important: COM has two modes - Command Mode and Input Mode**
**重要：COM有两种模式 - 命令模式和输入模式**

### Mode Switching / 模式切换

| Operation 操作 | Description 说明 |
|----------------|------------------|
| Default to Command Mode 默认进入命令模式 | Command mode is default after starting COM 启动COM后默认为命令模式 |
| Input Space 输入空格 | Enter Input Mode (send message) 进入输入模式（发送消息） |
| After sending message 发送消息后 | Auto return to Command Mode 自动返回命令模式 |

### Command Mode Commands / 命令模式命令

#### Room Management / 房间管理

| Command 命令 | Function 功能 | Example 示例 |
|--------------|---------------|--------------|
| `l` | List all rooms 列出所有房间 | Shows room name, users, topic 显示房间名、人数、主题 |
| `g` | Go to room (goto) 进入房间 | `g spacebar` |
| `w` | Who - view users in current room 查看当前房间用户 | Shows user list 显示用户列表 |
| `q` | Quit COM 退出COM | Shows "Unlinking TTY..." 显示"Unlinking TTY..." |

#### Message History / 消息历史

| Command 命令 | Function 功能 | Description 说明 |
|--------------|---------------|------------------|
| `r` | Review last 18 lines 查看最近18行历史 | Quick review 快速回顾 |
| `R` | Review specified lines 查看指定行数历史 | Enter line count 输入行数后回车 |

### Input Mode / 输入模式

| Operation 操作 | Description 说明 |
|----------------|------------------|
| Input Space 输入空格 | Enter input mode, shows username prompt 进入输入模式，显示用户名提示符 |
| Input message + Enter 输入消息 + 回车 | Send message to current room 发送消息到当前房间 |
| Message Format 消息格式 | `[username] your message 你的消息` |

### Default Rooms / 默认房间

| Room 房间 | Description 说明 |
|-----------|------------------|
| `lobby` | Default welcome room 默认进入的欢迎房间 |
| `spacebar` | Active chat room 活跃的聊天房间 |
| `anonradio` | Radio related room 电台相关房间 |

---

## SDF Shell Command Reference (for "sh:" prefix) / SDF Shell命令参考（用于"sh:"前缀）

When user uses "sh:" prefix, nanobot needs to translate natural language to correct SDF command.
当用户使用"sh:"前缀时，nanobot需要将自然语言翻译为正确的SDF命令。

### Information Query Commands / 信息查询命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| View help/command list 查看帮助/命令列表 | `help` or `commands` | Display basic Unix commands 显示基本Unix命令 |
| View membership info 查看会员信息 | `arpa` | ARPA membership info ARPA会员信息 |
| View MetaARPA info 查看MetaARPA信息 | `meta` | MetaARPA membership info MetaARPA会员信息 |
| View DBA info 查看DBA信息 | `dba` | Database membership info 数据库会员信息 |
| View membership types 查看会员类型 | `how` | Membership type overview 会员类型概览 |
| View software list 查看软件列表 | `software` | Software available per membership level 各会员级别可用软件 |
| View FAQ 查看FAQ | `faq` | Interactive FAQ browsing 交互式FAQ浏览 |
| View editor list 查看编辑器列表 | `editors` | Available text editors 可用文本编辑器 |
| View games list 查看游戏列表 | `games` | Installed games 安装的游戏 |
| View max users 查看最大用户数 | `maxusers` | Concurrent user record 同时在线用户记录 |
| View downtime reasons 查看停机原因 | `downtime` | Recent server downtime reasons 最近服务器停机原因 |

### Account Management Commands / 账户管理命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| Change password/info 修改密码/信息 | `maint` | Change password, shell, contact info 修改密码、shell、联系信息 |
| View disk usage 查看磁盘使用 | `disk` | Display home/mail/gopher/web space usage 显示home/mail/gopher/web空间使用 |
| View account expiry 查看账户到期 | `expire` | Display account expiry time 显示账户到期时间 |
| View membership dues 查看会员费 | `dues` | Membership dues details 会员费详情 |
| Set backspace key 设置退格键 | `bksp` | Set backspace key 设置退格键 |
| View available domains 查看可用域名 | `domains` | Domains for webhosting 可用于webhosting的域名 |

### Social Communication Commands / 社交通信命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| Enter chat room 进入聊天室 | `com` | COM chat system COM聊天系统 |
| View bulletin board 查看公告板 | `bboard` | SDF bulletin board system SDF公告板系统 |
| Send message to user 发送消息给用户 | `mesg` | Send message to other users 发送消息给其他用户 |
| Leave note for user 留言给用户 | `notes` | Leave note for other users 给其他用户留言 |
| View user info 查看用户信息 | `uinfo` | User join date and membership level 用户加入日期和会员级别 |
| View user website 查看用户网站 | `url username` | Display user website URL 显示用户网站URL |
| Set profile 设置个人资料 | `profiles` | Set personal profile 设置个人资料 |
| Sign/view guestbook 签名/查看留言板 | `guestbook` | SDF guestbook SDF留言板 |
| View online time 查看在线时间 | `online` | User's online time today 用户今日在线时间 |
| Submit journal 提交日志 | `happening` | Anonymous journal entry 匿名日志条目 |

### Website and Gopher Commands / 网站和Gopher命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| Create website 创建网站 | `mkhomepg` | Set up SDF website 设置SDF网站 |
| Create Gopher space 创建Gopher空间 | `mkgopher` | Set up Gopherspace 设置Gopherspace |
| Publish website 发布网站 | `addlink` | Publish website link 发布网站链接 |

### Database Commands / 数据库命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| Setup MySQL 设置MySQL | `startsql` | Create MySQL database (DBA member) 创建MySQL数据库(DBA会员) |
| Change MySQL password 修改MySQL密码 | `mypassword` | Change MySQL password 修改MySQL密码 |
| Reset MySQL password 重置MySQL密码 | `reset-mysql` | Reset MySQL password 重置MySQL密码 |

### VPN and VPS Commands / VPN和VPS命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| View VPN info 查看VPN信息 | `vpn` | VPN membership info VPN会员信息 |
| Configure VPN 配置VPN | `setvpn` | Configure PPTP VPN login 配置PPTP VPN登录 |
| View VPN stats 查看VPN统计 | `vpnstats` | VPN usage statistics VPN使用统计 |

### Other Utility Commands / 其他实用命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| Shorten URL 缩短URL | `surl` | SDF URL shortening service SDF URL缩短服务 |
| Upload file 上传文件 | `upload` | Upload files (rz wrapper) 上传文件(rz包装) |
| View random quote 查看随机名言 | `smj` | SDF admin quotes SDF管理员名言 |
| View stock price 查看股票价格 | `quote symbol` | Stock price (may not work) 股票价格(可能不可用) |
| Donation info 捐款信息 | `address` | SDF address and PayPal info SDF地址和PayPal信息 |
| View Twenex software 查看Twenex软件 | `twenex` | /sys/sdf/bin software summary /sys/sdf/bin软件摘要 |

### Common Unix Commands / 常用Unix命令

| User May Say 用户可能说 | Correct Command 正确命令 | Description 说明 |
|------------------------|--------------------------|------------------|
| List files 列出文件 | `ls` or `ls -la` | List directory contents 列出目录内容 |
| View current directory 查看当前目录 | `pwd` | Print working directory 显示当前目录 |
| Change directory 切换目录 | `cd dirname` | Change directory 切换目录 |
| View file content 查看文件内容 | `cat filename` | Display file content 显示文件内容 |
| View file (paged) 查看文件(分页) | `more filename` or `less filename` | Paged view 分页查看 |
| Edit file 编辑文件 | `pico filename` or `vi filename` | Edit file 编辑文件 |
| Create directory 创建目录 | `mkdir dirname` | Create directory 创建目录 |
| Delete file 删除文件 | `rm filename` | Remove file 删除文件 |
| Delete directory 删除目录 | `rmdir dirname` | Remove empty directory 删除空目录 |
| Copy file 复制文件 | `cp source dest` | Copy file 复制文件 |
| Move/rename 移动/重命名 | `mv source dest` | Move or rename 移动或重命名 |
| Find file 查找文件 | `find . -name "filename"` | Find file 查找文件 |
| View processes 查看进程 | `ps` or `ps aux` | Show processes 显示进程 |
| View disk space 查看磁盘空间 | `df -h` | Disk space 磁盘空间 |
| View who's online 查看谁在线 | `who` or `w` | Online users 在线用户 |

---

## nanobot Operation Guide / nanobot操作指南

When user requests the following, nanobot should call corresponding tools:
当用户请求以下操作时，nanobot应调用对应工具：

### COM Chat Operations / COM聊天操作

| User Request 用户请求 | Call Tool 调用工具 | Example 示例 |
|----------------------|-------------------|--------------|
| Connect to SDF 连接到SDF | `ssh_connect` | `ssh_connect("sdf.org", "user", "pass")` |
| Enter chat room 进入聊天室 | `com_login` | `com_login()` |
| Send message 发送消息 | `com_send` | `com_send(" Hello")` (space prefix 空格开头) |
| Read messages 读取消息 | `com_read` | `com_read(10)` |
| View users 查看用户 | `com_send` | `com_send("w")` |
| List rooms 列出房间 | `com_send` | `com_send("l")` |
| Enter room 进入房间 | `com_send` | `com_send("g spacebar")` |
| View history 查看历史 | `com_send` | `com_send("r")` |
| Exit chat 退出聊天 | `com_logout` | `com_logout()` |
| Disconnect 断开连接 | `ssh_disconnect` | `ssh_disconnect()` |

### SSH Command Operations (sh: prefix) / SSH命令操作（sh:前缀）

| User Request 用户请求 | Call Tool 调用工具 | Example 示例 |
|----------------------|-------------------|--------------|
| View help 查看帮助 | `com_send` | `com_send("help")` |
| View disk 查看磁盘 | `com_send` | `com_send("disk")` |
| View membership info 查看会员信息 | `com_send` | `com_send("arpa")` |
| View bulletin board 查看公告板 | `com_send` | `com_send("bboard")` |
| Change password 修改密码 | `com_send` | `com_send("maint")` |
| Execute Unix command 执行Unix命令 | `com_send` | `com_send("ls -la")` |

## Tool List / 工具列表

| Tool 工具 | Description 描述 | Parameters 参数 |
|-----------|------------------|-----------------|
| `ssh_connect` | Connect to SSH server 连接SSH服务器 | host, username, password, port |
| `com_login` | Login to COM chat room 登录COM聊天室 | none 无 |
| `com_send` | Send command/message 发送命令/消息 | message |
| `com_read` | Read messages 读取消息 | count |
| `com_logout` | Logout from COM 退出COM | none 无 |
| `ssh_disconnect` | Disconnect SSH 断开SSH | none 无 |

## Usage Examples / 使用示例

```
User 用户: Connect to sdf.org, username user, password pass 连接到sdf.org，用户名user，密码pass
Assistant 助手: [Call ssh_connect(host="sdf.org", username="user", password="pass")]
Connected to sdf.org 已连接到sdf.org

User 用户: Enter chat room 进入聊天室
Assistant 助手: [Call com_login()]
Logged into COM chat room, currently in lobby 已登录COM聊天室，当前在lobby房间

User 用户: List rooms 列出房间
Assistant 助手: [Call com_send("l")]
Room list 房间列表:
- spacebar (16 users 人): there is life out there
- lobby (1 user 人): SDF's Welcoming Room

User 用户: Enter spacebar room 进入spacebar房间
Assistant 助手: [Call com_send("g spacebar")]
Entered spacebar room 已进入spacebar房间

User 用户: com: Hello everyone 大家好
Assistant 助手: [Detected com: prefix, translate and send 检测到com:前缀，翻译为英文并发送]
Sent 发送: Hello everyone!

User 用户: sh: View disk usage 查看磁盘使用
Assistant 助手: [Detected sh: prefix, translate to command 检测到sh:前缀，翻译为命令]
[Call com_send("disk")]
Filesystem     Size  Used Avail Use%
/home/user      10G   2G   8G   20%

User 用户: sh: List files 列出文件
Assistant 助手: [Call com_send("ls -la")]
total 64
drwxr-xr-x  5 user user 4096 Jan 1 00:00 .
drwxr-xr-x  3 root root 4096 Jan 1 00:00 ..

User 用户: Exit 退出
Assistant 助手: [Call com_logout() and ssh_disconnect()]
Exited 已退出
```

## Notes / 注意事项

1. Requires Python 3.10+ 需要Python 3.10+
2. Requires SDF.org account 需要SDF.org账号
3. COM command mode has no prompt, only cursor COM命令模式下无提示符，只有光标
4. Send message requires space to enter input mode 发送消息需先输入空格进入输入模式
5. Messages auto-filter ANSI control characters 消息会自动过滤ANSI控制字符
6. Default uses nanobot message queue, no extra deployment needed 默认使用nanobot消息队列，无需额外部署
7. "sh:" prefix for SDF commands, nanobot translates natural language "sh:"前缀用于执行SDF命令，nanobot需将自然语言翻译为正确命令
yu