#!/usr/bin/env python3
"""SDFShell - SDF.org COM Chat Channel for nanobot
SDFShell - SDF.org COM聊天室 nanobot 通道

Architecture Design / 架构设计：
- paramiko-expect: Interactive SSH session / 交互式SSH会话
- pyte: Terminal emulator, parse ncurses output / 终端模拟器，解析ncurses输出
- asyncio: Unified async event loop / 统一的异步事件循环
- Message Queue: Support nanobot Queue / Redis / Memory / 消息队列: 支持nanobot Queue / Redis / 内存队列

Message Flow / 消息流向：
- COM Message → pyte Parse → Queue → Agent → Feishu / COM消息 → pyte解析 → Queue → Agent → 飞书
- Feishu Message → Queue → Agent Translate → SSH Send → COM / 飞书消息 → Queue → Agent翻译 → SSH发送 → COM
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
import signal
import sys
import threading
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine

# Python version check / Python版本检查
if sys.version_info < (3, 10):
    raise RuntimeError("SDFShell requires Python 3.10+ / SDFShell需要Python 3.10+")

# Dependency check / 依赖检查
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

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

# nanobot import / nanobot导入
try:
    from nanobot.channels.base import BaseChannel
    from nanobot.bus.queue import Queue as NanobotQueue
    from nanobot.bus.events import Event
    HAS_NANOBOT = True
except ImportError:
    HAS_NANOBOT = False
    NanobotQueue = None
    Event = None
    class BaseChannel:
        """Fallback base class / 回退基类"""
        def __init__(self, config: dict): self.config = config
        async def start(self): pass
        async def stop(self): pass
        async def send(self, message: dict): pass

# Logging configuration / 日志配置
# Default log file path / 默认日志文件路径
DEFAULT_LOG_DIR = os.path.expanduser("~/.nanobot/logs")
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, "sdfshell.log")

def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> logging.Logger:
    """Setup logging system / 配置日志系统
    
    Args:
        level: Log level / 日志级别
        log_file: Log file path, default to ~/.nanobot/logs/sdfshell.log
                  日志文件路径，默认为 ~/.nanobot/logs/sdfshell.log
    
    Returns:
        Configured logger / 配置好的日志器
    """
    logger = logging.getLogger("sdfshell")
    logger.setLevel(level)
    
    if not logger.handlers:
        # Console handler / 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(console_handler)
        
        # File handler / 文件处理器
        if log_file is None:
            log_file = DEFAULT_LOG_FILE
        
        try:
            # Ensure log directory exists / 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d]: %(message)s"
            ))
            logger.addHandler(file_handler)
            logger.info(f"Log file: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to create log file: {e}")
    
    return logger

log = setup_logging()


# ============== Exception System / 异常体系 ==============

class SDFShellError(Exception):
    """SDFShell base exception / SDFShell基础异常"""
    pass

class SSHError(SDFShellError):
    """SSH相关异常"""
    pass

class COMError(SDFShellError):
    """COM相关异常"""
    pass

class ConnectionError(SDFShellError):
    """连接异常"""
    pass

class QueueError(SDFShellError):
    """队列异常"""
    pass

class ParseError(SDFShellError):
    """解析异常"""
    pass


# ============== 全局异常处理 ==============

def global_exception_handler(exc_type, exc_value, exc_tb):
    """全局异常处理器"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    
    log.critical(f"Unhandled exception: {exc_type.__name__}: {exc_value}")
    log.debug("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

sys.excepthook = global_exception_handler


def async_exception_handler(loop, context):
    """异步异常处理器"""
    exception = context.get("exception")
    if exception:
        log.error(f"Async exception: {type(exception).__name__}: {exception}")
    else:
        log.error(f"Async error: {context.get('message', 'Unknown error')}")

def _setup_async_exception_handler():
    """设置异步异常处理器"""
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(async_exception_handler)
    except RuntimeError:
        pass

_setup_async_exception_handler()


# ============== 工具函数 ==============

T = TypeVar('T')

def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        log.warning(f"Retry {attempt + 1}/{max_retries} after {current_delay}s: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator


def strip_ansi(text: str) -> str:
    """移除ANSI控制字符"""
    pattern = re.compile(r'\x1b\[[0-9;]*[mGKH]|\x1b\][^\x07]*\x07|\x1b[()][AB012]')
    return pattern.sub('', text)


def clean_text(text: str) -> str:
    """清理文本"""
    text = strip_ansi(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return ' '.join(text.split()).strip()


# ============== 消息队列抽象 ==============

class MessageQueue(ABC):
    """消息队列抽象基类"""
    
    @abstractmethod
    async def publish(self, channel: str, message: dict) -> None:
        """发布消息"""
        pass
    
    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        """订阅消息"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭队列"""
        pass


class MemoryQueue(MessageQueue):
    """内存消息队列"""
    
    def __init__(self, maxsize: int = 1000):
        self._queues: dict[str, asyncio.Queue] = {}
        self._maxsize = maxsize
        self._lock = asyncio.Lock()
    
    async def _get_queue(self, channel: str) -> asyncio.Queue:
        async with self._lock:
            if channel not in self._queues:
                self._queues[channel] = asyncio.Queue(maxsize=self._maxsize)
            return self._queues[channel]
    
    async def publish(self, channel: str, message: dict) -> None:
        queue = await self._get_queue(channel)
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            log.warning(f"Queue {channel} is full, dropping message")
    
    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        queue = await self._get_queue(channel)
        while True:
            message = await queue.get()
            yield message
    
    async def close(self) -> None:
        self._queues.clear()


class RedisQueue(MessageQueue):
    """Redis消息队列"""
    
    def __init__(self, url: str = "redis://localhost:6379/0"):
        if not HAS_REDIS:
            raise QueueError("redis not installed: pip install redis")
        self._url = url
        self._client: Optional[redis.Redis] = None
    
    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._url)
        return self._client
    
    async def publish(self, channel: str, message: dict) -> None:
        import json
        client = await self._get_client()
        await client.publish(f"sdfshell:{channel}", json.dumps(message))
    
    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        import json
        client = await self._get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"sdfshell:{channel}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError:
                    continue
    
    async def close(self) -> None:
        if self._client:
            await self._client.close()


class NanobotQueueAdapter(MessageQueue):
    """nanobot queue adapter - Integrates with nanobot's message bus
    
    Uses nanobot.bus.Queue for event-driven message passing
    """
    
    def __init__(self):
        if not HAS_NANOBOT or NanobotQueue is None:
            raise QueueError("nanobot not available")
        self._queue = NanobotQueue()
        self._subscribers: dict[str, list] = {}
        log.info("[Queue] NanobotQueueAdapter initialized")
    
    async def publish(self, channel: str, message: dict) -> None:
        """Publish message to nanobot message bus"""
        try:
            if Event:
                event = Event(
                    type="sdfshell_message",
                    channel=channel,
                    data=message,
                    timestamp=time.time()
                )
                await self._queue.publish(event)
                log.debug(f"[Queue] Published to {channel}: {message.get('type', 'unknown')}")
            else:
                log.warning("[Queue] Event class not available, message not published")
        except Exception as e:
            log.error(f"[Queue] Publish error: {e}")
    
    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        """Subscribe to messages from nanobot message bus"""
        async for event in self._queue.subscribe():
            try:
                # Filter by channel if specified
                if hasattr(event, 'channel') and event.channel == channel:
                    yield event.data if hasattr(event, 'data') else {}
                elif not hasattr(event, 'channel'):
                    # No channel filter, yield all
                    yield event.data if hasattr(event, 'data') else {}
            except Exception as e:
                log.error(f"[Queue] Subscribe error: {e}")
                continue
    
    async def close(self) -> None:
        """Close the queue"""
        self._subscribers.clear()
        log.info("[Queue] NanobotQueueAdapter closed")


def create_queue(queue_type: str = "memory", **kwargs) -> MessageQueue:
    """创建消息队列"""
    if queue_type == "redis":
        return RedisQueue(**kwargs)
    elif queue_type == "nanobot" and HAS_NANOBOT:
        return NanobotQueueAdapter()
    else:
        return MemoryQueue(**kwargs)


# ============== 终端模拟器 ==============

class TerminalEmulator:
    """pyte terminal emulator - Parse ncurses output for COM chat messages
    
    Event-driven message extraction with deduplication
    Output: Only username, message content, and timestamp (converted to Beijing time)
    """
    
    # Beijing timezone (UTC+8)
    BEIJING_TZ = timezone(timedelta(hours=8))
    
    def __init__(self, cols: int = 80, rows: int = 24):
        if not HAS_PYTE:
            raise SDFShellError("pyte not installed: pip install pyte")
        self.cols = cols
        self.rows = rows
        self._seen_messages: set[str] = set()  # Deduplication
        self._max_seen = 1000  # Limit memory
        self._reset_screen()
    
    def _reset_screen(self) -> None:
        self.screen = pyte.Screen(self.cols, self.rows)
        self.stream = pyte.Stream(self.screen)
    
    def feed(self, data: str) -> None:
        try:
            self.stream.feed(data)
        except Exception as e:
            log.error(f"Terminal feed error: {e}")
    
    def get_display(self) -> str:
        lines = [clean_text(line) for line in self.screen.display]
        return '\n'.join(line for line in lines if line)
    
    def _extract_timestamp(self, line: str) -> str | None:
        """Extract timestamp from line and convert to Beijing time
        
        Supports formats:
        - [HH:MM] or [HH:MM:SS]
        - HH:MM or HH:MM:SS
        - (HH:MM) or (HH:MM:SS)
        
        Returns Beijing time string (UTC+8)
        """
        time_patterns = [
            r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]',  # [HH:MM] or [HH:MM:SS]
            r'\((\d{1,2}:\d{2}(?::\d{2})?)\)',  # (HH:MM) or (HH:MM:SS)
            r'(\d{1,2}:\d{2}(?::\d{2})?)',      # HH:MM or HH:MM:SS
        ]
        for pattern in time_patterns:
            match = re.search(pattern, line)
            if match:
                time_str = match.group(1)
                try:
                    # Parse time and convert to Beijing time
                    now = datetime.now(self.BEIJING_TZ)
                    if ':' in time_str:
                        parts = time_str.split(':')
                        hour = int(parts[0])
                        minute = int(parts[1])
                        second = int(parts[2]) if len(parts) > 2 else 0
                        
                        # Create datetime with today's date and parsed time
                        msg_time = datetime(
                            now.year, now.month, now.day,
                            hour, minute, second,
                            tzinfo=self.BEIJING_TZ
                        )
                        return msg_time.strftime("%H:%M:%S")
                except (ValueError, IndexError):
                    pass
                return time_str
        return None
    
    def get_messages(self) -> list[dict]:
        """Extract user chat messages with deduplication
        
        Returns list of dicts with ONLY:
        - username: str
        - content: str
        - timestamp: str | None (Beijing time, UTC+8)
        
        All other terminal artifacts are stripped by pyte
        """
        messages = []
        system_keywords = frozenset([
            'welcome', 'connected', 'disconnected', 'system', 'server',
            'online', 'users', 'status', 'help', 'error', 'warning',
            'has joined', 'has left', 'entered', 'exited', '***'
        ])
        system_users = frozenset(['system', 'server', 'bot', 'admin', 'root', '***'])
        
        for line in self.screen.display:
            line = clean_text(line)
            if len(line) < 3:
                continue
            
            line_lower = line.lower()
            if any(kw in line_lower for kw in system_keywords):
                continue
            
            # Extract timestamp first (converted to Beijing time)
            timestamp = self._extract_timestamp(line)
            
            # Remove timestamp from line for user/message parsing
            line_no_time = re.sub(r'[\[\(]?\d{1,2}:\d{2}(?::\d{2})?[\]\)]?', '', line).strip()
            
            # Match COM chat message formats
            patterns = [
                r'^[<\[]?(\w+)[>\]:]\s*(.+)$',  # user: msg or <user> msg
                r'^(\w+)\s*>\s*(.+)$',           # user > msg
                r'^\[(\w+)\]\s*(.+)$',           # [user] msg
                r'^(\w+)\s+\|\s*(.+)$',          # user | msg (SDF format)
                r'^(\w+)\s{2,}(.+)$',            # user  msg (multi-space)
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line_no_time)
                if match:
                    user, content = match.group(1).strip(), match.group(2).strip()
                    if content and user.lower() not in system_users:
                        msg_key = f"{user}:{content}"
                        # Deduplication
                        if msg_key not in self._seen_messages:
                            self._seen_messages.add(msg_key)
                            # Return ONLY username, content, timestamp (Beijing time)
                            messages.append({
                                "username": user,
                                "content": content,
                                "timestamp": timestamp
                            })
                            # Limit memory
                            if len(self._seen_messages) > self._max_seen:
                                self._seen_messages = set(list(self._seen_messages)[-500:])
                    break
        
        return messages
    
    def reset(self) -> None:
        self._reset_screen()
        self._seen_messages.clear()


# ============== SSH会话 ==============

class SSHSession:
    """paramiko-expect SSH会话管理 - 支持重连"""
    
    def __init__(self, reconnect_attempts: int = 3, reconnect_delay: float = 5.0):
        if not HAS_PARAMIKO_EXPECT:
            raise SSHError("paramiko-expect not installed: pip install paramiko-expect")
        
        self.client: Optional[paramiko.SSHClient] = None
        self.interact: Optional[SSHClientInteraction] = None
        self.terminal: Optional[TerminalEmulator] = None
        
        self._connected = False
        self._lock = asyncio.Lock()
        self._reconnect_attempts = reconnect_attempts
        self._reconnect_delay = reconnect_delay
        
        # 连接参数（用于重连）
        self._host: str = ""
        self._port: int = 22
        self._username: str = ""
        self._password: str = ""
    
    @property
    def connected(self) -> bool:
        if not self._connected or self.client is None:
            return False
        try:
            transport = self.client.get_transport()
            return transport is not None and transport.is_active()
        except:
            return False
    
    async def connect(self, host: str, username: str, password: str, port: int = 22) -> str:
        """连接SSH服务器"""
        async with self._lock:
            try:
                # 保存连接参数
                self._host, self._port = host, port
                self._username, self._password = username, password
                
                log.info(f"[SSH] Connecting to {host}:{port} as {username}...")
                
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                log.debug(f"[SSH] Creating SSH connection with timeout=30s")
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        timeout=30,
                        banner_timeout=30,
                        look_for_keys=False,
                        allow_agent=False
                    )
                )
                
                self.interact = SSHClientInteraction(self.client, timeout=60, display=False)
                self.terminal = TerminalEmulator()
                self._connected = True
                
                log.info(f"[SSH] ✓ Connected successfully to {host}:{port}")
                log.debug(f"[SSH] Transport active: {self.client.get_transport().is_active() if self.client.get_transport() else False}")
                return f"Connected to {host}:{port}"
                
            except Exception as e:
                self._connected = False
                log.error(f"[SSH] ✗ Connection failed: {type(e).__name__}: {e}")
                log.debug(f"[SSH] Connection parameters: host={host}, port={port}, username={username}")
                raise SSHError(f"Connection failed: {e}") from e
    
    async def reconnect(self) -> str:
        """重新连接"""
        if not self._host:
            raise SSHError("No previous connection to reconnect")
        
        log.info(f"[SSH] Reconnecting to {self._host}:{self._port}...")
        log.debug(f"[SSH] Reconnect config: attempts={self._reconnect_attempts}, delay={self._reconnect_delay}s")
        
        for attempt in range(self._reconnect_attempts):
            log.info(f"[SSH] Reconnect attempt {attempt + 1}/{self._reconnect_attempts}")
            try:
                await self.disconnect()
                await asyncio.sleep(self._reconnect_delay)
                result = await self.connect(
                    self._host, self._username, self._password, self._port
                )
                log.info(f"[SSH] ✓ Reconnected successfully on attempt {attempt + 1}")
                return result
            except Exception as e:
                log.warning(f"[SSH] ✗ Reconnect attempt {attempt + 1} failed: {type(e).__name__}: {e}")
        
        log.error(f"[SSH] All {self._reconnect_attempts} reconnection attempts failed")
        raise SSHError(f"Failed to reconnect after {self._reconnect_attempts} attempts")
    
    async def disconnect(self) -> str:
        """断开连接"""
        async with self._lock:
            if not self._connected:
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
                raise SSHError(f"Disconnect failed: {e}") from e
    
    async def ensure_connected(self) -> None:
        """确保连接状态"""
        if not self.connected:
            await self.reconnect()
    
    async def send_command(self, command: str, expect: str = "$", timeout: float = 5.0) -> str:
        """发送命令"""
        await self.ensure_connected()
        
        async with self._lock:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.interact.send(command)
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.interact.expect(expect, timeout=timeout)
                )
                
                output = self.interact.current_output
                if self.terminal and output:
                    self.terminal.feed(output)
                    return self.terminal.get_display()
                
                return clean_text(output)
                
            except Exception as e:
                log.error(f"Send command error: {e}")
                if "not open" in str(e).lower() or "closed" in str(e).lower():
                    self._connected = False
                    await self.reconnect()
                    return await self.send_command(command, expect, timeout)
                raise SSHError(f"Command failed: {e}") from e
    
    async def send_and_read(self, command: str, wait: float = 1.0) -> tuple[str, list[str]]:
        """发送命令并读取消息"""
        await self.ensure_connected()
        
        async with self._lock:
            try:
                self.interact.send(command)
                await asyncio.sleep(wait)
                
                output = ""
                while self.interact.channel.recv_ready():
                    output += self.interact.channel.recv(4096).decode('utf-8', errors='replace')
                
                if self.terminal and output:
                    self.terminal.feed(output)
                    return self.terminal.get_display(), self.terminal.get_messages()
                
                return clean_text(output), []
                
            except Exception as e:
                log.error(f"Send and read error: {e}")
                if "not open" in str(e).lower() or "closed" in str(e).lower():
                    self._connected = False
                    await self.reconnect()
                    return await self.send_and_read(command, wait)
                raise SSHError(f"Read failed: {e}") from e


# ============== COM会话 ==============

class COMSession:
    """COM聊天室会话"""
    
    def __init__(self, ssh: SSHSession):
        self.ssh = ssh
        self._in_com = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False
        self._message_callback: Optional[Callable[[list[str]], None]] = None
        self._monitor_interval = 3.0
    
    @property
    def in_com(self) -> bool:
        return self._in_com
    
    async def login(self) -> str:
        """登录COM"""
        if not self.ssh.connected:
            log.error("[COM] Cannot login: SSH not connected")
            raise COMError("SSH not connected")
        
        try:
            log.info("[COM] Logging into COM chat room...")
            display, _ = await self.ssh.send_and_read("com", wait=2.0)
            
            log.debug(f"[COM] Login response preview: {display[:200]}...")
            
            if ">" in display or "COM" in display.upper():
                self._in_com = True
                log.info("[COM] ✓ Logged into COM successfully")
                return f"Logged into COM\n{display}"
            
            log.warning("[COM] Login status unclear, check response")
            return f"Login may have failed\n{display}"
            
        except Exception as e:
            log.error(f"[COM] ✗ Login failed: {type(e).__name__}: {e}")
            raise COMError(f"Login failed: {e}") from e
    
    async def logout(self) -> str:
        """退出COM"""
        if not self._in_com:
            log.debug("[COM] Not in COM, nothing to logout")
            return "Not in COM"
        
        log.info("[COM] Logging out of COM...")
        self._monitoring = False
        
        try:
            await self.ssh.send_command("/q", expect="$", timeout=2.0)
            self._in_com = False
            log.info("[COM] ✓ Logged out of COM successfully")
            return "Logged out of COM"
            
        except Exception as e:
            log.error(f"[COM] ✗ Logout failed: {type(e).__name__}: {e}")
            raise COMError(f"Logout failed: {e}") from e
    
    async def send_message(self, message: str) -> str:
        """发送消息"""
        if not self._in_com:
            log.error("[COM] Cannot send: not in COM")
            raise COMError("Not in COM")
        
        try:
            log.info(f"[COM] Sending message: {message[:50]}...")
            await self.ssh.send_and_read(message, wait=0.5)
            log.info(f"[COM] ✓ Message sent successfully")
            return f"Sent: {message}"
            
        except Exception as e:
            log.error(f"[COM] ✗ Send failed: {type(e).__name__}: {e}")
            raise COMError(f"Send failed: {e}") from e
    
    async def read_messages(self, count: int = 10) -> list[dict]:
        """Read messages from COM chat
        
        Returns list of dicts with: username, content, timestamp
        """
        if not self._in_com:
            log.error("[COM] Cannot read: not in COM")
            raise COMError("Not in COM")
        
        try:
            log.debug(f"[COM] Reading up to {count} messages...")
            _, messages = await self.ssh.send_and_read("", wait=0.5)
            result = messages[-count:] if messages else []
            log.debug(f"[COM] Read {len(result)} messages")
            return result
            
        except Exception as e:
            log.error(f"[COM] ✗ Read failed: {type(e).__name__}: {e}")
            raise COMError(f"Read failed: {e}") from e
    
    async def start_monitor(self, callback: Callable[[list[str]], None], interval: float = 3.0) -> str:
        """Start message monitoring - Event-driven polling
        
        Monitors COM chat room for new messages and triggers callback
        """
        if self._monitoring:
            log.warning("[COM] Monitor already running")
            return "Already monitoring"
        
        self._message_callback = callback
        self._monitor_interval = interval
        self._monitoring = True
        
        log.info(f"[COM] Starting message monitor (interval: {interval}s)")
        
        async def _monitor_loop():
            """Event-driven monitoring loop"""
            consecutive_errors = 0
            max_errors = 5
            
            while self._monitoring and self._in_com:
                try:
                    # Read new messages
                    messages = await self.read_messages(count=10)
                    
                    if messages and self._message_callback:
                        # Trigger callback with new messages
                        self._message_callback(messages)
                        log.debug(f"[COM] Processed {len(messages)} new messages")
                    
                    consecutive_errors = 0  # Reset error counter on success
                    
                except Exception as e:
                    consecutive_errors += 1
                    log.error(f"[COM] Monitor error ({consecutive_errors}/{max_errors}): {e}")
                    
                    if consecutive_errors >= max_errors:
                        log.error("[COM] Too many errors, stopping monitor")
                        self._monitoring = False
                        break
                    
                    # Wait longer after error
                    await asyncio.sleep(self._monitor_interval * 2)
                    continue
                
                await asyncio.sleep(self._monitor_interval)
            
            log.info("[COM] Monitor loop ended")
        
        self._monitor_task = asyncio.create_task(_monitor_loop())
        log.info("[COM] ✓ Message monitor started")
        return "Monitor started"
    
    async def stop_monitor(self) -> str:
        """Stop message monitoring"""
        if not self._monitoring:
            return "Not monitoring"
        
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        log.info("[COM] ✓ Message monitor stopped")
        return "Monitor stopped"


# ============== 配置管理 ==============

CONFIG_FILE = os.path.expanduser("~/.nanobot/skills/sdfshell/config.json")

def load_config() -> dict:
    """加载配置
    
    Load configuration from file
    从文件加载配置
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load config: {e}")
    return {}

def save_config(config: dict) -> bool:
    """保存配置
    
    Save configuration to file
    保存配置到文件
    """
    try:
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log.info(f"Config saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        log.error(f"Failed to save config: {e}")
        return False

def set_config(host: str = None, username: str = None, password: str = None, port: int = 22) -> str:
    """设置配置 (对话配置入口)
    
    Set configuration via conversation
    通过对话设置配置
    
    Args:
        host: SSH host address / SSH主机地址
        username: SSH username / SSH用户名
        password: SSH password / SSH密码
        port: SSH port / SSH端口
    
    Returns:
        Configuration result message
        配置结果消息
    """
    config = load_config()
    
    if host:
        config["host"] = host
    if username:
        config["username"] = username
    if password:
        config["password"] = password
    if port:
        config["port"] = port
    
    if save_config(config):
        masked_password = "****" if config.get("password") else "not set"
        return f"""✅ Configuration saved:
• Host: {config.get('host', 'not set')}
• Port: {config.get('port', 22)}
• Username: {config.get('username', 'not set')}
• Password: {masked_password}

Ready to connect! Say "Connect to SDF" to start."""
    else:
        return "❌ Failed to save configuration. Please check permissions."

def get_config_status() -> str:
    """获取配置状态
    
    Get current configuration status
    获取当前配置状态
    """
    config = load_config()
    
    if not config:
        return """⚠️ SDFShell is not configured yet!

Please configure your credentials:
• Say "Set SDF host to sdf.org"
• Say "Set SDF username to YOUR_USERNAME"
• Say "Set SDF password to YOUR_PASSWORD"
Or: "Configure SDF with username YOUR_NAME and password YOUR_PASS" """
    
    masked_password = "****" if config.get("password") else "not set"
    return f"""📋 Current Configuration:
• Host: {config.get('host', 'not set')}
• Port: {config.get('port', 22)}
• Username: {config.get('username', 'not set')}
• Password: {masked_password}

{'✅ Ready to connect!' if config.get('host') and config.get('username') and config.get('password') else '⚠️ Please complete configuration.'} """


# ============== SDFShell Channel ==============

class SDFShellChannel(BaseChannel):
    """SDFShell nanobot通道
    
    配置示例:
        channels:
          sdfshell:
            enabled: true
            host: sdf.org
            port: 22
            username: your_username
            password: your_password
            monitor_interval: 3.0
            queue_type: memory  # memory / redis / nanobot
            redis_url: redis://localhost:6379/0
            reconnect_attempts: 3
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Try to load from config file first / 首先尝试从配置文件加载
        saved_config = load_config()
        
        # 连接配置 (priority: config param > saved config > env var > default)
        # 连接配置 (优先级: 配置参数 > 保存的配置 > 环境变量 > 默认值)
        self.host = config.get("host") or saved_config.get("host") or os.environ.get("SDF_HOST", "sdf.org")
        self.port = config.get("port") or saved_config.get("port") or int(os.environ.get("SDF_PORT", "22"))
        self.username = config.get("username") or saved_config.get("username") or os.environ.get("SDF_USERNAME", "")
        self.password = config.get("password") or saved_config.get("password") or os.environ.get("SDF_PASSWORD", "")
        self.monitor_interval = config.get("monitor_interval", 3.0)
        
        # 队列配置 - 默认使用nanobot Queue
        self.queue_type = config.get("queue_type", "nanobot" if HAS_NANOBOT else "memory")
        self.redis_url = config.get("redis_url", "redis://localhost:6379/0")
        
        # 重连配置
        self.reconnect_attempts = config.get("reconnect_attempts", 3)
        
        # 组件
        self._ssh = SSHSession(reconnect_attempts=self.reconnect_attempts)
        self._com = COMSession(self._ssh)
        self._queue: Optional[MessageQueue] = None
        
        self._running = False
        self._channel_name = "sdfshell"
        
        # Log configuration status / 记录配置状态
        if not self.username or not self.password:
            log.warning("[SDFShell] Configuration incomplete - username/password not set")
            log.info("[SDFShell] Please configure using: set_config(username='...', password='...')")
    
    async def start(self) -> None:
        """启动通道"""
        log.info(f"Starting SDFShell channel: {self.host}")
        
        # Check configuration / 检查配置
        if not self.username or not self.password:
            log.warning("[SDFShell] Cannot start: username/password not configured")
            log.info("[SDFShell] Please configure first:")
            log.info("  - Say 'Set SDF username to YOUR_NAME'")
            log.info("  - Say 'Set SDF password to YOUR_PASS'")
            log.info("  - Or add to ~/.nanobot/config.yaml")
            self._running = True  # Mark as running but not connected
            return
        
        # 创建消息队列
        try:
            if self.queue_type == "redis":
                self._queue = RedisQueue(self.redis_url)
            elif self.queue_type == "nanobot" and HAS_NANOBOT:
                self._queue = NanobotQueueAdapter()
            else:
                self._queue = MemoryQueue()
            log.info(f"Using {self.queue_type} queue")
        except Exception as e:
            log.warning(f"Failed to create {self.queue_type} queue, falling back to memory: {e}")
            self._queue = MemoryQueue()
        
        # 连接SSH
        await self._ssh.connect(self.host, self.username, self.password, self.port)
        await self._com.login()
        
        # 启动消息监控
        await self._com.start_monitor(
            callback=self._on_com_message,
            interval=self.monitor_interval
        )
        
        self._running = True
        log.info("SDFShell channel started")
    
    async def stop(self) -> None:
        """停止通道"""
        log.info("Stopping SDFShell channel")
        
        self._running = False
        
        await self._com.stop_monitor()
        await self._com.logout()
        await self._ssh.disconnect()
        
        if self._queue:
            await self._queue.close()
        
        log.info("SDFShell channel stopped")
    
    def _on_com_message(self, messages: list[dict]) -> None:
        """Handle COM message callback - Route to nanobot via message queue
        
        Event-driven message processing:
        1. Messages already parsed by pyte (username, content, timestamp only)
        2. Add metadata for translation/summarization
        3. Publish to nanobot message bus
        
        Input: list of dicts with {username, content, timestamp}
        """
        if not messages:
            return
        
        log.info(f"[SDFShell] Processing {len(messages)} COM messages")
        
        # Format messages for nanobot - already clean from pyte
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "username": msg.get("username", "unknown"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp"),
                "source": "sdf_com_chat",
                "needs_translation": True,
                "needs_summary": len(messages) > 3
            })
        
        # Create event data
        event_data = {
            "type": "com_messages",
            "channel": self._channel_name,
            "messages": formatted_messages,
            "count": len(messages),
            "timestamp": time.time(),
            "instruction": (
                "Please: 1) Translate to user's language, "
                "2) Summarize if multiple messages, "
                "3) Add helpful context/reminders when appropriate"
            )
        }
        
        # Publish to queue asynchronously
        if self._queue:
            try:
                asyncio.create_task(self._queue.publish(self._channel_name, event_data))
                log.debug(f"[SDFShell] Queued {len(messages)} messages for nanobot")
            except Exception as e:
                log.error(f"[SDFShell] Failed to queue messages: {e}")
        else:
            log.warning("[SDFShell] No queue available, messages not forwarded")
    
    async def receive(self) -> AsyncGenerator[dict, None]:
        """接收消息（nanobot调用）"""
        async for message in self._queue.subscribe(self._channel_name):
            if not self._running:
                break
            yield message
    
    async def send(self, message: dict) -> None:
        """发送消息（nanobot调用）"""
        content = message.get("content", "")
        if not content:
            return
        
        if not self._com.in_com:
            log.warning("Not in COM, cannot send message")
            return
        
        try:
            await self._com.send_message(content)
            log.info(f"Message sent to COM: {content[:50]}...")
        except Exception as e:
            log.error(f"Failed to send message: {e}")
    
    @property
    def is_connected(self) -> bool:
        return self._ssh.connected and self._com.in_com


# ============== 消息路由 ==============

class MessageType(Enum):
    """消息类型枚举"""
    COM_CHAT = auto()      # com: 前缀 - 发送到COM聊天室
    SSH_COMMAND = auto()   # sh: 前缀 - 执行SSH命令
    NORMAL = auto()        # 无前缀 - 普通对话


@dataclass
class RoutedMessage:
    """路由后的消息"""
    type: MessageType
    content: str
    original: str


def route_message(text: str) -> RoutedMessage:
    """路由消息 - 根据前缀判断消息类型
    
    Rules / 规则:
    - "com:" prefix → Send to COM chat room (auto-translate to English)
      "com:" 前缀 → 发送到COM聊天室（自动翻译成英文）
    - "sh:" prefix → Execute SSH/SDF command
      "sh:" 前缀 → 执行SSH/SDF命令
    - No prefix → Normal conversation
      无前缀 → 普通对话
    
    Args:
        text: Input text / 输入文本
    
    Returns:
        RoutedMessage with type and content
        包含类型和内容的路由消息
    """
    text = text.strip()
    
    if text.lower().startswith("com:"):
        content = text[4:].strip()
        log.debug(f"Route: COM_CHAT - {content[:50]}...")
        return RoutedMessage(MessageType.COM_CHAT, content, text)
    
    elif text.lower().startswith("sh:"):
        content = text[3:].strip()
        log.debug(f"Route: SSH_COMMAND - {content[:50]}...")
        return RoutedMessage(MessageType.SSH_COMMAND, content, text)
    
    else:
        log.debug(f"Route: NORMAL - {text[:50]}...")
        return RoutedMessage(MessageType.NORMAL, text, text)


# ============== 全局实例 ==============

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


# ============== nanobot工具函数 ==============

def ssh_connect(host: str = None, username: str = None, password: str = None, port: int = 22) -> str:
    """连接SSH服务器
    
    如果参数未提供，从配置文件读取
    """
    try:
        # 如果参数未提供，从配置文件读取
        if not host or not username or not password:
            config = load_config()
            host = host or config.get("host", "sdf.org")
            username = username or config.get("username")
            password = password or config.get("password")
            port = config.get("port", 22)
        
        if not username or not password:
            return "Error: No credentials configured. Run set_config() first."
        
        ssh, _ = _get_sessions()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ssh.connect(host, username, password, port))
        loop.close()
        return result
    except Exception as e:
        return f"Error: {e}"


def com_login() -> str:
    """登录COM"""
    try:
        _, com = _get_sessions()
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(com.login())
        loop.close()
        return result
    except Exception as e:
        return f"Error: {e}"


def com_send(message: str) -> str:
    """发送消息"""
    try:
        _, com = _get_sessions()
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(com.send_message(message))
        loop.close()
        return result
    except Exception as e:
        return f"Error: {e}"


def com_read(count: int = 10) -> str:
    """读取消息"""
    try:
        _, com = _get_sessions()
        loop = asyncio.new_event_loop()
        messages = loop.run_until_complete(com.read_messages(count))
        loop.close()
        return '\n'.join(f"- {m}" for m in messages) if messages else "No messages"
    except Exception as e:
        return f"Error: {e}"


def com_logout() -> str:
    """退出COM"""
    try:
        _, com = _get_sessions()
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(com.logout())
        loop.close()
        return result
    except Exception as e:
        return f"Error: {e}"


def ssh_disconnect() -> str:
    """断开SSH"""
    try:
        ssh, com = _get_sessions()
        loop = asyncio.new_event_loop()
        if com.in_com:
            loop.run_until_complete(com.logout())
        result = loop.run_until_complete(ssh.disconnect())
        loop.close()
        return result
    except Exception as e:
        return f"Error: {e}"


def ssh_exec(command: str) -> str:
    """执行SSH命令 (sh: 前缀路由)
    
    Execute SSH/SDF command via sh: prefix routing
    通过 sh: 前缀路由执行SSH/SDF命令
    
    Args:
        command: SSH command to execute / 要执行的SSH命令
    
    Returns:
        Command output / 命令输出
    """
    try:
        ssh, com = _get_sessions()
        loop = asyncio.new_event_loop()
        
        # If in COM, need to exit first / 如果在COM中，需要先退出
        was_in_com = com.in_com
        if was_in_com:
            log.debug("Temporarily exiting COM for SSH command")
            loop.run_until_complete(com.logout())
        
        result = loop.run_until_complete(ssh.send_command(command, expect="$", timeout=10.0))
        
        # Re-enter COM if was in COM / 如果之前在COM中，重新进入
        if was_in_com:
            log.debug("Re-entering COM after SSH command")
            loop.run_until_complete(com.login())
        
        loop.close()
        log.info(f"SSH command executed: {command[:50]}...")
        return result
    except Exception as e:
        log.error(f"SSH command failed: {e}")
        return f"Error: {e}"


def process_message(text: str) -> str:
    """处理消息 - 根据前缀路由到不同处理方式
    
    Process message with prefix routing
    根据前缀路由处理消息
    
    This is the main entry point for nanobot to process user messages.
    这是nanobot处理用户消息的主入口。
    
    Args:
        text: User input text / 用户输入文本
    
    Returns:
        Processing result / 处理结果
    """
    try:
        routed = route_message(text)
        
        if routed.type == MessageType.COM_CHAT:
            # Send to COM chat / 发送到COM聊天室
            _, com = _get_sessions()
            if not com.in_com:
                return "Error: Not in COM. Use com_login first."
            
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(com.send_message(routed.content))
            loop.close()
            return f"[COM] {result}"
        
        elif routed.type == MessageType.SSH_COMMAND:
            # Execute SSH command / 执行SSH命令
            return ssh_exec(routed.content)
        
        else:
            # Normal conversation - return hint / 普通对话 - 返回提示
            return (
                "Normal message (no prefix). "
                "Use 'com:' to send to COM chat, 'sh:' to execute SSH command."
            )
    
    except Exception as e:
        log.error(f"Process message error: {e}")
        return f"Error: {e}"


# ============== 安装后欢迎消息 ==============

def get_welcome_message() -> str:
    """获取安装后欢迎消息
    
    Get post-installation welcome message for user guidance
    获取安装后欢迎消息用于用户指导
    """
    return """🎉 SDFShell installed successfully!

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

Ask me anything about SDF.org!"""


def format_com_messages(messages: list[dict], user_language: str = "auto") -> str:
    """格式化COM消息供用户阅读
    
    Format COM messages for user reading with translation hints
    格式化COM消息供用户阅读并附带翻译提示
    
    Args:
        messages: List of message dicts from COM
        user_language: Target language for translation (auto-detect if "auto")
    
    Returns:
        Formatted message string for display
    """
    if not messages:
        return "No messages"
    
    lines = ["📨 [COM Message]:", ""]
    
    for msg in messages:
        raw = msg.get("raw", "")
        lines.append(f"  {raw}")
    
    # Add instruction for nanobot
    if len(messages) > 3:
        lines.extend([
            "",
            "---",
            f"💡 Summary needed: {len(messages)} messages",
            f"🔄 Please translate to {user_language if user_language != 'auto' else 'user language'}"
        ])
    else:
        lines.extend([
            "",
            f"🔄 Please translate to {user_language if user_language != 'auto' else 'user language'}"
        ])
    
    return "\n".join(lines)


# ============== TOOLS定义 ==============

TOOLS = [
    {
        "name": "ssh_connect",
        "description": "连接SSH服务器 / Connect to SSH server",
        "parameters": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "主机地址 / Host address"},
                "username": {"type": "string", "description": "用户名 / Username"},
                "password": {"type": "string", "description": "密码 / Password"},
                "port": {"type": "integer", "description": "端口 / Port", "default": 22}
            },
            "required": ["host", "username", "password"]
        }
    },
    {
        "name": "com_login",
        "description": "登录COM聊天室 / Login to COM chat room",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "com_send",
        "description": "发送消息到COM / Send message to COM",
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "消息内容 / Message content"}},
            "required": ["message"]
        }
    },
    {
        "name": "com_read",
        "description": "读取COM消息 / Read COM messages",
        "parameters": {
            "type": "object",
            "properties": {"count": {"type": "integer", "description": "数量 / Count", "default": 10}}
        }
    },
    {
        "name": "com_logout",
        "description": "退出COM / Logout from COM",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "ssh_disconnect",
        "description": "断开SSH连接 / Disconnect SSH",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "ssh_exec",
        "description": "执行SSH命令 (sh:前缀路由) / Execute SSH command (sh: prefix routing)",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "SSH命令 / SSH command"}},
            "required": ["command"]
        }
    },
    {
        "name": "process_message",
        "description": "处理消息 - 根据前缀路由 (com:/sh:) / Process message with prefix routing",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "用户输入 / User input"}},
            "required": ["text"]
        }
    },
    {
        "name": "get_welcome_message",
        "description": "获取安装后欢迎消息 / Get post-installation welcome message",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "format_com_messages",
        "description": "格式化COM消息供用户阅读 / Format COM messages for user reading",
        "parameters": {
            "type": "object",
            "properties": {
                "messages": {"type": "array", "description": "消息列表 / Message list"},
                "user_language": {"type": "string", "description": "目标语言 / Target language", "default": "auto"}
            },
            "required": ["messages"]
        }
    },
    {
        "name": "set_config",
        "description": "设置SDF配置 (对话配置) / Set SDF configuration via conversation",
        "parameters": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "主机地址 / Host address"},
                "username": {"type": "string", "description": "用户名 / Username"},
                "password": {"type": "string", "description": "密码 / Password"},
                "port": {"type": "integer", "description": "端口 / Port", "default": 22}
            }
        }
    },
    {
        "name": "get_config_status",
        "description": "获取配置状态 / Get current configuration status",
        "parameters": {"type": "object", "properties": {}}
    }
]


__version__ = "2.3.0"
__all__ = [
    "SDFShellChannel",
    "SSHSession",
    "COMSession",
    "TerminalEmulator",
    "MessageQueue",
    "MemoryQueue",
    "RedisQueue",
    "SDFShellError",
    "MessageType",
    "RoutedMessage",
    "route_message",
    "ssh_connect",
    "com_login",
    "com_send",
    "com_read",
    "com_logout",
    "ssh_disconnect",
    "ssh_exec",
    "process_message",
    "get_welcome_message",
    "format_com_messages",
    "set_config",
    "get_config_status",
    "load_config",
    "save_config",
    "TOOLS",
    "DEFAULT_LOG_FILE",
]


if __name__ == "__main__":
    print(f"SDFShell v{__version__} - SDF.org COM Chat Channel for nanobot")
    print(f"Log file: {DEFAULT_LOG_FILE}")
    print(f"paramiko-expect: {HAS_PARAMIKO_EXPECT}")
    print(f"pyte: {HAS_PYTE}")
    print(f"redis: {HAS_REDIS}")
    print(f"nanobot: {HAS_NANOBOT}")
    print()
    print("=== Welcome Message ===")
    print(get_welcome_message())
