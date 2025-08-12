# ui/__init__.py - UI模块包
"""
用户界面模块
包含所有窗口和界面组件
"""

from .main_window import MainWindow
from .sender_setup import SenderSetupWindow
from .receiver_setup import ReceiverSetupWindow
from .chat_room import ChatRoomWindow

__all__ = [
    'MainWindow',
    'SenderSetupWindow', 
    'ReceiverSetupWindow',
    'ChatRoomWindow'
]

__version__ = '1.0.0'