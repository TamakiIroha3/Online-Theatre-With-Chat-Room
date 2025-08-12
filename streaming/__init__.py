# streaming/__init__.py - 流媒体模块包
"""
流媒体处理模块
包含FFmpeg、MPV和Nginx的管理器
"""

from .ffmpeg_manager import FFmpegManager
from .mpv_player import MPVPlayer
from .nginx_manager import NginxManager

__all__ = [
    'FFmpegManager',
    'MPVPlayer',
    'NginxManager'
]

__version__ = '1.0.0'