#!/usr/bin/env python3
"""SDFShell - SDF.org COM Chat Channel for nanobot

架构设计：
- paramiko-expect: 交互式SSH会话
- pyte: 终端模拟器，解析ncurses输出
- asyncio: 统一的异步事件循环
- 消息队列: 支持nanobot Queue / Redis / 内存队列

消息流向：
- COM消息 → pyte解析 → Queue → Agent → 飞书
- 飞书消息 → Queue → Agent翻译 → SSH发送 → COM
"""

from __future__ import annotations

import asyncio
import functools
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
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine

# Python版本检查
if sys.version_info < (3, 10):
    raise RuntimeError("SDFShell requires Python 3.10+")

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

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

# nanobot导入
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
        def __init__(self, config: dict): self.config = config
        async def start(self): pass
        async def stop(self): pass
        async def send(self, message: dict): pass

# 日志配置
def setup_logging(level: int = logging.INFO, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger("sdfshell")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(handler)
        if log_file:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ))
            logger.addHandler(fh)
    return logger

log = setup_logging()


# ============== 异常体系 ==============

class SDFShellError(Exception):
    """SDFShell基础异常"""
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

# 设置异步异常处理器
try:
    asyncio.get_event_loop().set_exception_handler(async_exception_handler)
except:
    pass


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
    """nanobot队列适配器"""
    
    def __init__(self):
        if not HAS_NANOBOT or NanobotQueue is None:
            raise QueueError("nanobot not available")
        self._queue = NanobotQueue()
    
    async def publish(self, channel: str, message: dict) -> None:
        if Event:
            event = Event(type="message", channel=channel, data=message)
            await self._queue.publish(event)
    
    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        async for event in self._queue.subscribe():
            if hasattr(event, 'channel') and event.channel == channel:
                yield event.data if hasattr(event, 'data') else {}
    
    async def close(self) -> None:
        pass


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
    """pyte终端模拟器 - 解析ncurses输出"""
    
    def __init__(self, cols: int = 80, rows: int = 24):
        if not HAS_PYTE:
            raise SDFShellError("pyte not installed: pip install pyte")
        self.cols = cols
        self.rows = rows
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
    
    def get_messages(self) -> list[str]:
        """提取用户聊天消息"""
        messages = []
        system_keywords = frozenset([
            'welcome', 'connected', 'disconnected', 'system', 'server',
            'online', 'users', 'status', 'help', 'error', 'warning'
        ])
        system_users = frozenset(['system', 'server', 'bot', 'admin', 'root'])
        
        for line in self.screen.display:
            line = clean_text(line)
            if len(line) < 3:
                continue
            
            line_lower = line.lower()
            if any(kw in line_lower for kw in system_keywords):
                continue
            
            # 匹配多种消息格式
            patterns = [
                r'^[<\[]?(\w+)[>\]:]\s*(.+)$',  # user: msg 或 <user> msg
                r'^(\w+)\s*>\s*(.+)$',           # user > msg
                r'^\[(\w+)\]\s*(.+)$',           # [user] msg
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    user, msg = match.group(1).strip(), match.group(2).strip()
                    if msg and user.lower() not in system_users:
                        messages.append(f"{user}: {msg}")
                    break
        
        return messages
    
    def reset(self) -> None:
        self._reset_screen()


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
                
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
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
                
                log.info(f"SSH connected: {host}:{port}")
                return f"Connected to {host}:{port}"
                
            except Exception as e:
                self._connected = False
                log.error(f"SSH connection failed: {e}")
                raise SSHError(f"Connection failed: {e}") from e
    
    async def reconnect(self) -> str:
        """重新连接"""
        if not self._host:
            raise SSHError("No previous connection to reconnect")
        
        log.info(f"Attempting to reconnect to {self._host}...")
        
        for attempt in range(self._reconnect_attempts):
            try:
                await self.disconnect()
                await asyncio.sleep(self._reconnect_delay)
                result = await self.connect(
                    self._host, self._username, self._password, self._port
                )
                log.info(f"Reconnected successfully on attempt {attempt + 1}")
                return result
            except Exception as e:
                log.warning(f"Reconnect attempt {attempt + 1} failed: {e}")
        
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
            raise COMError("SSH not connected")
        
        try:
            display, _ = await self.ssh.send_and_read("com", wait=2.0)
            
            if ">" in display or "COM" in display.upper():
                self._in_com = True
                log.info("COM logged in")
                return f"Logged into COM\n{display}"
            
            return f"Login may have failed\n{display}"
            
        except Exception as e:
            log.error(f"COM login error: {e}")
            raise COMError(f"Login failed: {e}") from e
    
    async def logout(self) -> str:
        """退出COM"""
        if not self._in_com:
            return "Not in COM"
        
        self._monitoring = False
        
        try:
            await self.ssh.send_command("/q", expect="$", timeout=2.0)
            self._in_com = False
            log.info("COM logged out")
            return "Logged out of COM"
            
        except Exception as e:
            log.error(f"COM logout error: {e}")
            raise COMError(f"Logout failed: {e}") from e
    
    async def send_message(self, message: str) -> str:
        """发送消息"""
        if not self._in_com:
            raise COMError("Not in COM")
        
        try:
            await self.ssh.send_and_read(message, wait=0.5)
            log.info(f"Message sent: {message[:50]}...")
            return f"Sent: {message}"
            
        except Exception as e:
            log.error(f"Send message error: {e}")
            raise COMError(f"Send failed: {e}") from e
    
    async def read_messages(self, count: int = 10) -> list[str]:
        """读取消息"""
        if not self._in_com:
            raise COMError("Not in COM")
        
        try:
            _, messages = await self.ssh.send_and_read("", wait=0.5)
            return messages[-count:] if messages else []
            
        except Exception as e:
            log.error(f"Read messages error: {e}")
            raise COMError(f"Read failed: {e}") from e
    
    async def start_monitor(self, callback: Callable[[list[str]], None], interval: float = 3.0) -> str:
        """启动消息监控"""
        if self._monitoring:
            return "Already monitoring"
        
        self._message_callback = callback
        self._monitor_interval = interval
        self._monitoring = True
        
        async def _monitor_loop():
            while self._monitoring and self._in_com:
                try:
                    messages = await self.read_messages(count=5)
                    if messages and self._message_callback:
                        self._message_callback(messages)
                except Exception as e:
                    log.error(f"Monitor error: {e}")
                await asyncio.sleep(self._monitor_interval)
        
        self._monitor_task = asyncio.create_task(_monitor_loop())
        log.info("Message monitor started")
        return "Monitor started"
    
    async def stop_monitor(self) -> str:
        """停止监控"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        log.info("Message monitor stopped")
        return "Monitor stopped"


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
        
        # 连接配置
        self.host = config.get("host") or os.environ.get("SDF_HOST", "sdf.org")
        self.port = config.get("port") or int(os.environ.get("SDF_PORT", "22"))
        self.username = config.get("username") or os.environ.get("SDF_USERNAME", "")
        self.password = config.get("password") or os.environ.get("SDF_PASSWORD", "")
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
    
    async def start(self) -> None:
        """启动通道"""
        log.info(f"Starting SDFShell channel: {self.host}")
        
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
        if self.username and self.password:
            await self._ssh.connect(self.host, self.username, self.password, self.port)
            await self._com.login()
            
            # 启动消息监控
            await self._com.start_monitor(
                callback=self._on_com_message,
                interval=self.monitor_interval
            )
        else:
            log.warning("Username/password not configured. Use ssh_connect to connect manually.")
        
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
    
    def _on_com_message(self, messages: list[str]) -> None:
        """处理COM消息回调"""
        for msg in messages:
            asyncio.create_task(self._queue.publish(self._channel_name, {
                "type": "message",
                "channel": self._channel_name,
                "content": msg,
                "timestamp": time.time()
            }))
            log.debug(f"COM message queued: {msg[:50]}...")
    
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

def ssh_connect(host: str, username: str, password: str, port: int = 22) -> str:
    """连接SSH服务器"""
    try:
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


# ============== TOOLS定义 ==============

TOOLS = [
    {
        "name": "ssh_connect",
        "description": "连接SSH服务器",
        "parameters": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "主机地址"},
                "username": {"type": "string", "description": "用户名"},
                "password": {"type": "string", "description": "密码"},
                "port": {"type": "integer", "description": "端口", "default": 22}
            },
            "required": ["host", "username", "password"]
        }
    },
    {
        "name": "com_login",
        "description": "登录COM聊天室",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "com_send",
        "description": "发送消息到COM",
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "消息内容"}},
            "required": ["message"]
        }
    },
    {
        "name": "com_read",
        "description": "读取COM消息",
        "parameters": {
            "type": "object",
            "properties": {"count": {"type": "integer", "description": "数量", "default": 10}}
        }
    },
    {
        "name": "com_logout",
        "description": "退出COM",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "ssh_disconnect",
        "description": "断开SSH连接",
        "parameters": {"type": "object", "properties": {}}
    }
]


__version__ = "2.0.0"
__all__ = [
    "SDFShellChannel",
    "SSHSession",
    "COMSession",
    "TerminalEmulator",
    "MessageQueue",
    "MemoryQueue",
    "RedisQueue",
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
    print("SDFShell v2.0.0 - SDF.org COM Chat Channel for nanobot")
    print(f"paramiko-expect: {HAS_PARAMIKO_EXPECT}")
    print(f"pyte: {HAS_PYTE}")
    print(f"redis: {HAS_REDIS}")
    print(f"nanobot: {HAS_NANOBOT}")
