# ui/receiver_setup.py - 接收端设置界面
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIntValidator
import random
import config
from utils.logger import get_logger
from utils.network_utils import NetworkUtils

logger = get_logger(__name__)

class ReceiverSetupWindow(QMainWindow):
    """接收端设置界面"""
    
    # 信号
    setup_completed = Signal(dict)  # 设置完成信号，传递配置参数
    back_requested = Signal()       # 返回主界面信号
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        # 窗口设置
        self.setWindowTitle(f"{config.APP_NAME} - 接收端设置")
        size = config.WINDOW_SIZES["receiver_setup"]
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
        title_label = QLabel("接收端设置")
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
        
        # 服务器IP地址
        server_ip_label = QLabel("服务器IP地址:")
        form_layout.addWidget(server_ip_label, row, 0, Qt.AlignRight)
        
        self.server_ip_input = QLineEdit()
        self.server_ip_input.setMinimumHeight(30)
        self.server_ip_input.setPlaceholderText("输入服务器IP地址 (支持IPv4/IPv6)")
        form_layout.addWidget(self.server_ip_input, row, 1)
        
        row += 1
        
        # 服务器端口
        server_port_label = QLabel("服务器端口:")
        form_layout.addWidget(server_port_label, row, 0, Qt.AlignRight)
        
        self.server_port_input = QLineEdit()
        self.server_port_input.setText(str(config.NETWORK_DEFAULTS["websocket_port"]))
        self.server_port_input.setValidator(QIntValidator(1, 65535))
        self.server_port_input.setMinimumHeight(30)
        self.server_port_input.setPlaceholderText("1-65535")
        form_layout.addWidget(self.server_port_input, row, 1)
        
        row += 1
        
        # 昵称
        nickname_label = QLabel("昵称:")
        form_layout.addWidget(nickname_label, row, 0, Qt.AlignRight)
        
        self.nickname_input = QLineEdit()
        self.nickname_input.setText(self.get_random_receiver_nickname())
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
        
        main_layout.addWidget(form_widget)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 提示信息
        info_label = QLabel("提示：请向发送端获取服务器地址和验证码")
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
        
        # 连接按钮
        self.connect_button = QPushButton("连接")
        self.connect_button.setMinimumHeight(35)
        self.connect_button.setObjectName("primary_button")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        button_layout.addWidget(self.connect_button)
        
        main_layout.addLayout(button_layout)
    
    def get_random_receiver_nickname(self) -> str:
        """获取随机接收端昵称（包含稀有角色）"""
        # 极小概率出现稀有角色
        if random.random() < config.RARE_ROLE_PROBABILITY:
            return random.choice(config.RARE_ROLE_NAMES)
        return random.choice(config.ROLE_NAMES)
    
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
            
            QLineEdit {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 5px 10px;
                font-size: {fonts['size_normal']}px;
            }}
            
            QLineEdit:focus {{
                border: 2px solid {colors['primary']};
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
    
    def validate_input(self) -> bool:
        """验证输入"""
        # 验证服务器IP地址
        server_ip = self.server_ip_input.text().strip()
        if not server_ip:
            QMessageBox.warning(self, "输入错误", "请输入服务器IP地址")
            return False
        
        # 尝试解析主机名或IP地址
        if not NetworkUtils.is_valid_ip(server_ip):
            # 可能是域名，尝试解析
            resolved_ip = NetworkUtils.resolve_hostname(server_ip)
            if not resolved_ip:
                QMessageBox.warning(self, "输入错误", "无效的服务器地址")
                return False
        
        # 验证端口
        try:
            port = int(self.server_port_input.text())
            if not (1 <= port <= 65535):
                raise ValueError("端口无效")
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
    
    def on_connect_clicked(self):
        """连接按钮点击事件"""
        if not self.validate_input():
            return
        
        # 获取配置参数
        config_params = {
            "server_ip": self.server_ip_input.text().strip(),
            "server_port": int(self.server_port_input.text()),
            "nickname": self.nickname_input.text().strip(),
            "verification_code": self.code_input.text().strip()
        }
        
        logger.info(f"接收端配置: {config_params}")
        
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