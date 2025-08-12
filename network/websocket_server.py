# network/websocket_server.py - WebSocket服务器
import asyncio
import websockets
import json
import threading
from typing import Dict, Set, Optional, Any, Callable
from datetime import datetime
import config
from utils.logger import get_logger
from utils.network_utils import NetworkUtils
from streaming.ffmpeg_manager import FFmpegManager

logger = get_logger(__name__)

class WebSocketServer:
    """WebSocket服务器（发送端使用）"""
    
    def __init__(self, verification_code: str = None):
        """
        初始化WebSocket服务器
        Args:
            verification_code: 验证码
        """
        self.verification_code = verification_code or config.NETWORK_DEFAULTS["verification_code"]
        self.clients: Dict[str, Dict[str, Any]] = {}  # client_id -> client_info
        self.nicknames: Set[str] = set()  # 已使用的昵称
        self.server = None
        self.loop = None
        self.server_thread = None
        self.running = False
        self.ffmpeg_manager = FFmpegManager()
        self.next_srt_port = config.NETWORK_DEFAULTS["srt_base_port"]
        self.bind_ip = "0.0.0.0"
        self.port = config.NETWORK_DEFAULTS["websocket_port"]
        
        # 发送端自己的信息
        self.sender_nickname = None
        self.sender_id = "sender"
        
        # 回调函数
        self.on_message_callback: Optional[Callable] = None
        self.on_member_update_callback: Optional[Callable] = None
    
    async def start(self, host: str, port: int, sender_nickname: str) -> bool:
        """
        启动WebSocket服务器
        Args:
            host: 绑定地址
            port: 端口
            sender_nickname: 发送端昵称
        """
        try:
            self.bind_ip = host
            self.port = port
            self.sender_nickname = sender_nickname
            self.nicknames.add(sender_nickname)  # 添加发送端昵称
            
            # 处理IPv6地址
            if NetworkUtils.is_valid_ipv6(host):
                # WebSocket服务器绑定时不需要方括号
                host = host.strip('[]')
            
            # 创建服务器
            self.server = await websockets.serve(
                self.handle_client,
                host,
                port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10  # 添加关闭超时
            )
            
            self.running = True
            logger.info(f"WebSocket服务器已启动: {host}:{port}")
            
            # 通知回调：发送端加入
            if self.on_member_update_callback:
                await self._notify_member_update()
            
            return True
        
        except Exception as e:
            logger.error(f"启动WebSocket服务器失败: {e}")
            return False
    
    def start_in_thread(self, host: str, port: int, sender_nickname: str) -> bool:
        """在独立线程中启动服务器"""
        try:
            def run_server():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                # 启动服务器
                self.loop.run_until_complete(self.start(host, port, sender_nickname))
                
                # 运行事件循环
                self.loop.run_forever()
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # 等待服务器启动
            import time
            time.sleep(1)
            
            return self.running
        
        except Exception as e:
            logger.error(f"在线程中启动WebSocket服务器失败: {e}")
            return False
    
    async def handle_client(self, websocket):
        """处理客户端连接"""
        client_id = f"client_{id(websocket)}"
        # 如果需要，可以获取路径信息: path = websocket.path
        client_info = {
            "websocket": websocket,
            "authenticated": False,
            "nickname": None,
            "srt_port": None,
            "connected_time": datetime.now(),
            "remote_address": websocket.remote_address if hasattr(websocket, 'remote_address') else None
        }
        
        try:
            # 获取客户端地址信息
            remote_addr = websocket.remote_address if hasattr(websocket, 'remote_address') else "unknown"
            logger.info(f"新客户端连接: {client_id} 来自 {remote_addr}")
            
            # 等待认证
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if not client_info["authenticated"]:
                        # 处理认证
                        if msg_type == config.WS_MESSAGE_TYPES["AUTH"]:
                            await self._handle_auth(client_id, client_info, data)
                        else:
                            await self._send_error(websocket, "请先进行身份验证")
                    else:
                        # 处理已认证客户端的消息
                        if msg_type == config.WS_MESSAGE_TYPES["CHAT"]:
                            await self._handle_chat(client_id, data)
                        elif msg_type == config.WS_MESSAGE_TYPES["HEARTBEAT"]:
                            await websocket.send(json.dumps({"type": config.WS_MESSAGE_TYPES["HEARTBEAT"]}))
                        else:
                            logger.warning(f"未知消息类型: {msg_type}")
                
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON消息: {message}")
                    await self._send_error(websocket, "消息格式错误")
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端断开连接: {client_id}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"客户端连接关闭: {client_id} - {e}")
        except Exception as e:
            logger.error(f"处理客户端时出错: {e}")
        finally:
            # 清理断开的客户端
            await self._cleanup_client(client_id)
    
    async def _handle_auth(self, client_id: str, client_info: Dict, data: Dict):
        """处理认证请求"""
        code = data.get("code")
        nickname = data.get("nickname")
        websocket = client_info["websocket"]
        
        # 验证验证码
        if code != self.verification_code:
            await self._send_message(websocket, {
                "type": config.WS_MESSAGE_TYPES["AUTH_FAILED"],
                "message": "验证码错误"
            })
            await websocket.close()
            return
        
        # 检查昵称是否重复
        if nickname in self.nicknames:
            # 为昵称添加数字后缀
            original_nickname = nickname
            counter = 2
            while f"{original_nickname}_{counter}" in self.nicknames:
                counter += 1
            nickname = f"{original_nickname}_{counter}"
            logger.info(f"昵称重复，自动更改为: {nickname}")
        
        # 分配SRT端口
        srt_port = self._allocate_srt_port()
        if srt_port is None:
            await self._send_error(websocket, "无法分配SRT端口")
            await websocket.close()
            return
        
        # 启动RTMP到SRT转换
        rtmp_url = f"rtmp://127.0.0.1:{config.NGINX_CONFIG['rtmp']['port']}/live/stream"
        success = self.ffmpeg_manager.start_rtmp_to_srt(
            rtmp_url=rtmp_url,
            srt_port=srt_port,
            bind_ip=self.bind_ip,
            process_name=f"client_{nickname}_{srt_port}"
        )
        
        if not success:
            await self._send_error(websocket, "无法启动流转发服务")
            await websocket.close()
            return
        
        # 认证成功
        client_info["authenticated"] = True
        client_info["nickname"] = nickname
        client_info["srt_port"] = srt_port
        
        self.clients[client_id] = client_info
        self.nicknames.add(nickname)
        
        # 发送认证成功消息
        await self._send_message(websocket, {
            "type": config.WS_MESSAGE_TYPES["AUTH_SUCCESS"],
            "nickname": nickname,
            "srt_port": srt_port,
            "server_ip": self.bind_ip
        })
        
        # 广播用户加入消息
        await self._broadcast_message({
            "type": config.WS_MESSAGE_TYPES["JOIN"],
            "nickname": nickname,
            "message": f"{nickname} 加入了放映室"
        })
        
        # 发送成员列表
        await self._send_members_list(websocket)
        
        # 通知回调
        if self.on_member_update_callback:
            await self._notify_member_update()
        
        logger.info(f"客户端认证成功: {nickname} (SRT端口: {srt_port})")
    
    async def _handle_chat(self, client_id: str, data: Dict):
        """处理聊天消息"""
        if client_id not in self.clients:
            return
        
        client_info = self.clients[client_id]
        nickname = client_info["nickname"]
        message = data.get("message", "")
        
        # 广播聊天消息
        chat_data = {
            "type": config.WS_MESSAGE_TYPES["CHAT"],
            "nickname": nickname,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_message(chat_data)
        
        # 通知回调（不重复显示）
        if self.on_message_callback:
            self.on_message_callback(nickname, message)
    
    async def send_chat_message(self, message: str):
        """发送端发送聊天消息"""
        if not self.sender_nickname:
            return
        
        chat_data = {
            "type": config.WS_MESSAGE_TYPES["CHAT"],
            "nickname": self.sender_nickname,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # 广播给所有客户端
        await self._broadcast_message(chat_data)
        
        # 通知回调显示在自己的聊天框
        if self.on_message_callback:
            self.on_message_callback(self.sender_nickname, message)
    
    def send_chat_message_sync(self, message: str):
        """同步发送聊天消息（供UI线程调用）"""
        if self.loop and self.running:
            asyncio.run_coroutine_threadsafe(
                self.send_chat_message(message),
                self.loop
            )
    
    async def _cleanup_client(self, client_id: str):
        """清理断开的客户端"""
        if client_id not in self.clients:
            return
        
        client_info = self.clients[client_id]
        nickname = client_info["nickname"]
        srt_port = client_info["srt_port"]
        
        # 停止FFmpeg进程
        if srt_port:
            process_name = f"client_{nickname}_{srt_port}"
            self.ffmpeg_manager.stop_process(process_name)
        
        # 移除客户端记录
        del self.clients[client_id]
        if nickname:
            self.nicknames.discard(nickname)
        
        # 广播用户离开消息
        if nickname:
            await self._broadcast_message({
                "type": config.WS_MESSAGE_TYPES["LEAVE"],
                "nickname": nickname,
                "message": f"{nickname} 离开了放映室"
            })
        
        # 通知回调
        if self.on_member_update_callback:
            await self._notify_member_update()
        
        logger.debug(f"客户端已清理: {nickname}")
    
    async def _broadcast_message(self, data: Dict):
        """广播消息给所有已认证的客户端"""
        message = json.dumps(data, ensure_ascii=False)
        
        # 收集所有需要发送的任务
        tasks = []
        for client_info in self.clients.values():
            if client_info["authenticated"]:
                websocket = client_info["websocket"]
                tasks.append(self._send_raw_message(websocket, message))
        
        # 并发发送
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_message(self, websocket, data: Dict):
        """发送消息给指定客户端"""
        try:
            message = json.dumps(data, ensure_ascii=False)
            await websocket.send(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def _send_raw_message(self, websocket, message: str):
        """发送原始消息"""
        try:
            await websocket.send(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def _send_error(self, websocket, error_message: str):
        """发送错误消息"""
        await self._send_message(websocket, {
            "type": config.WS_MESSAGE_TYPES["ERROR"],
            "message": error_message
        })
    
    async def _send_members_list(self, websocket):
        """发送成员列表"""
        members = self.get_online_members()
        await self._send_message(websocket, {
            "type": config.WS_MESSAGE_TYPES["MEMBERS"],
            "members": members
        })
    
    async def _notify_member_update(self):
        """通知成员列表更新"""
        members = self.get_online_members()
        
        # 广播成员列表更新
        await self._broadcast_message({
            "type": config.WS_MESSAGE_TYPES["MEMBERS"],
            "members": members
        })
        
        # 触发回调
        if self.on_member_update_callback:
            try:
                self.on_member_update_callback(members)
            except Exception as e:
                logger.error(f"执行成员更新回调时出错: {e}")
    
    def get_online_members(self) -> list:
        """获取在线成员列表"""
        members = []
        
        # 添加发送端
        if self.sender_nickname:
            members.append({
                "nickname": self.sender_nickname,
                "role": "sender"
            })
        
        # 添加所有客户端
        for client_info in self.clients.values():
            if client_info["authenticated"] and client_info["nickname"]:
                members.append({
                    "nickname": client_info["nickname"],
                    "role": "receiver"
                })
        
        return members
    
    def _allocate_srt_port(self) -> Optional[int]:
        """分配可用的SRT端口"""
        port = NetworkUtils.find_available_port(self.next_srt_port)
        if port:
            self.next_srt_port = port + 1
        return port
    
    def set_on_message_callback(self, callback: Callable):
        """设置消息回调"""
        self.on_message_callback = callback
    
    def set_on_member_update_callback(self, callback: Callable):
        """设置成员更新回调"""
        self.on_member_update_callback = callback
    
    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 停止所有FFmpeg进程
        self.ffmpeg_manager.stop_all()
        
        if self.server:
            self.server.close()
        
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.server_thread:
            self.server_thread.join(timeout=2)
        
        logger.debug("WebSocket服务器已停止")
    
    def cleanup(self):
        """清理资源"""
        self.stop()
        self.ffmpeg_manager.cleanup()