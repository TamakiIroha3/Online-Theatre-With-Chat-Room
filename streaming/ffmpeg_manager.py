# streaming/ffmpeg_manager.py - FFmpeg管理器
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import config
from utils.logger import get_logger, get_ffmpeg_logger
from utils.process_manager import get_process_manager
from utils.network_utils import NetworkUtils

logger = get_logger(__name__)

class FFmpegManager:
    """FFmpeg进程管理器"""
    
    def __init__(self):
        self.process_manager = get_process_manager()
        self.ffmpeg_path = Path(config.EXTERNAL_PROGRAMS["ffmpeg"])
        self.processes: Dict[str, Dict[str, Any]] = {}
        
        # 验证FFmpeg是否存在
        if not self.ffmpeg_path.exists():
            logger.error(f"FFmpeg不存在: {self.ffmpeg_path}")
            raise FileNotFoundError(f"找不到FFmpeg: {self.ffmpeg_path}")
    
    def start_srt_to_rtmp(
        self,
        srt_port: int,
        rtmp_url: str = None,
        bind_ip: str = "0.0.0.0",
        process_name: str = None
    ) -> bool:
        """
        启动SRT到RTMP的转换进程
        Args:
            srt_port: SRT监听端口
            rtmp_url: RTMP推流地址，默认使用本地RTMP服务器
            bind_ip: SRT绑定IP地址
            process_name: 进程名称
        """
        if process_name is None:
            process_name = f"srt_to_rtmp_{srt_port}"
        
        if process_name in self.processes:
            logger.warning(f"进程 {process_name} 已存在")
            return False
        
        # 默认RTMP地址
        if rtmp_url is None:
            rtmp_url = f"rtmp://127.0.0.1:{config.NGINX_CONFIG['rtmp']['port']}/live/stream"
        
        # 处理IPv6地址格式
        if NetworkUtils.is_valid_ipv6(bind_ip):
            bind_ip = NetworkUtils.format_ipv6_for_url(bind_ip)
        
        # 构建FFmpeg命令
        command = [str(self.ffmpeg_path)]
        command.extend(config.FFMPEG_PARAMS["common"])
        
        # 添加分析和探测参数（在输入之前）
        command.extend([
            "-analyzeduration", "10000000",  # 10秒分析时长
            "-probesize", "10000000",        # 10MB探测大小
            "-fflags", "+genpts"             # 生成PTS
        ])
        
        # SRT输入参数
        srt_url = f"srt://{bind_ip}:{srt_port}?mode=listener&latency={config.FFMPEG_PARAMS['srt_input']['latency']}"
        command.extend(["-i", srt_url])
        
        # 输出参数（不转码）
        command.extend([
            "-c", "copy",
            "-f", "flv",
            "-flvflags", "no_duration_filesize",
            rtmp_url
        ])
        
        # 获取专用日志器
        process_logger = get_ffmpeg_logger(process_name)
        
        # 启动进程
        success = self.process_manager.start_process(
            name=process_name,
            command=command,
            stdout_callback=lambda line: self._handle_ffmpeg_output(process_name, line, process_logger),
            stderr_callback=lambda line: self._handle_ffmpeg_error(process_name, line, process_logger),
            restart_on_exit=True  # SRT输入断开时自动重启
        )
        
        if success:
            self.processes[process_name] = {
                "type": "srt_to_rtmp",
                "srt_port": srt_port,
                "rtmp_url": rtmp_url,
                "bind_ip": bind_ip,
                "start_time": datetime.now(),
                "logger": process_logger
            }
            logger.info(f"SRT->RTMP转换进程已启动 (端口: {srt_port})")
            return True
        
        return False
    
    def start_rtmp_to_srt(
        self,
        rtmp_url: str,
        srt_port: int,
        bind_ip: str = "0.0.0.0",
        process_name: str = None
    ) -> bool:
        """
        启动RTMP到SRT的转换进程
        Args:
            rtmp_url: RTMP拉流地址
            srt_port: SRT监听端口
            bind_ip: SRT绑定IP地址
            process_name: 进程名称
        """
        if process_name is None:
            process_name = f"rtmp_to_srt_{srt_port}"
        
        if process_name in self.processes:
            logger.warning(f"进程 {process_name} 已存在")
            return False
        
        # 处理IPv6地址格式
        if NetworkUtils.is_valid_ipv6(bind_ip):
            bind_ip = NetworkUtils.format_ipv6_for_url(bind_ip)
        
        # 构建FFmpeg命令
        command = [str(self.ffmpeg_path)]
        command.extend(config.FFMPEG_PARAMS["common"])
        
        # 添加分析和探测参数（在输入之前）
        command.extend([
            "-analyzeduration", "5000000",   # 5秒分析时长（RTMP相对稳定）
            "-probesize", "5000000",         # 5MB探测大小
            "-fflags", "+genpts"             # 生成PTS
        ])
        
        # RTMP输入参数
        command.extend([
            "-re",  # 按原始帧率读取
            "-i", rtmp_url
        ])
        
        # SRT输出参数
        srt_url = f"srt://{bind_ip}:{srt_port}?mode=listener&latency={config.FFMPEG_PARAMS['srt_output']['latency']}"
        command.extend([
            "-c", "copy",  # 不转码
            "-f", "mpegts",  # SRT使用MPEG-TS封装
            srt_url
        ])
        
        # 获取专用日志器
        process_logger = get_ffmpeg_logger(process_name)
        
        # 启动进程
        success = self.process_manager.start_process(
            name=process_name,
            command=command,
            stdout_callback=lambda line: self._handle_ffmpeg_output(process_name, line, process_logger),
            stderr_callback=lambda line: self._handle_ffmpeg_error(process_name, line, process_logger),
            restart_on_exit=False  # RTMP到SRT通常不需要自动重启
        )
        
        if success:
            self.processes[process_name] = {
                "type": "rtmp_to_srt",
                "rtmp_url": rtmp_url,
                "srt_port": srt_port,
                "bind_ip": bind_ip,
                "start_time": datetime.now(),
                "logger": process_logger
            }
            logger.info(f"RTMP->SRT转换进程已启动 (端口: {srt_port})")
            return True
        
        return False
    
    def stop_process(self, process_name: str) -> bool:
        """停止指定的FFmpeg进程"""
        if process_name not in self.processes:
            logger.warning(f"进程 {process_name} 不存在")
            return False
        
        success = self.process_manager.stop_process(process_name)
        
        if success:
            del self.processes[process_name]
            logger.debug(f"FFmpeg进程已停止: {process_name}")
            return True
        
        return False
    
    def stop_all(self):
        """停止所有FFmpeg进程"""
        for process_name in list(self.processes.keys()):
            self.stop_process(process_name)
    
    def is_process_running(self, process_name: str) -> bool:
        """检查进程是否在运行"""
        if process_name not in self.processes:
            return False
        
        return self.process_manager.is_process_running(process_name)
    
    def get_process_info(self, process_name: str) -> Optional[Dict[str, Any]]:
        """获取进程信息"""
        if process_name not in self.processes:
            return None
        
        info = self.processes[process_name].copy()
        info['running'] = self.is_process_running(process_name)
        info['uptime'] = (datetime.now() - info['start_time']).total_seconds()
        
        # 获取系统信息
        sys_info = self.process_manager.get_process_info(process_name)
        if sys_info:
            info.update(sys_info)
        
        # 不返回logger对象
        info.pop('logger', None)
        
        return info
    
    def get_all_processes(self) -> List[str]:
        """获取所有FFmpeg进程名称"""
        return list(self.processes.keys())
    
    def _handle_ffmpeg_output(self, process_name: str, line: str, process_logger):
        """处理FFmpeg标准输出"""
        # 只记录到文件，不在控制台输出
        process_logger.info(line)
        
        # 只在控制台显示关键信息
        if "Stream #" in line:
            logger.debug(f"[{process_name}] 检测到流")
        elif "fps=" in line:
            # 解析统计信息但不输出
            self._parse_stats(process_name, line)
    
    def _handle_ffmpeg_error(self, process_name: str, line: str, process_logger):
        """处理FFmpeg错误输出"""
        # 记录到文件
        process_logger.error(line)
        
        # 只在控制台输出重要错误
        if "error" in line.lower() or "failed" in line.lower():
            if "Connection refused" in line or "Connection reset" in line:
                logger.error(f"[{process_name}] 连接失败，可能需要重启")
            elif "Invalid data" in line:
                logger.warning(f"[{process_name}] 接收到无效数据")
            elif "dimensions not set" not in line.lower():  # 忽略dimensions not set错误
                logger.error(f"[{process_name}] FFmpeg错误")
        elif "warning" in line.lower() and "input queue" not in line.lower():
            # 忽略input queue满的警告
            pass
    
    def _parse_stats(self, process_name: str, line: str):
        """解析FFmpeg统计信息"""
        try:
            # 提取fps、bitrate等信息
            stats = {}
            
            if "fps=" in line:
                fps_str = line.split("fps=")[1].split()[0]
                stats['fps'] = float(fps_str)
            
            if "bitrate=" in line:
                bitrate_str = line.split("bitrate=")[1].split()[0]
                stats['bitrate'] = bitrate_str
            
            if "time=" in line:
                time_str = line.split("time=")[1].split()[0]
                stats['time'] = time_str
            
            if stats:
                if process_name in self.processes:
                    self.processes[process_name]['stats'] = stats
                    # 不输出到控制台，只更新内部状态
        
        except Exception as e:
            # 静默处理解析错误
            pass
    
    def cleanup(self):
        """清理资源"""
        self.stop_all()