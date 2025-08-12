# 在线放映室 (Online Theater With Chat Room)

一个基于Python开发的实时视频流分享和聊天室应用，支持SRT/RTMP协议的视频流传输。

## ✨ 功能特性

-  **视频流分享**：支持通过SRT协议接收本地或远程OBS推流到RTMP服务，并通过SRT协议分发给多个观看者
-  **实时聊天室**：内置聊天室功能，支持emoji表情
-  **IPv6支持**：优先支持IPv6网络，同时兼容IPv4
-  **多用户支持**：支持多个接收端同时观看
-  **验证码保护**：通过6位数字验证码控制访问权限

## 可支持的安全性扩展
-  **视频流保护**: RTMP服务不暴露，当一个客户端连接时会单独开启一个SRT端口专供此连接，并且SRT本身可选加密流
-  **WebSocket**: 可以使用wss来替代现有的ws服务，使用TLS加密连接与聊天信息

## 📋 系统要求

### 运行环境
- Python 3.8+ (开发与测试环境：3.13)
- Windows 10/11 (主要支持)
- 8GB+ RAM
- 稳定的网络连接

### Python依赖
- PySide6 >= 6.5.0 (Qt GUI框架)
- websockets >= 11.0 (WebSocket通信)
- netifaces >= 0.11.0 (网络接口)
- psutil >= 5.9.5 (进程管理)

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/TamakiIroha3/Online-Theatre-With-Chat-Room.git
cd Online-Theatre-With-Chat-Room
```

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 3. 下载外部程序

#### FFmpeg (必需)
- 下载地址：https://www.gyan.dev/ffmpeg/builds/
- 选择 "release builds" 的 "full" 版本
- 解压后将 `ffmpeg.exe` 复制到项目根目录

#### MPV播放器 (必需)
- 下载地址：https://sourceforge.net/projects/mpv-player-windows/
- Windows: 下载 Windows builds
- 将 `mpv.exe` 和 `mpv.com` 复制到项目根目录
- 如有 `d3dcompiler_43.dll` 也一并复制

#### Nginx-RTMP (必需)
- Windows版下载：https://github.com/illuspas/nginx-rtmp-win32
- 解压后将整个nginx文件夹放到项目的 `rtmp/` 目录
- 确保路径为 `./rtmp/nginx.exe`

### 4. 目录结构验证

确保项目目录结构如下：
```
online_theater/
├── main.py                 # 主程序
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── ffmpeg.exe            # [需下载] FFmpeg可执行文件
├── mpv.exe              # [需下载] MPV播放器
├── mpv.com              # [需下载] MPV命令行接口
├── d3dcompiler_43.dll   # [可选] D3D编译器
├── rtmp/
│   └── nginx.exe        # [需下载] Nginx-RTMP服务器
├── ui/                  # UI模块目录
├── network/             # 网络模块目录
├── streaming/           # 流媒体模块目录
├── utils/               # 工具模块目录
└── logs/                # [自动创建] 日志目录
```

### 5. 启动程序

#### Windows用户
双击运行 `start.bat` 或在命令行执行：
```bash
python main.py
```

#### Linux/macOS用户
```bash
python3 main.py
```

## 📖 使用指南

### 发送端（主播）操作流程

1. **启动程序**，选择【发送端】

2. **配置网络参数**：
   - **绑定IP**：选择网络接口（推荐IPv6，默认0.0.0.0监听所有）
   - **SRT端口**：用于接收OBS推流（默认9001）
   - **WebSocket端口**：用于聊天服务（默认10086）
   - **昵称**：您的显示名称（随机Fate角色名）
   - **验证码**：6位数字，分享给观看者（默认114514）
   - **本地播放**：~~是否在本地也播放视频~~ 服务端本地播放建议直接用VLC/MPV播放rtmp://localhost/live/stream

3. **点击【确认】**启动服务
   - 程序会自动启动Nginx RTMP服务器
   - FFmpeg开始监听SRT端口
   - ~~MPV播放器开始循环尝试连接RTMP流~~ 如果需要建议在启动OBS推流后手动开启播放

4. **配置OBS推流**：
   - 设置 -> 推流
   - 服务：自定义
   - 服务器： `srt://[绑定的IP]:9001` 
   - 串流密钥：留空

5. **开始推流**，MPV会自动检测到流并开始播放

### 接收端（观众）操作流程

1. **启动程序**，选择【接收端】

2. **输入连接信息**：
   - **服务器IP**：发送端的IP地址（支持IPv4/IPv6）
   - **服务器端口**：WebSocket端口（默认10086）
   - **昵称**：您的聊天室显示名称
   - **验证码**：从发送端获取的6位验证码

3. **点击【连接】**加入放映室
   - 自动进入聊天室
   - 数秒后自动启动播放器

### OBS推流设置建议

#### 输出设置
- **编码器**：x264 或 NVENC/AMF/QuickSync H264（硬件编码） 如果你用的RTMP支持HEVC扩展也可以使用HEVC
- **速率控制**：CBR（恒定比特率）
- **比特率**：3000-8000 Kbps（根据网络调整）
- **关键帧间隔**：1-2 秒
- **CPU使用预设**：veryfast 或 faster
- **配置文件**：high
- **调整**：zerolatency（零延迟）

#### 音频设置
- **音频比特率**：128-192 Kbps
- **采样率**：44.1 kHz 或 48 kHz
- **声道**：立体声

#### 视频设置
- **基础分辨率**：1920x1080 或您的屏幕分辨率
- **输出分辨率**：1920x1080 或 1280x720
- **下采样过滤器**：Lanczos
- **FPS**：30 或 60

## ⚙️ 配置文件说明

主要配置项在 `config.py` 中：

```python
# 网络默认配置
NETWORK_DEFAULTS = {
    "srt_input_port": 9001,      # SRT输入端口
    "websocket_port": 10086,     # WebSocket端口
    "verification_code": "114514", # 默认验证码
    "enable_local_play": True,    # 默认开启本地播放
}

# MPV重试配置
MPV_PARAMS = {
    "retry": {
        "sender_interval": 3,     # 发送端重试间隔（秒）
        "receiver_delay": 2       # 接收端启动延迟（秒）
    }
}
```

## 📊 日志系统

### 日志文件位置
- **主程序日志**：`logs/online_theater.log`
- **FFmpeg日志**：`logs/ffmpeg/[进程名]_[时间戳].log`

### 日志级别
- 控制台：只显示WARNING及以上级别
- 文件：记录所有详细信息

## 🔧 故障排除

### 常见问题

#### 1. 连接失败
- 检查防火墙设置，确保相应端口已开放
- Windows防火墙：允许程序通过防火墙
- 路由器：如需外网访问，配置端口转发

#### 2. OBS推流失败
- 确认SRT地址格式正确：`srt://IP:端口`
- 检查发送端是否正常运行
- 查看 `logs/ffmpeg/` 目录下的日志

#### 3. MPV无法播放
- 发送端：~~MPV会持续尝试连接~~，等待OBS推流后自行用任意软件播放rtmp://localhost/live/stream
- 接收端：检查网络连接，确认服务器地址正确
- 查看控制台输出的错误信息

#### 4. 程序无法启动
- 确认Python版本 >= 3.8
- 确认所有依赖已安装：`pip install -r requirements.txt`
- 确认外部程序（ffmpeg.exe, mpv.exe, nginx.exe）存在

#### 5. 验证码错误
- 确认输入的是6位数字
- 检查是否与发送端设置的验证码一致

### 端口占用问题

如果提示端口被占用，可以：
1. 更改配置文件中的默认端口
2. 或使用命令查找占用端口的程序：
   ```bash
   # Windows
   netstat -ano | findstr :9001
   
   ```

## 🛡️ 安全建议

1. **验证码**：使用复杂的验证码，避免未授权访问
2. **防火墙**：仅开放必要的端口
3. **配置加密信息**：使用SRT自带的加密来保护视频流，用TLS加密WebSocket
4. **定期更新**：保持程序和依赖的更新

## 📦 项目结构

```
online_theater/
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── .gitignore            # Git忽略文件
├── README.md             # 项目说明
├── start.bat             # Windows启动脚本
├── ui/                   # 用户界面模块
│   ├── __init__.py
│   ├── main_window.py    # 主窗口
│   ├── sender_setup.py   # 发送端设置
│   ├── receiver_setup.py # 接收端设置
│   └── chat_room.py      # 聊天室界面
├── network/              # 网络模块
│   ├── __init__.py
│   ├── websocket_server.py # WebSocket服务器
│   └── websocket_client.py # WebSocket客户端
├── streaming/            # 流媒体模块
│   ├── __init__.py
│   ├── ffmpeg_manager.py # FFmpeg管理
│   ├── mpv_player.py     # MPV播放器管理
│   └── nginx_manager.py  # Nginx管理
└── utils/                # 工具模块
    ├── __init__.py
    ├── logger.py         # 日志管理
    ├── network_utils.py  # 网络工具
    └── process_manager.py # 进程管理
```

## 🔄 更新日志

### v1.0.1 (2025-08-12)
- 🎯 使用QTimer实现客户端MPV延迟启动
- 🔄 发送端MPV无限循环等待OBS推流
- 📝 优化日志输出，FFmpeg日志只写入文件
- 🐛 修复WebSocket客户端关闭时的异常
- 🎨 修复聊天室emoji显示和消息换行问题
- 🔧 添加更多配置选项

### v1.0.0 (2025-08-10)
- 🎉 初始版本发布
- ✨ 支持SRT/RTMP流转发
- 💬 WebSocket聊天室
- 🌐 IPv6优先支持
- 👥 多客户端支持

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交Issue和Pull Request！

## 🙏 致谢

- FFmpeg - 强大的多媒体框架
- MPV - 优秀的媒体播放器
- Nginx-RTMP - 稳定的流媒体服务器
- PySide6 - Qt for Python
- Claude 最好的Vibe Coding模型

## 📞 联系方式

- GitHub Issues: [提交问题](https://github.com/TamakiIroha3/Online-Theatre-With-Chat-Room/issues)
- Email: 478065832@qq.com

---

**注意**：本项目仅供学习和个人使用，请遵守相关法律法规。
