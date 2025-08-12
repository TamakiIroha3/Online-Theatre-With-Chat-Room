# utils/process_manager.py - 进程管理器
import subprocess
import psutil
import platform
import signal
import time
import threading
from typing import Optional, List, Dict, Any
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

class ProcessManager:
    """统一的进程管理器"""
    
    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
    
    def start_process(
        self,
        name: str,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        stdout_callback: Optional[callable] = None,
        stderr_callback: Optional[callable] = None,
        restart_on_exit: bool = False
    ) -> bool:
        """
        启动进程
        Args:
            name: 进程名称（用于管理）
            command: 命令行参数列表
            cwd: 工作目录
            env: 环境变量
            stdout_callback: 标准输出回调函数
            stderr_callback: 标准错误回调函数
            restart_on_exit: 进程退出时是否自动重启
        """
        with self._lock:
            if name in self._processes:
                logger.warning(f"进程 {name} 已存在")
                return False
            
            try:
                # 准备启动参数
                startup_info = None
                if platform.system() == 'Windows':
                    # Windows下隐藏控制台窗口
                    startup_info = subprocess.STARTUPINFO()
                    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startup_info.wShowWindow = subprocess.SW_HIDE
                
                # 启动进程
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE if stdout_callback else subprocess.DEVNULL,
                    stderr=subprocess.PIPE if stderr_callback else subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    cwd=cwd,
                    env=env,
                    startupinfo=startup_info,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0,
                    text=True,
                    bufsize=1  # 行缓冲
                )
                
                self._processes[name] = process
                logger.debug(f"进程 {name} 已启动 (PID: {process.pid})")
                
                # 启动输出监控线程
                if stdout_callback or stderr_callback:
                    monitor_thread = threading.Thread(
                        target=self._monitor_process_output,
                        args=(name, process, stdout_callback, stderr_callback, restart_on_exit, command, cwd, env),
                        daemon=True
                    )
                    monitor_thread.start()
                    self._threads[name] = monitor_thread
                elif restart_on_exit:
                    # 即使没有输出回调，如果需要自动重启也要监控
                    monitor_thread = threading.Thread(
                        target=self._monitor_process_exit,
                        args=(name, process, command, cwd, env),
                        daemon=True
                    )
                    monitor_thread.start()
                    self._threads[name] = monitor_thread
                
                return True
            
            except Exception as e:
                logger.error(f"启动进程 {name} 失败: {e}")
                return False
    
    def _monitor_process_output(
        self,
        name: str,
        process: subprocess.Popen,
        stdout_callback: Optional[callable],
        stderr_callback: Optional[callable],
        restart_on_exit: bool,
        command: List[str],
        cwd: Optional[str],
        env: Optional[Dict[str, str]]
    ):
        """监控进程输出"""
        try:
            # 创建读取线程
            threads = []
            
            if stdout_callback and process.stdout:
                stdout_thread = threading.Thread(
                    target=self._read_stream,
                    args=(process.stdout, stdout_callback),
                    daemon=True
                )
                stdout_thread.start()
                threads.append(stdout_thread)
            
            if stderr_callback and process.stderr:
                stderr_thread = threading.Thread(
                    target=self._read_stream,
                    args=(process.stderr, stderr_callback),
                    daemon=True
                )
                stderr_thread.start()
                threads.append(stderr_thread)
            
            # 等待进程结束
            process.wait()
            
            # 等待所有读取线程结束
            for thread in threads:
                thread.join(timeout=1)
            
            # 处理进程退出
            with self._lock:
                if name in self._processes:
                    del self._processes[name]
                if name in self._threads:
                    del self._threads[name]
            
            exit_code = process.returncode
            if exit_code != 0:
                logger.warning(f"进程 {name} 异常退出，退出码: {exit_code}")
            else:
                logger.debug(f"进程 {name} 正常退出")
            
            # 自动重启逻辑
            if restart_on_exit and not self._shutdown_event.is_set():
                logger.debug(f"尝试重启进程 {name}")
                time.sleep(3)  # 等待3秒后重启
                if not self._shutdown_event.is_set():
                    self.start_process(
                        name, command, cwd, env,
                        stdout_callback, stderr_callback,
                        restart_on_exit
                    )
        
        except Exception as e:
            logger.error(f"监控进程 {name} 输出时出错: {e}")
    
    def _monitor_process_exit(
        self,
        name: str,
        process: subprocess.Popen,
        command: List[str],
        cwd: Optional[str],
        env: Optional[Dict[str, str]]
    ):
        """仅监控进程退出（用于自动重启）"""
        try:
            process.wait()
            
            with self._lock:
                if name in self._processes:
                    del self._processes[name]
                if name in self._threads:
                    del self._threads[name]
            
            exit_code = process.returncode
            if exit_code != 0:
                logger.warning(f"进程 {name} 异常退出，退出码: {exit_code}")
                
                # 自动重启
                if not self._shutdown_event.is_set():
                    logger.debug(f"尝试重启进程 {name}")
                    time.sleep(3)
                    if not self._shutdown_event.is_set():
                        self.start_process(name, command, cwd, env, None, None, True)
        
        except Exception as e:
            logger.error(f"监控进程 {name} 退出时出错: {e}")
    
    def _read_stream(self, stream, callback):
        """读取流数据"""
        try:
            for line in stream:
                if self._shutdown_event.is_set():
                    break
                if line:
                    callback(line.rstrip())
        except Exception as e:
            logger.debug(f"读取流时出错: {e}")
    
    def stop_process(self, name: str, timeout: int = 5) -> bool:
        """
        停止进程
        Args:
            name: 进程名称
            timeout: 等待超时时间（秒）
        """
        with self._lock:
            if name not in self._processes:
                logger.warning(f"进程 {name} 不存在")
                return False
            
            process = self._processes[name]
            
            try:
                # 先尝试正常终止
                if platform.system() == 'Windows':
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
                
                # 等待进程结束
                try:
                    process.wait(timeout=timeout)
                    logger.debug(f"进程 {name} 已正常停止")
                except subprocess.TimeoutExpired:
                    # 强制终止
                    logger.warning(f"进程 {name} 未响应，强制终止")
                    process.kill()
                    process.wait(timeout=2)
                
                # 清理记录
                del self._processes[name]
                if name in self._threads:
                    del self._threads[name]
                
                return True
            
            except Exception as e:
                logger.error(f"停止进程 {name} 失败: {e}")
                return False
    
    def stop_process_tree(self, name: str, timeout: int = 5) -> bool:
        """
        停止进程及其所有子进程
        Args:
            name: 进程名称
            timeout: 等待超时时间（秒）
        """
        with self._lock:
            if name not in self._processes:
                logger.warning(f"进程 {name} 不存在")
                return False
            
            process = self._processes[name]
            
            try:
                # 获取进程树
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                
                # 终止所有子进程
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                
                # 终止父进程
                parent.terminate()
                
                # 等待所有进程结束
                gone, alive = psutil.wait_procs(
                    [parent] + children,
                    timeout=timeout
                )
                
                # 强制杀死仍然存活的进程
                for p in alive:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass
                
                # 清理记录
                del self._processes[name]
                if name in self._threads:
                    del self._threads[name]
                
                logger.debug(f"进程树 {name} 已停止")
                return True
            
            except Exception as e:
                logger.error(f"停止进程树 {name} 失败: {e}")
                return False
    
    def is_process_running(self, name: str) -> bool:
        """检查进程是否在运行"""
        with self._lock:
            if name not in self._processes:
                return False
            
            process = self._processes[name]
            return process.poll() is None
    
    def get_process_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取进程信息"""
        with self._lock:
            if name not in self._processes:
                return None
            
            process = self._processes[name]
            
            try:
                p = psutil.Process(process.pid)
                return {
                    'pid': process.pid,
                    'name': p.name(),
                    'status': p.status(),
                    'cpu_percent': p.cpu_percent(),
                    'memory_info': p.memory_info()._asdict(),
                    'create_time': p.create_time(),
                    'num_threads': p.num_threads()
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None
    
    def get_all_processes(self) -> List[str]:
        """获取所有管理的进程名称"""
        with self._lock:
            return list(self._processes.keys())
    
    def stop_all(self, timeout: int = 5):
        """停止所有进程"""
        self._shutdown_event.set()
        
        processes = self.get_all_processes()
        for name in processes:
            try:
                # 对Nginx使用进程树停止
                if 'nginx' in name.lower():
                    self.stop_process_tree(name, timeout)
                else:
                    self.stop_process(name, timeout)
            except Exception as e:
                logger.error(f"停止进程 {name} 时出错: {e}")
        
        # 等待所有监控线程结束
        for thread in list(self._threads.values()):
            thread.join(timeout=1)
        
        self._threads.clear()
        logger.debug("所有进程已停止")
    
    def cleanup(self):
        """清理资源"""
        self.stop_all()
        self._processes.clear()
        self._threads.clear()
        self._shutdown_event.clear()

# 全局进程管理器实例
_global_process_manager = ProcessManager()

def get_process_manager() -> ProcessManager:
    """获取全局进程管理器实例"""
    return _global_process_manager