#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在线放映室 - 主程序入口
"""

import sys
import os
import signal
import traceback
import threading
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QObject, Signal, Slot, QTimer

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

import config
from utils.logger import LoggerManager, get_logger
from utils.process_manager import get_process_manager
from ui.main_window import MainWindow
from ui.sender_setup import SenderSetupWindow
from ui.receiver_setup import ReceiverSetupWindow
from ui.chat_room import ChatRoomWindow
from network.websocket_server import WebSocketServer
from network.websocket_client import WebSocketClient
from streaming.nginx_manager import NginxManager
from streaming.ffmpeg_manager import FFmpegManager
from streaming.mpv_player import MPVPlayer

# 初始化日志系统
LoggerManager.setup()
logger = get_logger(__name__)


class OnlineTheaterApp(QObject):
    """在线放映室应用主类"""
    
    # 定义信号（用于线程间通信）
    client_authenticated_signal = Signal(str, int)  # server_ip, srt_port
    client_error_signal = Signal(str)               # error_message
    client_disconnected_signal = Signal()
    chat_message_received_signal = Signal(str, str) # nickname, message
    member_list_updated_signal = Signal(list)       # members
    show_chat_room_signal = Signal()                # 显示聊天室
    mpv_closed_signal = Signal()                    # MPV关闭
    
    def __init__(self):
        super().__init__()
        self.app = None
        self.current_window = None
        self.role = None  # "sender" 或 "receiver"
        
        # 窗口实例
        self.main_window = None
        self.sender_setup_window = None
        self.receiver_setup_window = None
        self.chat_room_window = None
        
        # 网络组件
        self.ws_server = None
        self.ws_client = None
        
        # 流媒体组件
        self.nginx_manager = None
        self.ffmpeg_manager = None
        self.mpv_player = None
        
        # 配置信息
        self.config_params = {}
        
        # 用于存储待处理的SRT连接信息
        self.pending_srt_info = None
        
        # 连接内部信号
        self._connect_internal_signals()
    
    def _connect_internal_signals(self):
        """连接内部信号到槽函数"""
        self.client_authenticated_signal.connect(self._on_client_authenticated_main_thread)
        self.client_error_signal.connect(self._on_client_error_main_thread)
        self.client_disconnected_signal.connect(self._on_client_disconnected_main_thread)
        self.chat_message_received_signal.connect(self._on_chat_message_received_main_thread)
        self.member_list_updated_signal.connect(self._on_member_list_updated_main_thread)
        self.show_chat_room_signal.connect(self._show_chat_room_main_thread)
        self.mpv_closed_signal.connect(self._on_mpv_closed_main_thread)
    
    def run(self):
        """运行应用"""
        try:
            # 创建Qt应用
            self.app = QApplication(sys.argv)
            self.app.setApplicationName(config.APP_NAME)
            self.app.setApplicationDisplayName(config.APP_NAME)
            
            # 设置全局异常处理
            sys.excepthook = self.handle_exception
            
            # 设置退出信号处理
            signal.signal(signal.SIGINT, self.handle_signal)
            signal.signal(signal.SIGTERM, self.handle_signal)
            
            # 显示主窗口
            self.show_main_window()
            
            # 运行事件循环
            ret = self.app.exec()
            
            # 清理资源
            try:
                self.cleanup()
            except Exception as e:
                logger.error(f"退出时清理失败: {e}")
            
            return ret
        
        except Exception as e:
            logger.error(f"应用运行失败: {e}")
            traceback.print_exc()
            return 1
    
    def show_main_window(self):
        """显示主窗口"""
        self.main_window = MainWindow()
        self.main_window.sender_selected.connect(self.on_sender_selected)
        self.main_window.receiver_selected.connect(self.on_receiver_selected)
        self.main_window.center_on_screen()
        self.main_window.show()
        self.current_window = self.main_window
    
    @Slot()
    def on_sender_selected(self):
        """用户选择发送端"""
        self.role = "sender"
        self.show_sender_setup()
    
    @Slot()
    def on_receiver_selected(self):
        """用户选择接收端"""
        self.role = "receiver"
        self.show_receiver_setup()
    
    def show_sender_setup(self):
        """显示发送端设置界面"""
        self.sender_setup_window = SenderSetupWindow()
        self.sender_setup_window.setup_completed.connect(self.on_sender_setup_completed)
        self.sender_setup_window.back_requested.connect(self.back_to_main)
        self.sender_setup_window.center_on_screen()
        
        # 切换窗口
        if self.current_window:
            self.current_window.hide()
        self.sender_setup_window.show()
        self.current_window = self.sender_setup_window
    
    def show_receiver_setup(self):
        """显示接收端设置界面"""
        self.receiver_setup_window = ReceiverSetupWindow()
        self.receiver_setup_window.setup_completed.connect(self.on_receiver_setup_completed)
        self.receiver_setup_window.back_requested.connect(self.back_to_main)
        self.receiver_setup_window.center_on_screen()
        
        # 切换窗口
        if self.current_window:
            self.current_window.hide()
        self.receiver_setup_window.show()
        self.current_window = self.receiver_setup_window
    
    @Slot()
    def back_to_main(self):
        """返回主界面"""
        if self.current_window:
            self.current_window.hide()
        
        if not self.main_window:
            self.show_main_window()
        else:
            self.main_window.show()
            self.current_window = self.main_window
    
    @Slot(dict)
    def on_sender_setup_completed(self, params):
        """发送端设置完成"""
        self.config_params = params
        logger.info(f"发送端配置完成: {params}")
        
        # 启动发送端服务
        if self.start_sender_services():
            self.show_chat_room()
        else:
            QMessageBox.critical(
                self.current_window,
                "启动失败",
                "无法启动发送端服务，请检查配置和日志"
            )
    
    @Slot(dict)
    def on_receiver_setup_completed(self, params):
        """接收端设置完成"""
        self.config_params = params
        logger.info(f"接收端配置完成: {params}")
        
        # 连接到服务器
        if self.connect_to_server():
            # 连接成功后会通过回调显示聊天室
            pass
        else:
            QMessageBox.critical(
                self.current_window,
                "连接失败",
                "无法连接到服务器，请检查地址和端口"
            )
    
    def start_sender_services(self) -> bool:
        """启动发送端服务"""
        try:
            # 1. 启动Nginx RTMP服务器
            logger.info("启动Nginx RTMP服务器...")
            self.nginx_manager = NginxManager()
            if not self.nginx_manager.start():
                logger.error("启动Nginx失败")
                return False
            
            # 2. 启动FFmpeg SRT到RTMP转换
            logger.info("启动SRT到RTMP转换...")
            self.ffmpeg_manager = FFmpegManager()
            success = self.ffmpeg_manager.start_srt_to_rtmp(
                srt_port=self.config_params["srt_port"],
                bind_ip=self.config_params["bind_ip"],
                process_name="sender_srt_input"
            )
            if not success:
                logger.error("启动SRT到RTMP转换失败")
                self.nginx_manager.stop()
                return False
            
            # 3. 启动WebSocket服务器
            logger.info("启动WebSocket服务器...")
            self.ws_server = WebSocketServer(
                verification_code=self.config_params["verification_code"]
            )
            
            # 设置回调（使用lambda包装以确保线程安全）
            self.ws_server.set_on_message_callback(
                lambda nick, msg: self.chat_message_received_signal.emit(nick, msg)
            )
            self.ws_server.set_on_member_update_callback(
                lambda members: self.member_list_updated_signal.emit(members)
            )
            
            # 启动服务器
            success = self.ws_server.start_in_thread(
                host=self.config_params["bind_ip"],
                port=self.config_params["ws_port"],
                sender_nickname=self.config_params["nickname"]
            )
            
            if not success:
                logger.error("启动WebSocket服务器失败")
                self.ffmpeg_manager.stop_all()
                self.nginx_manager.stop()
                return False
            
            # 4. 如果选择本地播放，启动MPV
            if self.config_params.get("enable_local_play", True):
                logger.info("[发送端] 启动本地播放器（将持续尝试连接RTMP流）...")
                self.mpv_player = MPVPlayer(player_type="sender")
                self.mpv_player.set_on_closed_callback(
                    lambda: self.mpv_closed_signal.emit()
                )
                self.mpv_player.play_rtmp(retry=True)
            
            logger.info("[发送端] 所有服务启动成功，等待OBS推流...")
            return True
        
        except Exception as e:
            logger.error(f"启动发送端服务失败: {e}")
            traceback.print_exc()
            return False
    
    def connect_to_server(self) -> bool:
        """连接到服务器（接收端）"""
        try:
            logger.info("连接到服务器...")
            self.ws_client = WebSocketClient()
            
            # 设置回调（使用lambda包装以发射信号）
            self.ws_client.set_on_authenticated_callback(
                lambda ip, port: self.client_authenticated_signal.emit(ip, port)
            )
            self.ws_client.set_on_message_callback(
                lambda nick, msg: self.chat_message_received_signal.emit(nick, msg)
            )
            self.ws_client.set_on_member_update_callback(
                lambda members: self.member_list_updated_signal.emit(members)
            )
            self.ws_client.set_on_error_callback(
                lambda err: self.client_error_signal.emit(err)
            )
            self.ws_client.set_on_disconnected_callback(
                lambda: self.client_disconnected_signal.emit()
            )
            
            # 连接服务器
            success = self.ws_client.connect_in_thread(
                host=self.config_params["server_ip"],
                port=self.config_params["server_port"],
                nickname=self.config_params["nickname"],
                verification_code=self.config_params["verification_code"]
            )
            
            if not success:
                logger.error("连接服务器失败")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            traceback.print_exc()
            return False
    
    def on_client_authenticated(self, server_ip: str, srt_port: int):
        """客户端认证成功回调（在WebSocket线程中）"""
        logger.info(f"认证成功，SRT端口: {srt_port}")
        # 保存信息并发射信号到主线程
        self.client_srt_info = (server_ip, srt_port)
        self.client_authenticated_signal.emit(server_ip, srt_port)
    
    @Slot(str, int)
    def _on_client_authenticated_main_thread(self, server_ip: str, srt_port: int):
        """客户端认证成功处理（在主线程中）"""
        # 启动MPV播放器
        self.mpv_player = MPVPlayer(player_type="receiver")
        
        # 设置MPV关闭回调（使用信号）
        self.mpv_player.set_on_closed_callback(
            lambda: self.mpv_closed_signal.emit()
        )
        
        success = QTimer.singleShot(5000, lambda: self.mpv_player.play_srt(server_ip, srt_port))
        
        # 显示聊天室
        self.show_chat_room()
    
    def on_client_error(self, error_msg: str):
        """客户端错误回调（在WebSocket线程中）"""
        logger.error(f"客户端错误: {error_msg}")
        self.client_error_signal.emit(error_msg)
    
    @Slot(str)
    def _on_client_error_main_thread(self, error_msg: str):
        """客户端错误处理（在主线程中）"""
        if self.current_window:
            QMessageBox.warning(
                self.current_window,
                "连接错误",
                error_msg
            )
    
    def on_client_disconnected(self):
        """客户端断开连接回调（在WebSocket线程中）"""
        logger.warning("与服务器断开连接")
        self.client_disconnected_signal.emit()
    
    @Slot()
    def _on_client_disconnected_main_thread(self):
        """客户端断开连接处理（在主线程中）"""
        # 可以在这里处理重连逻辑或显示提示
        if self.chat_room_window:
            self.chat_room_window.add_message("系统", "与服务器的连接已断开", True)
    
    def show_chat_room(self):
        """显示聊天室界面（确保在主线程中）"""
        # 如果不在主线程，发射信号
        if threading.current_thread() != threading.main_thread():
            self.show_chat_room_signal.emit()
            return
        
        self._show_chat_room_main_thread()
    
    @Slot()
    def _show_chat_room_main_thread(self):
        """显示聊天室界面（在主线程中执行）"""
        self.chat_room_window = ChatRoomWindow(
            role=self.role,
            nickname=self.config_params["nickname"]
        )
        
        # 连接信号
        self.chat_room_window.message_sent.connect(self.on_send_chat_message)
        self.chat_room_window.window_closing.connect(self.on_chat_room_closing)
        
        # 设置MPV关闭回调（使用信号）
        if self.mpv_player:
            self.mpv_player.set_on_closed_callback(
                lambda: self.mpv_closed_signal.emit()
            )
        
        self.chat_room_window.center_on_screen()
        
        # 切换窗口
        if self.current_window:
            self.current_window.hide()
        self.chat_room_window.show()
        self.current_window = self.chat_room_window
    
    @Slot(str)
    def on_send_chat_message(self, message):
        """发送聊天消息"""
        if self.role == "sender" and self.ws_server:
            self.ws_server.send_chat_message_sync(message)
        elif self.role == "receiver" and self.ws_client:
            self.ws_client.send_chat_message_sync(message)
    
    @Slot(str, str)
    def _on_chat_message_received_main_thread(self, nickname: str, message: str):
        """接收聊天消息处理（在主线程中）"""
        if self.chat_room_window:
            # 系统消息特殊处理
            is_system = (nickname == "系统")
            self.chat_room_window.add_message(nickname, message, is_system)
    
    @Slot(list)
    def _on_member_list_updated_main_thread(self, members: list):
        """成员列表更新处理（在主线程中）"""
        if self.chat_room_window:
            self.chat_room_window.update_member_list(members)
    
    @Slot()
    def _on_mpv_closed_main_thread(self):
        """MPV关闭处理（在主线程中）"""
        logger.info("播放器已关闭")
        # 接收端播放器关闭但聊天室保持
        if self.role == "receiver":
            if self.chat_room_window:
                self.chat_room_window.add_message("系统", "播放器已关闭，您仍可以继续聊天", True)
    
    @Slot()
    def on_chat_room_closing(self):
        """聊天室关闭"""
        logger.info("聊天室关闭")
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"关闭时清理失败: {e}")
        finally:
            self.app.quit()
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        
        # 清除待处理的连接信息
        self.pending_srt_info = None
        
        try:
            # 停止MPV
            if self.mpv_player:
                self.mpv_player.cleanup()
            
            # 停止WebSocket（先客户端后服务器）
            if self.ws_client:
                try:
                    self.ws_client.cleanup()
                except Exception as e:
                    logger.debug(f"清理WebSocket客户端时出错: {e}")
            
            if self.ws_server:
                try:
                    self.ws_server.cleanup()
                except Exception as e:
                    logger.debug(f"清理WebSocket服务器时出错: {e}")
            
            # 停止FFmpeg
            if self.ffmpeg_manager:
                self.ffmpeg_manager.cleanup()
            
            # 停止Nginx
            if self.nginx_manager:
                self.nginx_manager.cleanup()
            
            # 停止所有进程
            process_manager = get_process_manager()
            process_manager.cleanup()
            
            # 清理日志
            LoggerManager.cleanup()
            
            logger.info("资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """全局异常处理"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))
        
        # 显示错误对话框
        error_msg = f"{exc_type.__name__}: {exc_value}"
        QMessageBox.critical(None, "程序错误", f"发生未预期的错误:\n{error_msg}")
    
    def handle_signal(self, signum, frame):
        """处理系统信号"""
        logger.info(f"收到信号: {signum}")
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"信号处理时清理失败: {e}")
        finally:
            sys.exit(0)


def main():
    """主函数"""
    # 设置高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 创建并运行应用
    app = OnlineTheaterApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())