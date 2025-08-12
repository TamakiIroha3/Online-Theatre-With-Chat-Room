# streaming/nginx_manager.py - Nginx管理器
import os
import time
from pathlib import Path
from typing import Optional
import config
from utils.logger import get_logger
from utils.process_manager import get_process_manager

logger = get_logger(__name__)

class NginxManager:
    """Nginx RTMP服务器管理器"""
    
    def __init__(self):
        self.process_manager = get_process_manager()
        self.nginx_path = Path(config.EXTERNAL_PROGRAMS["nginx"])
        self.process_name = "nginx_rtmp"
        self.is_running = False
        
        # 验证Nginx是否存在
        if not self.nginx_path.exists():
            logger.error(f"Nginx不存在: {self.nginx_path}")
            raise FileNotFoundError(f"找不到Nginx: {self.nginx_path}")
    
    def start(self) -> bool:
        """启动Nginx RTMP服务器"""
        if self.is_running:
            logger.warning("Nginx已在运行")
            return True
        
        try:
            # 准备启动命令
            command = [str(self.nginx_path)]
            
            # 设置工作目录为nginx所在目录
            working_dir = self.nginx_path.parent
            
            # 启动Nginx
            success = self.process_manager.start_process(
                name=self.process_name,
                command=command,
                cwd=str(working_dir),
                stdout_callback=self._handle_output,
                stderr_callback=self._handle_error,
                restart_on_exit=False  # Nginx通常不需要自动重启
            )
            
            if success:
                # 等待Nginx完全启动
                time.sleep(1)
                
                # 验证是否成功启动
                if self.process_manager.is_process_running(self.process_name):
                    self.is_running = True
                    logger.info(f"Nginx RTMP服务器已启动 (端口: {config.NGINX_CONFIG['rtmp']['port']})")
                    return True
                else:
                    logger.error("Nginx启动后立即退出")
                    return False
            else:
                logger.error("启动Nginx失败")
                return False
        
        except Exception as e:
            logger.error(f"启动Nginx时出错: {e}")
            return False
    
    def stop(self) -> bool:
        """停止Nginx服务器"""
        if not self.is_running:
            logger.warning("Nginx未在运行")
            return True
        
        try:
            # Nginx通常会产生多个进程，需要停止整个进程树
            success = self.process_manager.stop_process_tree(
                self.process_name,
                timeout=5
            )
            
            if success:
                self.is_running = False
                logger.debug("Nginx RTMP服务器已停止")
                return True
            else:
                logger.error("停止Nginx失败")
                return False
        
        except Exception as e:
            logger.error(f"停止Nginx时出错: {e}")
            return False
    
    def restart(self) -> bool:
        """重启Nginx服务器"""
        logger.debug("正在重启Nginx...")
        
        # 先停止
        if self.is_running:
            if not self.stop():
                logger.error("停止Nginx失败，无法重启")
                return False
            
            # 等待端口释放
            time.sleep(2)
        
        # 再启动
        return self.start()
    
    def check_status(self) -> bool:
        """检查Nginx状态"""
        if not self.is_running:
            return False
        
        return self.process_manager.is_process_running(self.process_name)
    
    def get_rtmp_url(self, stream_key: str = None) -> str:
        """
        获取RTMP URL
        Args:
            stream_key: 流密钥，默认使用配置中的值
        """
        if stream_key is None:
            stream_key = config.NGINX_CONFIG['rtmp']['stream_key']
        
        return f"rtmp://127.0.0.1:{config.NGINX_CONFIG['rtmp']['port']}/{config.NGINX_CONFIG['rtmp']['app_name']}/{stream_key}"
    
    def _handle_output(self, line: str):
        """处理Nginx标准输出"""
        logger.debug(f"[Nginx] {line}")
    
    def _handle_error(self, line: str):
        """处理Nginx错误输出"""
        # Nginx的一些正常信息也会输出到stderr，所以根据内容判断级别
        if "error" in line.lower() or "failed" in line.lower():
            logger.error(f"[Nginx Error] {line}")
        elif "warning" in line.lower():
            logger.warning(f"[Nginx Warning] {line}")
        else:
            logger.debug(f"[Nginx] {line}")
    
    def cleanup(self):
        """清理资源"""
        if self.is_running:
            self.stop()