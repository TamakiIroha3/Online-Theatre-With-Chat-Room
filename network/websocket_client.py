# network/websocket_client.py - WebSocket客户端
import asyncio
import websockets
import json
import threading
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import config
from utils.logger import get_logger
from utils.network_utils import NetworkUtils

logger = get_logger(__name__)

class WebSocketClient:
    """WebSocket客户端（接收端使用）"""
    
    def __init__(self):
        """初始化WebSocket客户端"""
        self.websocket = None
        self.loop = None
        self.client_thread = None
        self.running = False
        self.connected = False
        self.authenticated = False
        
        # 连接信息
        self.server_host = None
        self.server_port = None
        self.nickname = None
        self.verification_code = None
        self.srt_port = None
        self.server_ip = None
        
        # 回调函数
        self.on_connected_callback: Optional[Callable] = None
        self.on_disconnected_callback: Optional[Callable] = None
        self.on_authenticated_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        self.on_member_update_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # 重连控制
        self.auto_reconnect = True
        self.reconnect_interval = config.NETWORK_DEFAULTS["reconnect_interval"]
        self.max_reconnect_attempts = config.NETWORK_DEFAULTS["max_reconnect_attempts"]
        self.reconnect_attempts = 0
    
    async def connect(self, host: str, port: int, nickname: str, verification_code: str) -> bool:
        """
        连接到WebSocket服务器
        Args:
            host: 服务器地址
            port: 服务器端口
            nickname: 昵称
            verification_code: 验证码
        """
        try:
            self.server_host = host
            self.server_port = port
            self.nickname = nickname
            self.verification_code = verification_code
            
            # 处理IPv6地址格式
            if NetworkUtils.is_valid_ipv6(host):
                # WebSocket URI中IPv6地址需要用方括号
                host_formatted = NetworkUtils.format_ipv6_for_url(host)
            else:
                host_formatted = host
            
            # 构建WebSocket URI
            uri = f"ws://{host_formatted}:{port}"
            logger.info(f"正在连接到: {uri}")
            
            # 连接服务器
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10  # 添加关闭超时
            )
            
            self.connected = True
            self.running = True
            self.reconnect_attempts = 0
            
            logger.info(f"已连接到服务器: {host}:{port}")
            
            # 触发连接回调
            if self.on_connected_callback:
                self.on_connected_callback()
            
            # 发送认证请求
            await self._authenticate()
            
            # 开始接收消息
            await self._receive_messages()
            
            return True
        
        except asyncio.CancelledError:
            # 任务被取消
            logger.debug("连接任务被取消")
            self.connected = False
            raise
        
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            self.connected = False
            
            # 触发错误回调
            if self.on_error_callback:
                self.on_error_callback(f"连接失败: {str(e)}")
            
            # 自动重连
            if self.auto_reconnect and self.reconnect_attempts < self.max_reconnect_attempts and self.running:
                await self._try_reconnect()
            
            return False
    
    def connect_in_thread(self, host: str, port: int, nickname: str, verification_code: str) -> bool:
        """在独立线程中连接服务器"""
        try:
            def run_client():
                try:
                    self.loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.loop)
                    
                    # 连接服务器
                    self.loop.run_until_complete(
                        self.connect(host, port, nickname, verification_code)
                    )
                except RuntimeError as e:
                    # 事件循环被停止时的正常情况
                    if "Event loop stopped" in str(e):
                        logger.debug("事件循环已停止")
                    else:
                        logger.error(f"运行客户端时出错: {e}")
                except Exception as e:
                    logger.error(f"客户端线程异常: {e}")
                finally:
                    # 确保循环关闭
                    if self.loop and not self.loop.is_closed():
                        self.loop.close()
            
            self.client_thread = threading.Thread(target=run_client, daemon=True)
            self.client_thread.start()
            
            # 等待连接和认证
            import time
            for _ in range(30):  # 最多等待3秒
                if self.authenticated:
                    return True
                time.sleep(0.1)
            
            return self.connected
        
        except Exception as e:
            logger.error(f"在线程中连接服务器失败: {e}")
            return False
    
    async def _authenticate(self):
        """发送认证请求"""
        if not self.running:
            return
            
        auth_data = {
            "type": config.WS_MESSAGE_TYPES["AUTH"],
            "code": self.verification_code,
            "nickname": self.nickname
        }
        
        await self._send_message(auth_data)
        logger.info("已发送认证请求")
    
    async def _receive_messages(self):
        """接收服务器消息"""
        try:
            async for message in self.websocket:
                # 检查是否应该停止
                if not self.running:
                    break
                    
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON消息: {message}")
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            if self.running:  # 只在仍在运行时记录警告
                logger.warning("服务器连接已断开")
                self.connected = False
                
                # 触发断开连接回调
                if self.on_disconnected_callback:
                    self.on_disconnected_callback()
                
                # 尝试重连
                if self.auto_reconnect:
                    await self._try_reconnect()
        
        except websockets.exceptions.ConnectionClosedError as e:
            if self.running:  # 只在仍在运行时记录警告
                logger.warning(f"服务器连接关闭: {e}")
                self.connected = False
                
                # 触发断开连接回调
                if self.on_disconnected_callback:
                    self.on_disconnected_callback()
                
                # 尝试重连
                if self.auto_reconnect:
                    await self._try_reconnect()
        
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            logger.debug("接收消息任务被取消")
            raise
        
        except Exception as e:
            if self.running:  # 只在仍在运行时记录错误
                logger.error(f"接收消息时出错: {e}")
            self.connected = False
    
    async def _handle_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        if not self.running:
            return
            
        msg_type = data.get("type")
        
        if msg_type == config.WS_MESSAGE_TYPES["AUTH_SUCCESS"]:
            # 认证成功
            self.authenticated = True
            self.nickname = data.get("nickname", self.nickname)  # 可能被服务器修改
            self.srt_port = data.get("srt_port")
            self.server_ip = data.get("server_ip")
            
            logger.info(f"认证成功: {self.nickname}")
            logger.info(f"SRT端口: {self.srt_port}")
            
            # 触发认证成功回调
            if self.on_authenticated_callback:
                self.on_authenticated_callback(self.server_ip, self.srt_port)
        
        elif msg_type == config.WS_MESSAGE_TYPES["AUTH_FAILED"]:
            # 认证失败
            error_msg = data.get("message", "认证失败")
            logger.error(f"认证失败: {error_msg}")
            
            # 触发错误回调
            if self.on_error_callback:
                self.on_error_callback(error_msg)
            
            # 断开连接
            await self.disconnect()
        
        elif msg_type == config.WS_MESSAGE_TYPES["CHAT"]:
            # 聊天消息
            nickname = data.get("nickname")
            message = data.get("message")
            
            # 触发消息回调
            if self.on_message_callback:
                self.on_message_callback(nickname, message)
        
        elif msg_type == config.WS_MESSAGE_TYPES["JOIN"]:
            # 用户加入
            nickname = data.get("nickname")
            message = data.get("message")
            
            # 作为系统消息处理
            if self.on_message_callback:
                self.on_message_callback("系统", message)
        
        elif msg_type == config.WS_MESSAGE_TYPES["LEAVE"]:
            # 用户离开
            nickname = data.get("nickname")
            message = data.get("message")
            
            # 作为系统消息处理
            if self.on_message_callback:
                self.on_message_callback("系统", message)
        
        elif msg_type == config.WS_MESSAGE_TYPES["MEMBERS"]:
            # 成员列表更新
            members = data.get("members", [])
            
            # 触发成员更新回调
            if self.on_member_update_callback:
                self.on_member_update_callback(members)
        
        elif msg_type == config.WS_MESSAGE_TYPES["ERROR"]:
            # 错误消息
            error_msg = data.get("message", "未知错误")
            logger.error(f"服务器错误: {error_msg}")
            
            # 触发错误回调
            if self.on_error_callback:
                self.on_error_callback(error_msg)
        
        elif msg_type == config.WS_MESSAGE_TYPES["HEARTBEAT"]:
            # 心跳响应
            logger.debug("收到心跳响应")
        
        else:
            logger.warning(f"未知消息类型: {msg_type}")
    
    async def send_chat_message(self, message: str):
        """发送聊天消息"""
        if not self.authenticated or not self.running:
            logger.debug("未认证或正在关闭，无法发送消息")
            return
        
        chat_data = {
            "type": config.WS_MESSAGE_TYPES["CHAT"],
            "message": message
        }
        
        await self._send_message(chat_data)
    
    def send_chat_message_sync(self, message: str):
        """同步发送聊天消息（供UI线程调用）"""
        if self.loop and self.authenticated and not self.loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self.send_chat_message(message),
                    self.loop
                )
            except Exception as e:
                logger.debug(f"发送聊天消息时出错: {e}")
    
    async def _send_message(self, data: Dict[str, Any]):
        """发送消息到服务器"""
        if not self.websocket or not self.connected or not self.running:
            logger.debug("未连接到服务器或正在关闭，跳过发送消息")
            return
        
        try:
            message = json.dumps(data, ensure_ascii=False)
            await self.websocket.send(message)
        except Exception as e:
            if self.running:  # 只在运行中时记录错误
                logger.error(f"发送消息失败: {e}")
    
    async def _send_heartbeat(self):
        """发送心跳包"""
        while self.running and self.connected:
            try:
                await asyncio.sleep(30)  # 每30秒发送一次心跳
                
                if self.authenticated and self.running:
                    await self._send_message({
                        "type": config.WS_MESSAGE_TYPES["HEARTBEAT"]
                    })
                    logger.debug("发送心跳包")
            
            except asyncio.CancelledError:
                # 任务被取消
                logger.debug("心跳任务被取消")
                break
            except Exception as e:
                logger.error(f"发送心跳包失败: {e}")
                break
    
    async def _try_reconnect(self):
        """尝试重新连接"""
        if not self.auto_reconnect or not self.running:
            return
        
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"达到最大重连次数({self.max_reconnect_attempts})，停止重连")
            
            # 触发错误回调
            if self.on_error_callback:
                self.on_error_callback("无法连接到服务器")
            return
        
        logger.info(f"将在{self.reconnect_interval}秒后尝试重连... (第{self.reconnect_attempts}次)")
        
        # 等待期间检查运行状态
        for _ in range(int(self.reconnect_interval * 10)):
            if not self.running:
                logger.debug("重连被取消")
                return
            await asyncio.sleep(0.1)
        
        if self.running:
            await self.connect(
                self.server_host,
                self.server_port,
                self.nickname,
                self.verification_code
            )
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        self.auto_reconnect = False  # 主动断开时不自动重连
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"关闭websocket时出错: {e}")
            finally:
                self.websocket = None
        
        self.connected = False
        self.authenticated = False
        
        logger.debug("已断开与服务器的连接")
    
    def disconnect_sync(self):
        """同步断开连接（供UI线程调用）"""
        if self.loop and self.connected and not self.loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.disconnect(),
                    self.loop
                )
                # 等待断开完成，最多1秒
                future.result(timeout=1.0)
            except Exception as e:
                logger.debug(f"同步断开连接时出错: {e}")
    
    def stop(self):
        """停止客户端"""
        self.running = False
        self.auto_reconnect = False
        
        # 先断开连接
        if self.websocket and self.connected:
            if self.loop and not self.loop.is_closed():
                # 创建断开连接的任务
                future = asyncio.run_coroutine_threadsafe(
                    self._disconnect_async(),
                    self.loop
                )
                try:
                    # 等待断开完成，最多1秒
                    future.result(timeout=1.0)
                except Exception as e:
                    logger.debug(f"断开连接时出错: {e}")
        
        # 停止事件循环
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
            
            # 等待循环实际停止
            import time
            max_wait = 10  # 最多等待1秒
            while self.loop.is_running() and max_wait > 0:
                time.sleep(0.1)
                max_wait -= 1
        
        # 等待线程结束
        if self.client_thread and self.client_thread.is_alive():
            self.client_thread.join(timeout=2)
        
        # 关闭事件循环
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.close()
            except Exception as e:
                logger.debug(f"关闭事件循环时出错: {e}")
        
        logger.debug("WebSocket客户端已停止")
    
    async def _disconnect_async(self):
        """异步断开连接（内部使用）"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            self.connected = False
            self.authenticated = False
        except Exception as e:
            logger.debug(f"异步断开连接时出错: {e}")
    
    # 回调函数设置器
    def set_on_connected_callback(self, callback: Callable):
        """设置连接成功回调"""
        self.on_connected_callback = callback
    
    def set_on_disconnected_callback(self, callback: Callable):
        """设置断开连接回调"""
        self.on_disconnected_callback = callback
    
    def set_on_authenticated_callback(self, callback: Callable):
        """设置认证成功回调"""
        self.on_authenticated_callback = callback
    
    def set_on_message_callback(self, callback: Callable):
        """设置消息回调"""
        self.on_message_callback = callback
    
    def set_on_member_update_callback(self, callback: Callable):
        """设置成员更新回调"""
        self.on_member_update_callback = callback
    
    def set_on_error_callback(self, callback: Callable):
        """设置错误回调"""
        self.on_error_callback = callback
    
    def cleanup(self):
        """清理资源"""
        try:
            self.stop()
        except Exception as e:
            logger.debug(f"清理资源时出错: {e}")