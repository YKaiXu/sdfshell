# SDFShell - SDF.org COM Chat Channel for nanobot

SDF.org COM chat room nanobot channel for bidirectional message passing with auto-translation support.

## Core Technologies

| Component | Technology | Function |
|-----------|------------|----------|
| SSH Connection | paramiko-expect | Interactive SSH session, auto password input |
| Terminal Parsing | pyte | Parse ncurses output, extract chat messages |
| Message Queue | nanobot.bus.Queue | Reliable message passing mechanism |

## Message Routing Rules

### Two Prefix Types

| Prefix | Purpose | Description |
|--------|---------|-------------|
| `com:` | **Send Chat Message** | Send message to COM chat room (auto-translate to English) |
| `sh:` | **Execute Command** | Execute SSH/SDF command (no translation) |
| No prefix | Normal conversation | Chat with nanobot, not sent to COM |

### Important Notes

- **`com:` prefix**: Message content will be **auto-translated to English** before sending to COM chat room
- **`sh:` prefix**: Command will be executed **without translation**, nanobot only translates natural language to correct command

### Message Flow

```
【COM → Feishu】
COM Chat Room → pyte Parse → Queue → Agent(LLM Translate) → Feishu

【Feishu → COM】
Feishu Message → Detect Prefix → 
  - "com:" → Translate to English → SSH Send → COM Chat Room
  - "sh:" → Execute SSH Command → Return Result
  - No prefix → Normal Conversation
```

### Bidirectional Auto-Translation

**Feishu → COM**:
1. User sends message in any language
2. nanobot detects `com:` prefix
3. LLM translates to English
4. Send to COM chat room

**COM → Feishu**:
1. COM message arrives (any language)
2. Message goes to queue
3. nanobot detects source language
4. LLM translates to user's chat tool language
5. Send to Feishu

**Implementation Status**:
- ✅ Message routing logic
- ✅ Queue mechanism
- ⚠️ Auto-translation requires nanobot LLM integration

## Installation

### One-Click Install Command

Send this command to nanobot:

```
请在bash执行: curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash
```

Or manually install:

```bash
# One-click install
curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash

# Or clone manually
git clone https://github.com/YKaiXu/sdfshell.git ~/.nanobot/skills/sdfshell
cd ~/.nanobot/skills/sdfshell
python3 -m venv venv
source venv/bin/activate
pip install paramiko paramiko-expect pyte
```

### What nanobot will learn

After installation, nanobot automatically knows:
- ✅ `com:` prefix - Send chat message (auto-translate to English)
- ✅ `sh:` prefix - Execute SSH/SDF command
- ✅ All COM chat room commands
- ✅ All SDF shell commands
- ✅ Common Unix commands
- ✅ Bidirectional auto-translation

## Configuration

Add to nanobot's `~/.nanobot/config.yaml`:

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

## COM Chat Room Complete Command Reference

**Important: COM has two modes - Command Mode and Input Mode**

### Mode Switching

| Operation | Description |
|-----------|-------------|
| Default to Command Mode | Command mode is default after starting COM |
| Input Space | Enter Input Mode (send message) |
| After sending message | Auto return to Command Mode |

### Command Mode Commands

#### Room Management

| Command | Function | Example |
|---------|----------|---------|
| `l` | List all rooms | Shows room name, users, topic |
| `g` | Go to room (goto) | `g spacebar` |
| `w` | Who - view users in current room | Shows user list |
| `q` | Quit COM | Shows "Unlinking TTY..." |

#### Message History

| Command | Function | Description |
|---------|----------|-------------|
| `r` | Review last 18 lines | Quick review |
| `R` | Review specified lines | Enter line count |

### Input Mode

| Operation | Description |
|-----------|-------------|
| Input Space | Enter input mode, shows username prompt |
| Input message + Enter | Send message to current room |
| Message Format | `[username] your message` |

### Default Rooms

| Room | Description |
|------|-------------|
| `lobby` | Default welcome room |
| `spacebar` | Active chat room |
| `anonradio` | Radio related room |

---

## SDF Shell Command Reference (for "sh:" prefix)

When user uses "sh:" prefix, nanobot needs to translate natural language to correct SDF command.

### Information Query Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| View help/command list | `help` or `commands` | Display basic Unix commands |
| View membership info | `arpa` | ARPA membership info |
| View MetaARPA info | `meta` | MetaARPA membership info |
| View DBA info | `dba` | Database membership info |
| View membership types | `how` | Membership type overview |
| View software list | `software` | Software available per membership level |
| View FAQ | `faq` | Interactive FAQ browsing |
| View editor list | `editors` | Available text editors |
| View games list | `games` | Installed games |
| View max users | `maxusers` | Concurrent user record |
| View downtime reasons | `downtime` | Recent server downtime reasons |

### Account Management Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Change password/info | `maint` | Change password, shell, contact info |
| View disk usage | `disk` | Display home/mail/gopher/web space usage |
| View account expiry | `expire` | Display account expiry time |
| View membership dues | `dues` | Membership dues details |
| Set backspace key | `bksp` | Set backspace key |
| View available domains | `domains` | Domains for webhosting |

### Social Communication Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Enter chat room | `com` | COM chat system |
| View bulletin board | `bboard` | SDF bulletin board system |
| Send message to user | `mesg` | Send message to other users |
| Leave note for user | `notes` | Leave note for other users |
| View user info | `uinfo` | User join date and membership level |
| View user website | `url username` | Display user website URL |
| Set profile | `profiles` | Set personal profile |
| Sign/view guestbook | `guestbook` | SDF guestbook |
| View online time | `online` | User's online time today |
| Submit journal | `happening` | Anonymous journal entry |

### Website and Gopher Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Create website | `mkhomepg` | Set up SDF website |
| Create Gopher space | `mkgopher` | Set up Gopherspace |
| Publish website | `addlink` | Publish website link |

### Database Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Setup MySQL | `startsql` | Create MySQL database (DBA member) |
| Change MySQL password | `mypassword` | Change MySQL password |
| Reset MySQL password | `reset-mysql` | Reset MySQL password |

### VPN and VPS Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| View VPN info | `vpn` | VPN membership info |
| Configure VPN | `setvpn` | Configure PPTP VPN login |
| View VPN stats | `vpnstats` | VPN usage statistics |

### Other Utility Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Shorten URL | `surl` | SDF URL shortening service |
| Upload file | `upload` | Upload files (rz wrapper) |
| View random quote | `smj` | SDF admin quotes |
| View stock price | `quote symbol` | Stock price (may not work) |
| Donation info | `address` | SDF address and PayPal info |
| View Twenex software | `twenex` | /sys/sdf/bin software summary |

### Common Unix Commands

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| List files | `ls` or `ls -la` | List directory contents |
| View current directory | `pwd` | Print working directory |
| Change directory | `cd dirname` | Change directory |
| View file content | `cat filename` | Display file content |
| View file (paged) | `more filename` or `less filename` | Paged view |
| Edit file | `pico filename` or `vi filename` | Edit file |
| Create directory | `mkdir dirname` | Create directory |
| Delete file | `rm filename` | Remove file |
| Delete directory | `rmdir dirname` | Remove empty directory |
| Copy file | `cp source dest` | Copy file |
| Move/rename | `mv source dest` | Move or rename |
| Find file | `find . -name "filename"` | Find file |
| View processes | `ps` or `ps aux` | Show processes |
| View disk space | `df -h` | Disk space |
| View who's online | `who` or `w` | Online users |

---

## nanobot Operation Guide

When user requests the following, nanobot should call corresponding tools:

### COM Chat Operations

| User Request | Call Tool | Example |
|--------------|-----------|---------|
| Connect to SDF | `ssh_connect` | `ssh_connect("sdf.org", "user", "pass")` |
| Enter chat room | `com_login` | `com_login()` |
| Send message | `com_send` | `com_send(" Hello")` (space prefix) |
| Read messages | `com_read` | `com_read(10)` |
| View users | `com_send` | `com_send("w")` |
| List rooms | `com_send` | `com_send("l")` |
| Enter room | `com_send` | `com_send("g spacebar")` |
| View history | `com_send` | `com_send("r")` |
| Exit chat | `com_logout` | `com_logout()` |
| Disconnect | `ssh_disconnect` | `ssh_disconnect()` |

### SSH Command Operations (sh: prefix)

| User Request | Call Tool | Example |
|--------------|-----------|---------|
| View help | `com_send` | `com_send("help")` |
| View disk | `com_send` | `com_send("disk")` |
| View membership info | `com_send` | `com_send("arpa")` |
| View bulletin board | `com_send` | `com_send("bboard")` |
| Change password | `com_send` | `com_send("maint")` |
| Execute Unix command | `com_send` | `com_send("ls -la")` |

## Tool List

| Tool | Description | Parameters |
|------|-------------|------------|
| `ssh_connect` | Connect to SSH server | host, username, password, port |
| `com_login` | Login to COM chat room | none |
| `com_send` | Send command/message | message |
| `com_read` | Read messages | count |
| `com_logout` | Logout from COM | none |
| `ssh_disconnect` | Disconnect SSH | none |

## Usage Examples

```
User: Connect to sdf.org, username user, password pass
Assistant: [Call ssh_connect(host="sdf.org", username="user", password="pass")]
Connected to sdf.org

User: Enter chat room
Assistant: [Call com_login()]
Logged into COM chat room, currently in lobby

User: List rooms
Assistant: [Call com_send("l")]
Room list:
- spacebar (16 users): there is life out there
- lobby (1 user): SDF's Welcoming Room

User: Enter spacebar room
Assistant: [Call com_send("g spacebar")]
Entered spacebar room

User: com: Hello everyone
Assistant: [Detected com: prefix, translate and send]
Sent: Hello everyone!

User: sh: View disk usage
Assistant: [Detected sh: prefix, translate to command]
[Call com_send("disk")]
Filesystem     Size  Used Avail Use%
/home/user      10G   2G   8G   20%

User: sh: List files
Assistant: [Call com_send("ls -la")]
total 64
drwxr-xr-x  5 user user 4096 Jan 1 00:00 .
drwxr-xr-x  3 root root 4096 Jan 1 00:00 ..

User: Exit
Assistant: [Call com_logout() and ssh_disconnect()]
Exited
```

## Notes

1. Requires Python 3.10+
2. Requires SDF.org account
3. COM command mode has no prompt, only cursor
4. Send message requires space to enter input mode
5. Messages auto-filter ANSI control characters
6. Default uses nanobot message queue, no extra deployment needed
7. "sh:" prefix for SDF commands, nanobot translates natural language

## Author

**YUKAIXU**
- Location: Hubei, China
- Email: yukaixu@outlook.com
- GitHub: https://github.com/YKaiXu
