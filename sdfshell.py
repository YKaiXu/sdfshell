#!/usr/bin/env python3
"""SDFShell - SDF.org COM Chat Channel for nanobot

基于nanobot.channels.base.BaseChannel实现的COM聊天室通道。
使用paramiko-expect进行交互式SSH连接，pyte解析ncurses输出。

消息流向：
- COM消息 → SDFShellChannel → nanobot Queue → Agent → 飞书
- 飞书消息 → FeishuChannel → nanobot Queue → Agent → SDFShellChannel → COM

核心依赖：
- paramiko-expect: 交互式SSH会话
- pyte: 终端模拟器，解析ncurses输出
- nanobot.bus: 消息队列机制
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# 依赖检查
try:
    import paramiko
    from paramiko_expect import SSHClientInteraction
    HAS_PARAMIKO_EXPECT = True
except ImportError:
    HAS_PARAMIKO_EXPECT = False

try:
    import pyte
    HAS_PYTE = True
except ImportError:
    HAS_PYTE = False

# nanobot导入
try:
    from nanobot.channels.base import BaseChannel
    from nanobot.bus.queue import Queue
    from nanobot.bus.events import Event
    HAS_NANOBOT = True
except ImportError:
    HAS_NANOBOT = False
    Queue = None
    Event = None
    class BaseChannel:
        def __init__(self, config: dict):
            self.config = config
        async def start(self): pass
        async def stop(self): pass
        async def send(self, message: dict): pass

log = logging.getLogger("sdfshell")


class SDFShellError(Exception):
    """SDFShell异常"""
    pass


def strip_ansi(text: str) -> str:
    """移除ANSI控制字符"""
    pattern = re.compile(r'\x1b\[[0-9;]*[mGKH]|\x1b\][^\x07]*\x07|\x1b[()][AB012]')
    return pattern.sub('', text)


def clean_text(text: str) -> str:
    """清理文本，只保留可读内容"""
    text = strip_ansi(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return ' '.join(text.split()).strip()


class TerminalEmulator:
    """pyte终端模拟器 - 解析ncurses输出"""
    
    def __init__(self, cols: int = 80, rows: int = 24):
        if not HAS_PYTE:
            raise SDFShellError("pyte not installed: pip install pyte")
        self.cols = cols
        self.rows = rows
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream(self.screen)
    
    def feed(self, data: str) -> None:
        self.stream.feed(data)
    
    def get_display(self) -> str:
        lines = [clean_text(line) for line in self.screen.display]
        return '\n'.join(line for line in lines if line)
    
    def get_messages(self) -> list[str]:
        """提取用户聊天消息"""
        messages = []
        system_keywords = {'welcome', 'connected', 'disconnected', 'system', 'server', 'online'}
        system_users = {'system', 'server', 'bot', 'admin'}
        
        for line in self.screen.display:
            line = clean_text(line)
            if len(line) < 3:
                continue
            
            line_lower = line.lower()
            if any(kw in line_lower for kw in system_keywords):
                continue
            
            match = re.match(r'^[<\[]?(\w+)[>\]:]\s*(.+)$', line)
            if match:
                user, msg = match.group(1).strip(), match.group(2).strip()
                if msg and user.lower() not in system_users:
                    messages.append(f"{user}: {msg}")
        
        return messages
    
    def reset(self) -> None:
        self.screen = pyte.Screen(self.cols, self.rows)
        self.stream = pyte.Stream(self.screen)


class SSHSession:
    """paramiko-expect SSH会话管理"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        if not HAS_PARAMIKO_EXPECT:
            raise SDFShellError("paramiko-expect not installed: pip install paramiko-expect")
        
        self.client: Optional[paramiko.SSHClient] = None
        self.interact: Optional[SSHClientInteraction] = None
        self.terminal: Optional[TerminalEmulator] = None
        self._connected = False
        self._op_lock = threading.Lock()
    
    @property
    def connected(self) -> bool:
        return self._connected and self.client is not None
    
    def connect(self, host: str, username: str, password: str, port: int = 22) -> str:
        """使用paramiko-expect连接SSH"""
        with self._op_lock:
            try:
                if self.connected:
                    return f"Already connected to {self.client.get_transport().getpeername()[0]}"
                
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=30,
                    banner_timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
                
                self.interact = SSHClientInteraction(self.client, timeout=60, display=False)
                self.terminal = TerminalEmulator()
                self._connected = True
                
                log.info(f"SSH connected: {host}:{port}")
                return f"Connected to {host}:{port}"
                
            except Exception as e:
                log.error(f"SSH connection failed: {e}")
                raise SDFShellError(f"Connection failed: {e}") from e
    
    def disconnect(self) -> str:
        """断开连接"""
        with self._op_lock:
            if not self.connected:
                return "Not connected"
            
            try:
                if self.interact:
                    self.interact.close()
                if self.client:
                    self.client.close()
                
                self._connected = False
                log.info("SSH disconnected")
                return "Disconnected"
                
            except Exception as e:
                log.error(f"Disconnect error: {e}")
                raise SDFShellError(f"Disconnect failed: {e}") from e
    
    def send_command(self, command: str, expect: str = "$", timeout: float = 5.0) -> str:
        """使用paramiko-expect发送命令"""
        with self._op_lock:
            if not self.connected or not self.interact:
                raise SDFShellError("Not connected")
            
            try:
                self.interact.send(command)
                self.interact.expect(expect, timeout=timeout)
                
                output = self.interact.current_output
                if self.terminal and output:
                    self.terminal.feed(output)
                    return self.terminal.get_display()
                
                return clean_text(output)
                
            except Exception as e:
                log.error(f"Send command error: {e}")
                raise SDFShellError(f"Command failed: {e}") from e
    
    def send_and_read(self, command: str, wait: float = 1.0) -> tuple[str, list[str]]:
        """发送命令并读取消息"""
        with self._op_lock:
            if not self.connected or not self.interact:
                raise SDFShellError("Not connected")
            
            try:
                self.interact.send(command)
                time.sleep(wait)
                
                output = ""
                while self.interact.channel.recv_ready():
                    output += self.interact.channel.recv(4096).decode('utf-8', errors='replace')
                
                if self.terminal and output:
                    self.terminal.feed(output)
                    return self.terminal.get_display(), self.terminal.get_messages()
                
                return clean_text(output), []
                
            except Exception as e:
                log.error(f"Send and read error: {e}")
                raise SDFShellError(f"Read failed: {e}") from e


class COMSession:
    """COM聊天室会话"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, ssh: SSHSession = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, ssh: SSHSession = None):
        if self._initialized:
            return
        self._initialized = True
        
        self.ssh = ssh or SSHSession()
        self._in_com = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        self._message_callback: Optional[Callable[[list[str]], None]] = None
    
    @property
    def in_com(self) -> bool:
        return self._in_com
    
    def login(self) -> str:
        """登录COM聊天室"""
        if not self.ssh.connected:
            raise SDFShellError("SSH not connected")
        
        try:
            display, _ = self.ssh.send_and_read("com", wait=2.0)
            
            if ">" in display or "COM" in display.upper():
                self._in_com = True
                log.info("COM logged in")
                return f"Logged into COM\n{display}"
            
            return f"Login may have failed\n{display}"
            
        except Exception as e:
            log.error(f"COM login error: {e}")
            raise SDFShellError(f"Login failed: {e}") from e
    
    def logout(self) -> str:
        """退出COM"""
        if not self._in_com:
            return "Not in COM"
        
        self._monitoring = False
        
        try:
            self.ssh.send_command("/q", expect="$", timeout=2.0)
            self._in_com = False
            log.info("COM logged out")
            return "Logged out of COM"
            
        except Exception as e:
            log.error(f"COM logout error: {e}")
            raise SDFShellError(f"Logout failed: {e}") from e
    
    def send_message(self, message: str) -> str:
        """发送消息到COM"""
        if not self._in_com:
            raise SDFShellError("Not in COM")
        
        try:
            self.ssh.send_and_read(message, wait=0.5)
            log.info(f"Message sent: {message[:50]}...")
            return f"Sent: {message}"
            
        except Exception as e:
            log.error(f"Send message error: {e}")
            raise SDFShellError(f"Send failed: {e}") from e
    
    def read_messages(self, count: int = 10) -> list[str]:
        """读取COM消息"""
        if not self._in_com:
            raise SDFShellError("Not in COM")
        
        try:
            _, messages = self.ssh.send_and_read("", wait=0.5)
            return messages[-count:] if messages else []
            
        except Exception as e:
            log.error(f"Read messages error: {e}")
            raise SDFShellError(f"Read failed: {e}") from e
    
    def start_monitor(self, callback: Callable[[list[str]], None], interval: float = 3.0) -> str:
        """启动消息监控"""
        if self._monitoring:
            return "Already monitoring"
        
        self._message_callback = callback
        self._monitoring = True
        
        def _monitor_loop():
            while self._monitoring and self._in_com:
                try:
                    messages = self.read_messages(count=5)
                    if messages and self._message_callback:
                        self._message_callback(messages)
                except Exception as e:
                    log.error(f"Monitor error: {e}")
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()
        log.info("Message monitor started")
        return "Monitor started"
    
    def stop_monitor(self) -> str:
        """停止监控"""
        self._monitoring = False
        log.info("Message monitor stopped")
        return "Monitor stopped"


class SDFShellChannel(BaseChannel):
    """SDFShell nanobot通道
    
    继承nanobot.channels.base.BaseChannel，实现COM聊天室消息收发。
    使用nanobot.bus.Queue进行消息传递，确保可靠性。
    
    配置示例 (config.yaml):
        channels:
          sdfshell:
            enabled: true
            host: sdf.org
            port: 22
            username: your_username
            password: your_password
            monitor_interval: 3.0
    
    消息流向：
        COM消息 → pyte解析 → Queue → Agent → 飞书
        飞书消息 → Queue → Agent翻译 → SSH发送 → COM
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # 从配置或环境变量读取
        self.host = config.get("host") or os.environ.get("SDF_HOST", "sdf.org")
        self.port = config.get("port") or int(os.environ.get("SDF_PORT", "22"))
        self.username = config.get("username") or os.environ.get("SDF_USERNAME", "")
        self.password = config.get("password") or os.environ.get("SDF_PASSWORD", "")
        self.monitor_interval = config.get("monitor_interval", 3.0)
        
        self._ssh = SSHSession()
        self._com = COMSession(self._ssh)
        
        # 使用nanobot消息队列（如果可用）
        if HAS_NANOBOT and Queue:
            self._queue = Queue()
            self._use_nanobot_queue = True
            log.info("Using nanobot bus queue")
        else:
            # 回退到内存队列
            self._message_queue: list[dict] = []
            self._queue_lock = threading.Lock()
            self._use_nanobot_queue = False
            log.warning("nanobot queue not available, using memory queue")
        
        self._running = False
    
    async def start(self) -> None:
        """启动通道"""
        log.info(f"Starting SDFShell channel: {self.host}")
        
        if not self.username or not self.password:
            log.warning("Username/password not configured. Use ssh_connect to connect manually.")
            return
        
        self._ssh.connect(self.host, self.username, self.password, self.port)
        self._com.login()
        
        self._running = True
        
        self._com.start_monitor(
            callback=self._on_com_message,
            interval=self.monitor_interval
        )
        
        log.info("SDFShell channel started")
    
    async def stop(self) -> None:
        """停止通道"""
        log.info("Stopping SDFShell channel")
        
        self._running = False
        self._com.stop_monitor()
        self._com.logout()
        self._ssh.disconnect()
        
        log.info("SDFShell channel stopped")
    
    def _on_com_message(self, messages: list[str]) -> None:
        """处理COM消息回调 - 放入队列（反向通道：COM → nanobot）"""
        for msg in messages:
            if self._use_nanobot_queue and Event:
                # 使用nanobot消息队列
                event = Event(
                    type="message",
                    channel="sdfshell",
                    data={"content": msg, "timestamp": time.time()}
                )
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._queue.publish(event))
                    else:
                        loop.run_until_complete(self._queue.publish(event))
                except:
                    pass
            else:
                # 内存队列回退
                event = {
                    "type": "message",
                    "channel": "sdfshell",
                    "content": msg,
                    "timestamp": time.time()
                }
                with self._queue_lock:
                    self._message_queue.append(event)
            
            log.debug(f"COM message queued: {msg[:50]}...")
    
    async def receive(self) -> AsyncGenerator[dict, None]:
        """接收消息（nanobot调用）- 反向通道入口"""
        if self._use_nanobot_queue:
            async for event in self._queue.subscribe():
                if not self._running:
                    break
                yield {
                    "type": event.type,
                    "channel": getattr(event, 'channel', 'sdfshell'),
                    "content": event.data.get("content", "") if hasattr(event, 'data') else "",
                    "timestamp": event.data.get("timestamp", time.time()) if hasattr(event, 'data') else time.time()
                }
        else:
            while self._running:
                with self._queue_lock:
                    if self._message_queue:
                        event = self._message_queue.pop(0)
                        yield event
                        continue
                
                await asyncio.sleep(0.1)
    
    async def send(self, message: dict) -> None:
        """发送消息（nanobot调用）- 正向通道：nanobot → COM"""
        content = message.get("content", "")
        
        if not content:
            return
        
        if not self._com.in_com:
            log.warning("Not in COM, cannot send message")
            return
        
        try:
            self._com.send_message(content)
            log.info(f"Message sent to COM: {content[:50]}...")
        except Exception as e:
            log.error(f"Failed to send message: {e}")
    
    @property
    def is_connected(self) -> bool:
        return self._ssh.connected and self._com.in_com


# 全局单例
_ssh_session: Optional[SSHSession] = None
_com_session: Optional[COMSession] = None
_sessions_lock = threading.Lock()


def _get_sessions() -> tuple[SSHSession, COMSession]:
    """获取全局会话实例"""
    global _ssh_session, _com_session
    with _sessions_lock:
        if _ssh_session is None:
            _ssh_session = SSHSession()
        if _com_session is None:
            _com_session = COMSession(_ssh_session)
        return _ssh_session, _com_session


# nanobot skill工具函数
def ssh_connect(host: str, username: str, password: str, port: int = 22) -> str:
    """使用paramiko-expect连接SSH服务器
    
    Args:
        host: SSH服务器地址，如 sdf.org
        username: 用户名
        password: 密码
        port: 端口号，默认22
    
    Returns:
        连接结果信息
    """
    try:
        ssh, _ = _get_sessions()
        return ssh.connect(host, username, password, port)
    except Exception as e:
        return f"Error: {e}"


def com_login() -> str:
    """登录SDF.org COM聊天室
    
    需要先通过ssh_connect连接到服务器。
    
    Returns:
        登录结果
    """
    try:
        _, com = _get_sessions()
        return com.login()
    except Exception as e:
        return f"Error: {e}"


def com_send(message: str) -> str:
    """发送消息到COM聊天室
    
    Args:
        message: 消息内容
    
    Returns:
        发送结果
    """
    try:
        _, com = _get_sessions()
        return com.send_message(message)
    except Exception as e:
        return f"Error: {e}"


def com_read(count: int = 10) -> str:
    """读取COM聊天室消息
    
    Args:
        count: 读取消息数量，默认10
    
    Returns:
        消息列表
    """
    try:
        _, com = _get_sessions()
        messages = com.read_messages(count)
        return '\n'.join(f"- {m}" for m in messages) if messages else "No messages"
    except Exception as e:
        return f"Error: {e}"


def com_logout() -> str:
    """退出COM聊天室
    
    Returns:
        退出结果
    """
    try:
        _, com = _get_sessions()
        return com.logout()
    except Exception as e:
        return f"Error: {e}"


def ssh_disconnect() -> str:
    """断开SSH连接
    
    Returns:
        断开结果
    """
    try:
        ssh, com = _get_sessions()
        if com.in_com:
            com.logout()
        return ssh.disconnect()
    except Exception as e:
        return f"Error: {e}"


# nanobot工具定义
TOOLS = [
    {
        "name": "ssh_connect",
        "description": "使用paramiko-expect连接SSH服务器。用于连接到SDF.org或其他SSH服务器。",
        "parameters": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "SSH服务器地址，如 sdf.org"},
                "username": {"type": "string", "description": "用户名"},
                "password": {"type": "string", "description": "密码"},
                "port": {"type": "integer", "description": "端口号，默认22", "default": 22}
            },
            "required": ["host", "username", "password"]
        }
    },
    {
        "name": "com_login",
        "description": "登录SDF.org COM聊天室。需要先通过ssh_connect连接到服务器。",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "com_send",
        "description": "发送消息到COM聊天室。需要先通过com_login登录。",
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "消息内容"}},
            "required": ["message"]
        }
    },
    {
        "name": "com_read",
        "description": "读取COM聊天室消息。返回最新的聊天消息。",
        "parameters": {
            "type": "object",
            "properties": {"count": {"type": "integer", "description": "读取数量，默认10", "default": 10}}
        }
    },
    {
        "name": "com_logout",
        "description": "退出COM聊天室。",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "ssh_disconnect",
        "description": "断开SSH连接。会自动退出COM聊天室。",
        "parameters": {"type": "object", "properties": {}}
    }
]


__version__ = "1.0.0"
__all__ = [
    "SDFShellChannel",
    "SSHSession",
    "COMSession",
    "TerminalEmulator",
    "SDFShellError",
    "ssh_connect",
    "com_login",
    "com_send",
    "com_read",
    "com_logout",
    "ssh_disconnect",
    "TOOLS",
]


if __name__ == "__main__":
    print("SDFShell - SDF.org COM Chat Channel for nanobot")
    print(f"paramiko-expect: {HAS_PARAMIKO_EXPECT}")
    print(f"pyte: {HAS_PYTE}")
    print(f"nanobot: {HAS_NANOBOT}")
