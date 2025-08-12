# config.py - 在线放映室配置文件
import random
import os

# 应用基本信息
APP_NAME = "在线放映室"
VERSION = "1.0.1"

# 界面主题配置
THEME = {
    "style": "Fusion",  # Qt风格
    "dark_mode": True,  # 暗色主题
    "colors": {
        "background": "#1e1e1e",
        "surface": "#2d2d2d", 
        "primary": "#4a9eff",
        "text": "#ffffff",
        "text_secondary": "#b0b0b0",
        "border": "#3d3d3d",
        "success": "#4caf50",
        "error": "#f44336",
        "warning": "#ff9800"
    },
    "fonts": {
        "default": "Microsoft YaHei UI",
        "size_normal": 10,
        "size_small": 9,
        "size_large": 12,
        "size_title": 14
    }
}

# 窗口尺寸配置
WINDOW_SIZES = {
    "main": {"width": 400, "height": 500, "min_width": 350, "min_height": 250},
    "sender_setup": {"width": 500, "height": 450, "min_width": 450, "min_height": 400},
    "receiver_setup": {"width": 450, "height": 400, "min_width": 400, "min_height": 350},
    "chat_room": {"width": 900, "height": 600, "min_width": 800, "min_height": 500}
}

# 角色名称池
ROLE_NAMES = ["Archer", "Saber", "Caster", "Assassin", "Rider", "Lancer", "Berserker"]
RARE_ROLE_NAMES = ["Ruler", "Avenger"]  # 极小概率出现
RARE_ROLE_PROBABILITY = 0.02  # 2%概率出现稀有角色

def get_random_nickname():
    """获取随机昵称"""
    if random.random() < RARE_ROLE_PROBABILITY:
        return random.choice(RARE_ROLE_NAMES)
    return random.choice(ROLE_NAMES)

# 网络默认配置
NETWORK_DEFAULTS = {
    "srt_input_port": 9001,       # SRT视频流输入端口
    "websocket_port": 10086,      # WebSocket监听端口
    "rtmp_port": 1935,            # RTMP端口
    "verification_code": "114514", # 默认验证码
    "srt_base_port": 10000,       # SRT分配端口起始值
    "enable_local_play": True,    # 默认开启本地播放
    "prefer_ipv6": True,          # 优先使用IPv6
    "connection_timeout": 10,     # 连接超时时间(秒)
    "reconnect_interval": 3,      # 重连间隔(秒)
    "max_reconnect_attempts": 5   # 最大重连次数
}

# 外部程序路径
EXTERNAL_PROGRAMS = {
    "ffmpeg": os.path.join(".", "ffmpeg.exe"),
    "mpv": os.path.join(".", "mpv.exe"),
    "nginx": os.path.join(".", "rtmp", "nginx.exe")
}

# FFmpeg参数配置
FFMPEG_PARAMS = {
    # SRT输入接收参数（发送端）
    "srt_input": {
        "mode": "listener",
        "latency": 120,        # 延迟120ms
        "rcvbuf": 10485760,    # 接收缓冲10MB
        "maxbw": -1,           # 不限制带宽
        "timeout": -1,         # 不超时
        "ipttl": 64,          # TTL值
        "iptos": 0x00         # TOS值
    },
    
    # SRT输出参数（客户端分发）
    "srt_output": {
        "mode": "listener",
        "latency": 3000,
        "sndbuf": 10485760,    # 发送缓冲10MB
        "maxbw": -1,
        "timeout": -1
    },
    
    # SRT转RTMP（发送端接收流后推送到本地RTMP）
    "srt_to_rtmp": [
        "-analyzeduration", "10000000",  # 分析时长10秒
        "-probesize", "10000000",        # 探测大小10MB
        "-fflags", "+genpts",            # 生成PTS避免时间戳问题
        "-i", "srt://0.0.0.0:{port}?mode=listener&latency=120",
        "-c", "copy",           # 不转码，只转封装
        "-f", "flv",           # 输出格式为FLV
        "-flvflags", "no_duration_filesize",
        "rtmp://127.0.0.1:1935/live/stream"
    ],
    
    # RTMP转SRT（为每个客户端分发）
    "rtmp_to_srt": [
        "-analyzeduration", "5000000",   # 分析时长5秒（RTMP相对稳定）
        "-probesize", "5000000",         # 探测大小5MB
        "-fflags", "+genpts",            # 生成PTS避免时间戳问题
        "-re",                  # 按原始帧率读取
        "-i", "rtmp://127.0.0.1:1935/live/stream",
        "-c", "copy",           # 不转码，只转封装
        "-f", "mpegts",        # SRT使用MPEG-TS封装
        "srt://0.0.0.0:{port}?mode=listener&latency=120"
    ],
    
    # 通用参数
    "common": [
        "-hide_banner",         # 隐藏版权信息
        "-loglevel", "warning", # 日志级别改为warning，减少输出
        "-stats",              # 显示统计信息
        "-nostdin"             # 不接受标准输入
    ]
}

# MPV参数配置
MPV_PARAMS = {
    # 发送端播放参数（从本地RTMP播放）
    "sender": [
        "--cache=yes",                    # 启用缓存
        "--cache-secs=300",              # 5分钟缓存
        "--demuxer-max-bytes=150M",      # 最大缓冲150MB
        "--demuxer-max-back-bytes=75M",  # 回退缓冲75MB
        "--hwdec=auto",                  # 自动硬件解码
        "--vo=gpu",                      # GPU渲染
        "--gpu-api=auto",                # 自动选择GPU API
        "--video-sync=audio",            # 音视频同步
        "--keep-open=yes",               # 播放结束后保持打开
        "--force-window=yes",            # 强制显示窗口
        "--osc=yes",                     # 显示控制界面
        "--osd-bar=yes",                 # 显示进度条
        "--network-timeout=60",          # 网络超时60秒
        "--stream-lavf-o=rtmp_live=1",  # RTMP直播模式
        "--title=在线放映室 - 发送端"
    ],
    
    # 接收端播放参数（从SRT播放）
    "receiver": [
        "--cache=yes",
        "--cache-secs=300",              # 5分钟缓存
        "--demuxer-max-bytes=150M",
        "--demuxer-max-back-bytes=75M",
        "--hwdec=auto",
        "--vo=gpu",
        "--gpu-api=auto",
        "--video-sync=audio",
        "--keep-open=no",                # 播放结束后关闭
        "--force-window=immediate",
        "--osc=yes",
        "--osd-bar=yes",
        "--network-timeout=60",
        "--demuxer-lavf-o=protocol_whitelist=[srt,crypto,file,rtp,tcp,udp]",
        "--title=在线放映室 - 接收端"
    ],
    
    # 通用参数
    "common": [
        "--input-default-bindings=yes",  # 默认键盘绑定
        "--input-vo-keyboard=yes",       # 键盘控制
        "--sub-auto=fuzzy",              # 自动加载字幕
        "--audio-channels=stereo",       # 立体声
        "--volume=100",                  # 默认音量
        "--volume-max=150",              # 最大音量150%
        "--msg-level=all=info"          # 日志级别
    ],
    
    # 重试配置
    "retry": {
        "sender_interval": 3,            # 发送端重试间隔（秒）
        "receiver_delay": 2              # 接收端启动延迟（秒）
    }
}

# Nginx配置
NGINX_CONFIG = {
    "rtmp": {
        "port": 1935,
        "app_name": "live",
        "stream_key": "stream",
        "chunk_size": 4096,
        "buflen": "5s",
        "allow_publish": "127.0.0.1",
        "deny_publish": "all"
    }
}

# WebSocket消息类型
WS_MESSAGE_TYPES = {
    "AUTH": "auth",                # 认证
    "AUTH_SUCCESS": "auth_success", # 认证成功
    "AUTH_FAILED": "auth_failed",   # 认证失败
    "CHAT": "chat",                # 聊天消息
    "JOIN": "join",                # 用户加入
    "LEAVE": "leave",              # 用户离开
    "MEMBERS": "members",          # 成员列表
    "SRT_PORT": "srt_port",        # SRT端口分配
    "ERROR": "error",              # 错误信息
    "HEARTBEAT": "heartbeat"       # 心跳包
}

# 日志配置
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file_name": "online_theater.log",
    "max_bytes": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
    "encoding": "utf-8"
}

# Emoji列表（常用表情）
EMOJI_LIST = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
    "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔",
    "🤐", "🤨", "😐", "😑", "😶", "😏", "😒", "🙄", "😬", "🤥",
    "😔", "😪", "😴", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", "😵",
    "🤯", "🤠", "😎", "🤓", "🧐", "😕", "😟", "🙁", "☹️", "😮",
    "😯", "😲", "😳", "🥺", "😦", "😧", "😨", "😰", "😥", "😢",
    "😭", "😱", "😖", "😣", "😞", "😓", "😩", "😫", "🥱", "😤",
    "😡", "😠", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👹",
    "👺", "👻", "👽", "👾", "🤖", "🎃", "😺", "😸", "😹", "😻",
    "😼", "😽", "🙀", "😿", "😾", "👋", "🤚", "🖐️", "✋", "🖖",
    "👌", "🤏", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉", "👆",
    "🖕", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛", "🤜", "👏",
    "🙌", "👐", "🤲", "🤝", "🙏", "❤️", "🧡", "💛", "💚", "💙",
    "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕", "💞", "💓", "💗",
    "💖", "💘", "💝", "🌹", "🌺", "🌸", "🌼", "🌻", "🌷", "🥀",
    "🎉", "🎊", "🎈", "🎁", "🎀", "🏆", "🥇", "🥈", "🥉", "🏅",
    "⭐", "🌟", "✨", "💫", "🔥", "💥", "💢", "💦", "💨", "💬"
]

# 错误消息
ERROR_MESSAGES = {
    "connection_failed": "连接失败，请检查网络设置",
    "auth_failed": "验证码错误，请重新输入",
    "port_unavailable": "端口被占用，请更换端口",
    "stream_failed": "视频流启动失败",
    "nickname_duplicate": "昵称已被使用，请更换",
    "server_error": "服务器错误，请稍后重试",
    "network_error": "网络错误，请检查网络连接"
}