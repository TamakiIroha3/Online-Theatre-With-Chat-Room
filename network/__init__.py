# network/__init__.py - 网络模块包
"""
网络通信模块
包含WebSocket服务器和客户端实现
"""

from .websocket_server import WebSocketServer
from .websocket_client import WebSocketClient

__all__ = [
    'WebSocketServer',
    'WebSocketClient'
]

__version__ = '1.0.0'