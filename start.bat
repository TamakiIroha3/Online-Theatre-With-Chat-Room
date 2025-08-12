@echo off
chcp 65001 >nul
title 在线放映室

echo ========================================
echo     在线放映室 - Online Theater
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查必要文件
if not exist "ffmpeg.exe" (
    echo [警告] 未找到 ffmpeg.exe
    echo 请下载ffmpeg并放置在当前目录
    echo.
)

if not exist "mpv.exe" (
    echo [警告] 未找到 mpv.exe
    echo 请下载mpv并放置在当前目录
    echo.
)

if not exist "rtmp\nginx.exe" (
    echo [警告] 未找到 rtmp\nginx.exe
    echo 请下载带RTMP模块的nginx并放置在rtmp目录
    echo.
)

REM 检查并安装依赖
echo 正在检查Python依赖...
pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo 首次运行，正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo 依赖安装完成！
    echo.
)

REM 创建必要的目录
if not exist "logs" mkdir logs
if not exist "logs\ffmpeg" mkdir logs\ffmpeg

REM 启动主程序
echo 正在启动在线放映室...
echo ----------------------------------------
python main.py
pause
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)

exit /b 0