# streaming/mpv_player.py - MPV播放器管理器
import os
import time
from pathlib import Path
from typing import Optional, List, Callable
import threading
import config
from utils.logger import get_logger
from utils.process_manager import get_process_manager
from utils.network_utils import NetworkUtils

logger = get_logger(__name__)

class MPVPlayer:
    """MPV播放器管理器"""
    
    def __init__(self, player_type: str = "receiver"):
        """
        初始化MPV播放器
        Args:
            player_type: 播放器类型 ("sender" 或 "receiver")
        """
        self.process_manager = get_process_manager()
        self.mpv_path = Path(config.EXTERNAL_PROGRAMS["mpv"])
        self.player_type = player_type
        self.process_name = f"mpv_{player_type}"
        self.is_playing = False
        self.retry_thread: Optional[threading.Thread] = None
        self.stop_retry = threading.Event()
        self.on_closed_callback: Optional[Callable] = None
        
        # 验证MPV是否存在
        if not self.mpv_path.exists():
            logger.error(f"MPV不存在: {self.mpv_path}")
            raise FileNotFoundError(f"找不到MPV: {self.mpv_path}")
    
    def play_rtmp(self, rtmp_url: str = None, retry: bool = True) -> bool:
        """
        播放RTMP流（发送端使用）
        Args:
            rtmp_url: RTMP流地址，默认使用本地RTMP服务器
            retry: 是否在流不可用时持续重试
        """
        if self.is_playing:
            logger.warning("MPV已在播放")
            return True
        
        # 默认RTMP地址
        if rtmp_url is None:
            rtmp_url = f"rtmp://127.0.0.1:{config.NGINX_CONFIG['rtmp']['port']}/live/stream"
        
        if retry:
            # 启动重试线程
            self.stop_retry.clear()
            self.retry_thread = threading.Thread(
                target=self._retry_play_rtmp,
                args=(rtmp_url,),
                daemon=True
            )
            self.retry_thread.start()
            return True
        else:
            return self._start_mpv(rtmp_url)
    
    def play_srt(self, host: str, port: int) -> bool:
        """
        播放SRT流（接收端使用）
        Args:
            host: SRT服务器地址
            port: SRT端口
        """
        if self.is_playing:
            logger.warning("MPV已在播放")
            return True
        
        # 处理IPv6地址格式
        if NetworkUtils.is_valid_ipv6(host):
            host = NetworkUtils.format_ipv6_for_url(host)
        
        # 构建SRT URL
        srt_url = f"srt://{host}:{port}?mode=caller&latency=3000"

        
        return self._start_mpv(srt_url)
    
    def _start_mpv(self, stream_url: str) -> bool:
        """
        启动MPV播放器
        Args:
            stream_url: 流地址
        """
        try:
            # 构建MPV命令
            command = [str(self.mpv_path)]
            
            # 添加播放器类型特定参数
            if self.player_type == "sender":
                command.extend(config.MPV_PARAMS["sender"])
            else:
                command.extend(config.MPV_PARAMS["receiver"])
            
            # 添加通用参数
            command.extend(config.MPV_PARAMS["common"])
            
            # 添加流地址
            command.append(stream_url)
            
            # 启动MPV
            success = self.process_manager.start_process(
                name=self.process_name,
                command=command,
                stdout_callback=self._handle_output,
                stderr_callback=self._handle_error,
                restart_on_exit=False
            )
            
            if success:
                self.is_playing = True
                logger.info(f"MPV播放器已启动")
                
                # 启动监控线程
                monitor_thread = threading.Thread(
                    target=self._monitor_player,
                    daemon=True
                )
                monitor_thread.start()
                
                return True
            else:
                logger.error("启动MPV失败")
                return False
        
        except Exception as e:
            logger.error(f"启动MPV时出错: {e}")
            return False
    
    def _retry_play_rtmp(self, rtmp_url: str):
        """持续重试播放RTMP流（用于等待流可用）- 服务端无限循环"""
        retry_count = 0
        retry_interval = 3  # 重试间隔（秒）
        
        logger.info(f"开始尝试播放RTMP流: {rtmp_url}")
        logger.info("将持续尝试直到成功连接或手动停止...")
        
        while not self.stop_retry.is_set():
            if self._start_mpv(rtmp_url):
                logger.debug("成功连接到RTMP流")
                break
            
            retry_count += 1
            logger.info(f"RTMP流暂不可用，{retry_interval}秒后重试... (尝试 {retry_count})")
            
            # 分段等待，以便能快速响应停止请求
            for _ in range(retry_interval * 10):
                if self.stop_retry.is_set():
                    logger.info("停止重试播放RTMP流")
                    return
                time.sleep(0.1)
    
    def stop(self) -> bool:
        """停止播放器"""
        # 停止重试
        self.stop_retry.set()
        if self.retry_thread and self.retry_thread.is_alive():
            self.retry_thread.join(timeout=1)
        
        if not self.is_playing:
            logger.warning("MPV未在播放")
            return True
        
        try:
            success = self.process_manager.stop_process(self.process_name)
            
            if success:
                self.is_playing = False
                logger.debug("MPV播放器已停止")
                return True
            else:
                logger.error("停止MPV失败")
                return False
        
        except Exception as e:
            logger.error(f"停止MPV时出错: {e}")
            return False
    
    def is_running(self) -> bool:
        """检查播放器是否在运行"""
        if not self.is_playing:
            return False
        
        return self.process_manager.is_process_running(self.process_name)
    
    def set_on_closed_callback(self, callback: Callable):
        """
        设置播放器关闭时的回调函数
        Args:
            callback: 回调函数
        """
        self.on_closed_callback = callback
    
    def _monitor_player(self):
        """监控播放器状态"""
        while self.is_playing:
            time.sleep(1)
            if not self.is_running():
                self.is_playing = False
                logger.debug("MPV播放器已关闭")
                
                # 触发回调
                if self.on_closed_callback:
                    try:
                        self.on_closed_callback()
                    except Exception as e:
                        logger.error(f"执行播放器关闭回调时出错: {e}")
                
                break
    
    def _handle_output(self, line: str):
        """处理MPV标准输出"""
        # 只记录关键信息
        if "Playing:" in line:
            logger.debug(f"[MPV] 正在播放")
        elif "Video:" in line or "Audio:" in line:
            logger.debug(f"[MPV] 流信息已加载")
    
    def _handle_error(self, line: str):
        """处理MPV错误输出"""
        # 只显示重要错误
        if "error" in line.lower() or "failed" in line.lower():
            if "No stream found" not in line:  # 忽略等待流的消息
                logger.error(f"[MPV] 播放错误")
        elif "warning" in line.lower():
            pass  # 忽略警告
    
    def cleanup(self):
        """清理资源"""
        self.stop_retry.set()
        if self.is_playing:
            self.stop()