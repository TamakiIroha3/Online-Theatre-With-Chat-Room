# utils/logger.py - 日志管理器
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
import config

class LoggerManager:
    """统一的日志管理器"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def setup(cls):
        """初始化日志系统"""
        if cls._initialized:
            return
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 设置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.LOGGING["level"]))
        
        # 清除已有的处理器
        root_logger.handlers.clear()
        
        # 文件处理器（主日志）
        main_log_path = log_dir / config.LOGGING["file_name"]
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_path,
            maxBytes=config.LOGGING["max_bytes"],
            backupCount=config.LOGGING["backup_count"],
            encoding=config.LOGGING["encoding"]
        )
        file_handler.setFormatter(cls._get_formatter())
        root_logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(cls._get_formatter())
        root_logger.addHandler(console_handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name):
        """获取指定名称的日志器"""
        if not cls._initialized:
            cls.setup()
        
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def get_ffmpeg_logger(cls, process_name):
        """获取FFmpeg专用日志器"""
        if not cls._initialized:
            cls.setup()
        
        logger_name = f"ffmpeg.{process_name}"
        if logger_name not in cls._loggers:
            logger = logging.getLogger(logger_name)
            
            # 为每个FFmpeg进程创建单独的日志文件
            log_dir = Path("logs") / "ffmpeg"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"{process_name}_{timestamp}.log"
            
            file_handler = logging.FileHandler(
                log_file,
                encoding=config.LOGGING["encoding"]
            )
            file_handler.setFormatter(cls._get_formatter(detailed=True))
            file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
            
            # 设置不向上传播，避免重复记录
            logger.propagate = False
            logger.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
            
            # 不再添加控制台输出handler，只输出到文件
            
            cls._loggers[logger_name] = logger
        
        return cls._loggers[logger_name]
    
    @classmethod
    def _get_formatter(cls, detailed=False):
        """获取日志格式化器"""
        if detailed:
            # 详细格式（用于FFmpeg等进程日志）
            format_str = "%(asctime)s.%(msecs)03d - [%(levelname)s] - %(message)s"
        else:
            # 标准格式
            format_str = config.LOGGING["format"]
        
        return logging.Formatter(
            format_str,
            datefmt=config.LOGGING["date_format"]
        )
    
    @classmethod
    def cleanup(cls):
        """清理日志系统"""
        for logger in cls._loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        cls._loggers.clear()
        cls._initialized = False

# 便捷函数
def get_logger(name):
    """获取日志器的便捷函数"""
    return LoggerManager.get_logger(name)

def get_ffmpeg_logger(process_name):
    """获取FFmpeg日志器的便捷函数"""
    return LoggerManager.get_ffmpeg_logger(process_name)