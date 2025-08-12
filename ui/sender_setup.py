# ui/sender_setup.py - 发送端设置界面
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QCheckBox,
    QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QIntValidator
import config
from utils.logger import get_logger
from utils.network_utils import NetworkUtils

logger = get_logger(__name__)

class SenderSetupWindow(QMainWindow):
    """发送端设置界面"""
    
    # 信号
    setup_completed = Signal(dict)  # 设置完成信号，传递配置参数
    back_requested = Signal()       # 返回主界面信号
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
        self.load_network_interfaces()
    
    def init_ui(self):
        """初始化UI"""
        # 窗口设置
        self.setWindowTitle(f"{config.APP_NAME} - 发送端设置")
        size = config.WINDOW_SIZES["sender_setup"]
        self.resize(size["width"], size["height"])
        self.setMinimumSize(size["min_width"], size["min_height"])
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("发送端设置")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_title"])
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # 设置表单
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setColumnStretch(1, 1)
        
        row = 0
        
        # 绑定IP地址
        ip_label = QLabel("绑定IP地址:")
        form_layout.addWidget(ip_label, row, 0, Qt.AlignRight)
        
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        self.ip_combo.setMinimumHeight(30)
        form_layout.addWidget(self.ip_combo, row, 1)
        
        row += 1
        
        # SRT监听端口
        srt_label = QLabel("SRT监听端口:")
        form_layout.addWidget(srt_label, row, 0, Qt.AlignRight)
        
        self.srt_port_input = QLineEdit()
        self.srt_port_input.setText(str(config.NETWORK_DEFAULTS["srt_input_port"]))
        self.srt_port_input.setValidator(QIntValidator(1, 65535))
        self.srt_port_input.setMinimumHeight(30)
        self.srt_port_input.setPlaceholderText("1-65535")
        form_layout.addWidget(self.srt_port_input, row, 1)
        
        row += 1
        
        # WebSocket端口
        ws_label = QLabel("WebSocket端口:")
        form_layout.addWidget(ws_label, row, 0, Qt.AlignRight)
        
        self.ws_port_input = QLineEdit()
        self.ws_port_input.setText(str(config.NETWORK_DEFAULTS["websocket_port"]))
        self.ws_port_input.setValidator(QIntValidator(1, 65535))
        self.ws_port_input.setMinimumHeight(30)
        self.ws_port_input.setPlaceholderText("1-65535")
        form_layout.addWidget(self.ws_port_input, row, 1)
        
        row += 1
        
        # 昵称
        nickname_label = QLabel("昵称:")
        form_layout.addWidget(nickname_label, row, 0, Qt.AlignRight)
        
        self.nickname_input = QLineEdit()
        self.nickname_input.setText(config.get_random_nickname())
        self.nickname_input.setMinimumHeight(30)
        self.nickname_input.setMaxLength(20)
        self.nickname_input.setPlaceholderText("输入您的昵称")
        form_layout.addWidget(self.nickname_input, row, 1)
        
        row += 1
        
        # 验证码
        code_label = QLabel("验证码:")
        form_layout.addWidget(code_label, row, 0, Qt.AlignRight)
        
        self.code_input = QLineEdit()
        self.code_input.setText(config.NETWORK_DEFAULTS["verification_code"])
        self.code_input.setMinimumHeight(30)
        self.code_input.setMaxLength(6)
        self.code_input.setPlaceholderText("6位数字验证码")
        form_layout.addWidget(self.code_input, row, 1)
        
        row += 1
        
        # 本地播放选项
        self.local_play_checkbox = QCheckBox("开启本地播放")
        self.local_play_checkbox.setChecked(config.NETWORK_DEFAULTS["enable_local_play"])
        form_layout.addWidget(self.local_play_checkbox, row, 1)
        
        main_layout.addWidget(form_widget)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 提示信息
        info_label = QLabel("提示：确保防火墙已允许相应端口的访问")
        info_label.setAlignment(Qt.AlignCenter)
        info_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_small"])
        info_label.setFont(info_font)
        info_label.setStyleSheet(f"color: {config.THEME['colors']['text_secondary']};")
        main_layout.addWidget(info_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 返回按钮
        self.back_button = QPushButton("返回")
        self.back_button.setMinimumHeight(35)
        self.back_button.clicked.connect(self.on_back_clicked)
        button_layout.addWidget(self.back_button)
        
        button_layout.addStretch()
        
        # 确认按钮
        self.confirm_button = QPushButton("确认")
        self.confirm_button.setMinimumHeight(35)
        self.confirm_button.setObjectName("primary_button")
        self.confirm_button.clicked.connect(self.on_confirm_clicked)
        button_layout.addWidget(self.confirm_button)
        
        main_layout.addLayout(button_layout)
    
    def apply_theme(self):
        """应用主题"""
        colors = config.THEME["colors"]
        fonts = config.THEME["fonts"]
        
        stylesheet = f"""
            QMainWindow {{
                background-color: {colors['background']};
            }}
            
            QLabel {{
                color: {colors['text']};
                font-size: {fonts['size_normal']}px;
            }}
            
            QLineEdit, QComboBox {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 5px 10px;
                font-size: {fonts['size_normal']}px;
            }}
            
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {colors['primary']};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {colors['text']};
                margin-right: 5px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {colors['surface']};
                color: {colors['text']};
                selection-background-color: {colors['primary']};
                border: 1px solid {colors['border']};
            }}
            
            QCheckBox {{
                color: {colors['text']};
                font-size: {fonts['size_normal']}px;
                spacing: 8px;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {colors['border']};
                border-radius: 3px;
                background-color: {colors['surface']};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {colors['primary']};
                border-color: {colors['primary']};
            }}
            
            QPushButton {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 8px 20px;
                font-size: {fonts['size_normal']}px;
            }}
            
            QPushButton:hover {{
                background-color: {colors['border']};
            }}
            
            QPushButton:pressed {{
                background-color: {colors['background']};
            }}
            
            QPushButton#primary_button {{
                background-color: {colors['primary']};
                color: white;
                border: none;
            }}
            
            QPushButton#primary_button:hover {{
                background-color: #5aa6ff;
            }}
            
            QFrame {{
                background-color: {colors['border']};
            }}
        """
        
        self.setStyleSheet(stylesheet)
    
    def load_network_interfaces(self):
        """加载网络接口列表"""
        try:
            # 获取所有IP地址
            ip_list = NetworkUtils.get_all_ip_addresses()
            
            # 清空下拉框
            self.ip_combo.clear()
            
            # 添加默认选项
            self.ip_combo.addItem("0.0.0.0 (所有接口)")
            
            # 添加IPv6和IPv4地址
            ipv6_addresses = []
            ipv4_addresses = []
            
            for ip, interface in ip_list:
                if ':' in ip:  # IPv6
                    ipv6_addresses.append(f"{ip} - {interface}")
                else:  # IPv4
                    ipv4_addresses.append(f"{ip} - {interface}")
            
            # 优先添加IPv6地址
            if config.NETWORK_DEFAULTS["prefer_ipv6"]:
                for addr in ipv6_addresses:
                    self.ip_combo.addItem(addr)
                for addr in ipv4_addresses:
                    self.ip_combo.addItem(addr)
            else:
                for addr in ipv4_addresses:
                    self.ip_combo.addItem(addr)
                for addr in ipv6_addresses:
                    self.ip_combo.addItem(addr)
            
            # 尝试设置公网IPv6为默认
            public_ipv6 = NetworkUtils.get_public_ipv6()
            if public_ipv6:
                for i in range(self.ip_combo.count()):
                    if public_ipv6 in self.ip_combo.itemText(i):
                        self.ip_combo.setCurrentIndex(i)
                        break
        
        except Exception as e:
            logger.error(f"加载网络接口失败: {e}")
            self.ip_combo.addItem("127.0.0.1 (本地)")
    
    def validate_input(self) -> bool:
        """验证输入"""
        # 验证IP地址
        ip_text = self.ip_combo.currentText()
        ip = ip_text.split(' ')[0]  # 提取IP地址部分
        
        if ip != "0.0.0.0" and not NetworkUtils.is_valid_ip(ip):
            QMessageBox.warning(self, "输入错误", "请输入有效的IP地址")
            return False
        
        # 验证端口
        try:
            srt_port = int(self.srt_port_input.text())
            ws_port = int(self.ws_port_input.text())
            
            if not (1 <= srt_port <= 65535):
                raise ValueError("SRT端口无效")
            if not (1 <= ws_port <= 65535):
                raise ValueError("WebSocket端口无效")
            
            if srt_port == ws_port:
                QMessageBox.warning(self, "输入错误", "SRT端口和WebSocket端口不能相同")
                return False
        
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的端口号(1-65535)")
            return False
        
        # 验证昵称
        nickname = self.nickname_input.text().strip()
        if not nickname:
            QMessageBox.warning(self, "输入错误", "请输入昵称")
            return False
        
        # 验证验证码
        code = self.code_input.text().strip()
        if not code or len(code) != 6 or not code.isdigit():
            QMessageBox.warning(self, "输入错误", "请输入6位数字验证码")
            return False
        
        return True
    
    def on_confirm_clicked(self):
        """确认按钮点击事件"""
        if not self.validate_input():
            return
        
        # 获取配置参数
        ip_text = self.ip_combo.currentText()
        ip = ip_text.split(' ')[0]  # 提取IP地址部分
        
        config_params = {
            "bind_ip": ip,
            "srt_port": int(self.srt_port_input.text()),
            "ws_port": int(self.ws_port_input.text()),
            "nickname": self.nickname_input.text().strip(),
            "verification_code": self.code_input.text().strip(),
            "enable_local_play": self.local_play_checkbox.isChecked()
        }
        
        logger.info(f"发送端配置: {config_params}")
        
        # 发送设置完成信号
        self.setup_completed.emit(config_params)
    
    def on_back_clicked(self):
        """返回按钮点击事件"""
        self.back_requested.emit()
    
    def center_on_screen(self):
        """将窗口居中显示"""
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen_rect.center())
        self.move(window_rect.topLeft())