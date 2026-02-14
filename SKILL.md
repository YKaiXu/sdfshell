# SDFShell - SDF.org COM Chat Channel for nanobot

SDF.org COM chat room nanobot channel for bidirectional message passing with auto-translation support.

## What is COM?

**COM = SDF.org Chat Room System (NOT serial port!)**

- **COM** is the chat room system on SDF.org (Super Dimension Fortress)
- It's a multi-user chat system accessible via SSH
- Users can join different chat rooms like `#anonradio`, `#spacebar`, etc.
- **NOT related to serial ports (COM1, COM2, etc.)**

---

## 🎯 NANOBOT LEARNING PROMPT

**Copy this prompt and send to nanobot to teach it how to use SDFShell:**

```
You have a skill called "sdfshell" that lets you interact with SDF.org COM chat room.

## How to Use SDFShell

### Step 1: Configure Credentials
Before using, you MUST configure SDF credentials. When user says:
- "Set SDF username to XXX" → Call set_config(username="XXX")
- "Set SDF password to XXX" → Call set_config(password="XXX")
- "Configure SDF with username XXX and password YYY" → Call set_config(username="XXX", password="YYY")

### Step 2: Connect to SDF
When user says "Connect to SDF" or "Login to SDF":
1. Check if username and password are configured
2. If not configured, ask user to configure first
3. If configured, call ssh_connect() to establish SSH connection

### Step 3: Use COM Chat
When user message starts with "com:" prefix:
1. Extract the message after "com:"
2. Call com_send(message="extracted message")
3. DO NOT execute as bash command!

Example:
- User: "com: Hello everyone!"
- You: Call com_send(message="Hello everyone!")

### Step 4: Execute SSH Commands
When user message starts with "sh:" prefix:
1. Extract the command after "sh:"
2. Call ssh_exec(command="extracted command")
3. DO NOT execute as bash command!

Example:
- User: "sh: ls -la"
- You: Call ssh_exec(command="ls -la")

### Available Tools
- set_config() - Configure SDF credentials
- get_config_status() - Check current configuration
- ssh_connect() - Connect to SDF server
- ssh_disconnect() - Disconnect from SDF server
- ssh_exec() - Execute command on SDF server
- com_login() - Login to COM chat room
- com_send() - Send message to COM chat room
- com_read() - Read messages from COM chat room
- com_logout() - Logout from COM chat room

### IMPORTANT
- "com:" is NOT a bash command, it's a prefix to send chat messages
- "sh:" is NOT a bash command, it's a prefix to execute SSH commands
- Always check configuration before connecting
- Translate user's message to English before sending to COM (if needed)
```

---

## Core Technologies

| Component | Technology | Function |
|-----------|------------|----------|
| SSH Connection | paramiko-expect | Interactive SSH session, auto password input |
| Terminal Parsing | pyte | Parse ncurses output, extract chat messages |
| Message Queue | nanobot.bus.Queue | Message passing between SDFShell and nanobot |

## Architecture

### How SDFShell Connects to nanobot

**IMPORTANT**: SDFShell does NOT connect to nanobot via API. Instead:

1. **Chat Tool Connection**: Handled by nanobot's built-in Channels (Feishu, WeChat, Telegram, Discord, etc.)
2. **SDFShell Connection**: Uses nanobot's message queue mechanism (`nanobot.bus.Queue`)
3. **Message Flow**: External systems → Channel → Queue → Agent → Tools → Response

### Multi-Platform Support

SDFShell works with **ALL** nanobot-connected chat platforms:

| Platform | Connection | SDFShell Support |
|----------|------------|------------------|
| Feishu (飞书) | Built-in WebSocket | ✅ Full support |
| WeChat (微信) | Built-in Channel | ✅ Full support |
| Telegram | Built-in Channel | ✅ Full support |
| Discord | Built-in Channel | ✅ Full support |
| Slack | Built-in Channel | ✅ Full support |
| Any other | Custom Channel | ✅ Full support |

**How it works:**
```
┌─────────────────────────────────────────────────────────────┐
│                        nanobot                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Feishu    │    │    Agent    │    │  SDFShell   │     │
│  │   Channel   │◄──►│   (LLM)     │◄──►│   Channel   │     │
│  │ (built-in)  │    │             │    │  (skill)    │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│  ┌──────┴──────┐           │           ┌──────┴──────┐     │
│  │   WeChat    │           │           │   Telegram  │     │
│  │   Channel   │◄──────────┼──────────►│   Channel   │     │
│  └─────────────┘           │           └─────────────┘     │
│                            │                                │
│                    ┌───────▼───────┐                        │
│                    │ Message Queue │                        │
│                    │ (nanobot.bus) │                        │
│                    └───────────────┘                        │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    Feishu App            WeChat              Telegram
```

**Any user from any platform can:**
- Send messages to SDF.org COM chat room
- Receive COM messages (with auto-translation)
- Execute SDF shell commands

## Message Routing Rules

**CRITICAL: When user message starts with prefix, you MUST call the corresponding tool:**

| User Message | Tool to Call | Parameters |
|--------------|--------------|------------|
| `com: Hello` | `com_send` | `message="Hello"` |
| `com:hello` | `com_send` | `message="hello"` |
| `com: l` | `com_send` | `message="l"` (list rooms) |
| `com: g spacebar` | `com_send` | `message="g spacebar"` (join room) |
| `sh: ls -la` | `ssh_exec` | `command="ls -la"` |
| `sh:df -h` | `ssh_exec` | `command="df -h"` |
| `sh: help` | `ssh_exec` | `command="help"` |

**DO NOT execute `com:` or `sh:` as bash commands!**

Instead, extract the message after the prefix and call the appropriate tool.

### Routing Logic

```python
def route_message(user_message: str) -> dict:
    """Route user message to appropriate handler"""
    message = user_message.strip()
    
    # COM chat message
    if message.lower().startswith("com:"):
        content = message[4:].strip()
        return {"tool": "com_send", "message": content}
    
    # SSH command
    if message.lower().startswith("sh:"):
        command = message[3:].strip()
        return {"tool": "ssh_exec", "command": command}
    
    # Regular message - no routing
    return {"tool": None, "message": message}
```

### Usage Examples

**Example 1: Send chat message**
```
User: com: Hello everyone!
Action: Call com_send(message="Hello everyone!")
Result: Message sent to COM chat room
```

**Example 2: List chat rooms**
```
User: com: l
Action: Call com_send(message="l")
Result: List available chat rooms
```

**Example 3: Execute SSH command**
```
User: sh: ls -la
Action: Call ssh_exec(command="ls -la")
Result: Execute command on SDF server
```

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
Execute in bash: curl -fsSL https://raw.githubusercontent.com/YKaiXu/sdfshell/main/install.sh | bash
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

### Post-Installation Welcome Message

**IMPORTANT: After installation, nanobot MUST proactively send this welcome message to the user:**

```
🎉 SDFShell installed successfully!

I can now help you interact with SDF.org COM chat room. Here's how to use:

📝 Message Prefixes:
• com: Hello → Send "Hello" to COM chat room (auto-translate to English)
• sh: disk → Execute "disk" command on SDF server
• No prefix → Normal conversation with me

⚙️ Configuration Required:
Before using, please configure your SDF credentials:
• Say "Set SDF host to sdf.org"
• Say "Set SDF username to YOUR_USERNAME"
• Say "Set SDF password to YOUR_PASSWORD"
Or say "Configure SDF with username YOUR_NAME and password YOUR_PASS"

🚀 Quick Start:
1. Configure your credentials (see above)
2. Say "Connect to SDF" or "Connect to server"
3. Say "Enter chat room" to join COM
4. Say "com: Hello everyone!" to send a message

💡 Tips:
• Use "sh: help" to see all SDF commands
• Use "com: l" to list chat rooms
• Use "com: g spacebar" to join the active room

Ask me anything about SDF.org!
```

### Configuration via Conversation

**nanobot can configure SDF through natural conversation:**

| User Says | nanobot Action |
|-----------|----------------|
| "Set SDF host to sdf.org" | Call `set_config(host="sdf.org")` |
| "Set SDF username to myname" | Call `set_config(username="myname")` |
| "Set SDF password to mypass" | Call `set_config(password="mypass")` |
| "Configure SDF with username X and password Y" | Call `set_config(username="X", password="Y")` |
| "What's my SDF config?" | Call `get_config_status()` |
| "Connect to SDF" | Check config, then call `ssh_connect()` |

**Configuration is saved to:** `~/.nanobot/skills/sdfshell/config.json`

### Message Processing Logic

**When COM messages arrive, nanobot should:**

1. **Translate**: Detect source language, translate to user's chat tool language
2. **Summarize**: If multiple messages, provide a brief summary
3. **Remind**: Add helpful context when appropriate

**Example Output Format:**

```
📨 [COM Message] from spacebar room:

user1: Hey, anyone know how to use IRC here?
user2: Yes, type 'help irc' in the shell

---
💡 Summary: Users discussing IRC usage on SDF
🔄 Translated from English to Chinese
```

**When to add reminders:**
- New user joins the room → Remind about room rules
- Technical question asked → Suggest relevant SDF commands
- User seems confused → Offer help with specific commands

## Configuration

Add to nanobot's `~/.nanobot/config.json`:

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

## Running Methods

SDFShell supports two running modes:

### 1. As nanobot Channel (Recommended)

SDFShell runs as a nanobot channel, integrated with nanobot's message processing:

```json
// Add to ~/.nanobot/config.json
{
  "channels": {
    "sdfshell": {
      "enabled": true,
      "host": "sdf.org",
      "username": "your_username",
      "password": "your_password"
    }
  }
}
```

Then start nanobot normally - SDFShell will auto-start.

### 2. As systemd Service (Standalone)

For standalone monitoring without nanobot:

```bash
# Install service
mkdir -p ~/.config/systemd/user
cp ~/.nanobot/workspace/skills/sdfshell/sdfshell.service ~/.config/systemd/user/

# Enable and start
systemctl --user enable sdfshell
systemctl --user start sdfshell

# Check status
systemctl --user status sdfshell

# View logs
journalctl --user -u sdfshell -f
```

### Log Files

| Location | Description |
|----------|-------------|
| `~/.nanobot/logs/sdfshell.log` | Main log file |
| `journalctl --user -u sdfshell` | systemd journal logs |

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

**File and Directory Commands:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| List files | `ls` | List directory contents |
| List all files (hidden too) | `ls -la` | List all files with details |
| View current directory | `pwd` | Print working directory |
| Change directory | `cd dirname` | Change to directory |
| Go to home directory | `cd ~` or `cd` | Go to home |
| Go up one directory | `cd ..` | Parent directory |
| Create directory | `mkdir dirname` | Create new directory |
| Create nested directories | `mkdir -p path/to/dir` | Create parent dirs as needed |
| Remove empty directory | `rmdir dirname` | Remove empty directory |
| Remove directory with contents | `rm -rf dirname` | Remove directory recursively |
| Create empty file | `touch filename` | Create empty file |
| View file content | `cat filename` | Display file content |
| View file with line numbers | `cat -n filename` | Display with line numbers |
| View file (paged) | `less filename` | Paged view, use q to quit |
| View first 10 lines | `head filename` | First 10 lines |
| View first N lines | `head -n 20 filename` | First 20 lines |
| View last 10 lines | `tail filename` | Last 10 lines |
| View last N lines | `tail -n 20 filename` | Last 20 lines |
| Follow file updates | `tail -f filename` | Follow file updates live |
| Copy file | `cp source dest` | Copy file |
| Copy directory | `cp -r source dest` | Copy directory recursively |
| Move/rename file | `mv source dest` | Move or rename |
| Delete file | `rm filename` | Remove file |
| Delete multiple files | `rm file1 file2` | Remove multiple files |
| Find file by name | `find . -name "filename"` | Find file in current dir |
| Find file by type | `find . -type f -name "*.txt"` | Find all .txt files |
| Search in file | `grep "pattern" filename` | Search for pattern |
| Search case-insensitive | `grep -i "pattern" filename` | Case-insensitive search |
| Search in all files | `grep -r "pattern" .` | Recursive search |
| Compare two files | `diff file1 file2` | Show differences |
| Archive files | `tar -cvf archive.tar files` | Create tar archive |
| Extract archive | `tar -xvf archive.tar` | Extract tar archive |
| Compress with gzip | `gzip filename` | Compress file |
| Decompress gzip | `gunzip filename.gz` | Decompress file |
| Create zip | `zip archive.zip files` | Create zip archive |
| Extract zip | `unzip archive.zip` | Extract zip archive |

**File Permissions and Ownership:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Change permissions | `chmod 755 filename` | Set rwx for owner, rx for others |
| Change permissions recursive | `chmod -R 755 dirname` | Recursive permission change |
| Make executable | `chmod +x filename` | Add execute permission |
| Change owner | `chown user filename` | Change file owner |
| Change owner and group | `chown user:group filename` | Change owner and group |
| View permissions | `ls -la filename` | Show file permissions |

**Process Management:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| View running processes | `ps` | Show processes |
| View all processes | `ps aux` | Show all processes |
| View processes live | `top` | Interactive process viewer |
| View processes (better) | `htop` | Enhanced process viewer |
| Kill process by PID | `kill PID` | Terminate process |
| Force kill process | `kill -9 PID` | Force terminate |
| Kill by name | `killall name` | Kill all processes by name |
| Run in background | `command &` | Run command in background |
| View background jobs | `jobs` | List background jobs |
| Bring to foreground | `fg %1` | Bring job 1 to foreground |
| Send to background | `bg %1` | Send job 1 to background |

**Disk and System Information:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| View disk space | `df -h` | Disk space human-readable |
| View directory size | `du -sh dirname` | Directory size |
| View file size | `du -h filename` | File size |
| View memory usage | `free -h` | Memory usage |
| View system info | `uname -a` | System information |
| View hostname | `hostname` | Show hostname |
| View uptime | `uptime` | System uptime |
| View who's online | `who` or `w` | Online users |
| View current user | `whoami` | Current username |
| View user groups | `groups` | User's groups |
| View user ID | `id` | User and group IDs |

**Network Commands:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Test connectivity | `ping hostname` | Ping a host |
| View network interfaces | `ifconfig` or `ip a` | Network interfaces |
| View ports | `netstat -tuln` | Listening ports |
| View connections | `ss -tuln` | Socket statistics |
| Download file | `wget URL` | Download from URL |
| Download with curl | `curl -O URL` | Download with curl |
| Trace network route | `traceroute hostname` | Trace route to host |
| DNS lookup | `nslookup hostname` | DNS query |
| View routing table | `route -n` | Routing table |

**Text Processing:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Print text | `echo "text"` | Print text |
| Append to file | `echo "text" >> file` | Append text to file |
| Overwrite file | `echo "text" > file` | Overwrite file |
| Sort file contents | `sort filename` | Sort lines |
| Sort reverse | `sort -r filename` | Sort in reverse |
| Count lines | `wc -l filename` | Count lines |
| Count words | `wc -w filename` | Count words |
| Count characters | `wc -c filename` | Count characters |
| Remove duplicates | `sort filename \| uniq` | Unique lines |
| Cut columns | `cut -d',' -f1 filename` | Cut first column by delimiter |
| Search and replace | `sed 's/old/new/g' filename` | Replace all occurrences |
| Print specific lines | `sed -n '5,10p' filename` | Print lines 5-10 |

**User Management:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Add user | `useradd username` | Create new user |
| Modify user | `usermod options username` | Modify user |
| Delete user | `userdel username` | Delete user |
| Change password | `passwd` | Change own password |
| Change user password | `passwd username` | Change user's password |
| Switch user | `su username` | Switch to user |
| Run as root | `sudo command` | Run with elevated privileges |
| Switch to root | `sudo su` or `su -` | Become root |

**System Control:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Start service | `systemctl start service` | Start service |
| Stop service | `systemctl stop service` | Stop service |
| Restart service | `systemctl restart service` | Restart service |
| Service status | `systemctl status service` | Check service status |
| Enable service | `systemctl enable service` | Enable at boot |
| Disable service | `systemctl disable service` | Disable at boot |
| View logs | `journalctl -u service` | View service logs |
| Shutdown system | `shutdown now` | Shutdown immediately |
| Reboot system | `reboot` | Restart system |

**Environment and Variables:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| View environment | `env` or `printenv` | Show environment variables |
| Set variable | `export VAR=value` | Set environment variable |
| View PATH | `echo $PATH` | Show PATH variable |
| View home directory | `echo $HOME` | Show home directory |
| Create alias | `alias name='command'` | Create command alias |
| View aliases | `alias` | List all aliases |
| Find command location | `which command` | Show command path |
| Find binary/source/man | `whereis command` | Show all locations |
| Command description | `whatis command` | Brief command description |
| View manual | `man command` | Command manual page |

**File Editors:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Edit with nano | `nano filename` | Simple editor |
| Edit with vim | `vi filename` or `vim filename` | Advanced editor |
| Edit with emacs | `emacs filename` | Emacs editor |

**SSH and Remote:**

| User May Say | Correct Command | Description |
|--------------|-----------------|-------------|
| Connect to server | `ssh user@host` | SSH connection |
| Connect with port | `ssh -p port user@host` | SSH with specific port |
| Copy file to remote | `scp file user@host:/path` | Secure copy |
| Copy from remote | `scp user@host:/path/file .` | Copy from remote |
| Sync directory | `rsync -avz source/ dest/` | Sync directories |

**Natural Language Translation Examples:**

| User Says | Translate To |
|-----------|--------------|
| "Show me all files" | `ls -la` |
| "What directory am I in?" | `pwd` |
| "Go to home" | `cd ~` |
| "Create a folder called test" | `mkdir test` |
| "Delete the test folder" | `rm -rf test` |
| "Make a new file called notes.txt" | `touch notes.txt` |
| "Show what's in notes.txt" | `cat notes.txt` |
| "Copy file.txt to backup/" | `cp file.txt backup/` |
| "Move old.txt to new.txt" | `mv old.txt new.txt` |
| "Find all Python files" | `find . -name "*.py"` |
| "Search for 'error' in log.txt" | `grep "error" log.txt` |
| "How much disk space is left?" | `df -h` |
| "What's using the most space?" | `du -sh * \| sort -rh \| head` |
| "Show running processes" | `ps aux` |
| "Kill process 1234" | `kill 1234` |
| "What's my IP address?" | `ip a` or `ifconfig` |
| "Download this URL" | `wget URL` |
| "Count lines in file" | `wc -l filename` |
| "Show last 50 lines of log" | `tail -n 50 filename` |
| "Follow the log file" | `tail -f filename` |

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
