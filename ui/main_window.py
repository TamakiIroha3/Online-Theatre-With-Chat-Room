# ui/main_window.py - 主窗口
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
import config
from utils.logger import get_logger

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    """主窗口 - 选择发送端或接收端"""
    
    # 信号
    sender_selected = Signal()
    receiver_selected = Signal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
        self.setup_animations()
    
    def init_ui(self):
        """初始化UI"""
        # 窗口设置
        self.setWindowTitle(config.APP_NAME)
        size = config.WINDOW_SIZES["main"]
        self.resize(size["width"], size["height"])
        self.setMinimumSize(size["min_width"], size["min_height"])
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # 标题
        title_label = QLabel(config.APP_NAME)
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_title"])
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("请选择您的角色")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_normal"])
        subtitle_label.setFont(subtitle_font)
        main_layout.addWidget(subtitle_label)
        
        # 添加弹性空间
        main_layout.addStretch(1)
        
        # 按钮容器
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setSpacing(15)
        
        # 发送端按钮
        self.sender_button = self.create_role_button(
            "发送端",
            "创建放映室，分享视频流",
            "primary"
        )
        self.sender_button.clicked.connect(self.on_sender_clicked)
        button_layout.addWidget(self.sender_button)
        
        # 接收端按钮
        self.receiver_button = self.create_role_button(
            "接收端",
            "加入放映室，观看视频流",
            "secondary"
        )
        self.receiver_button.clicked.connect(self.on_receiver_clicked)
        button_layout.addWidget(self.receiver_button)
        
        main_layout.addWidget(button_container)
        
        # 添加弹性空间
        main_layout.addStretch(2)
        
        # 版本信息
        version_label = QLabel(f"版本 {config.VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_small"])
        version_label.setFont(version_font)
        version_label.setStyleSheet(f"color: {config.THEME['colors']['text_secondary']};")
        main_layout.addWidget(version_label)
    
    def create_role_button(self, title: str, description: str, style: str) -> QPushButton:
        """
        创建角色选择按钮
        Args:
            title: 按钮标题
            description: 按钮描述
            style: 按钮样式 ("primary" 或 "secondary")
        """
        button = QPushButton()
        button.setObjectName(f"{style}_button")
        
        # 创建按钮内容
        button_text = f"{title}\n{description}"
        button.setText(button_text)
        
        # 设置按钮属性
        button.setMinimumHeight(80)
        button.setCursor(Qt.PointingHandCursor)
        
        # 设置字体
        button_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_normal"])
        button.setFont(button_font)
        
        return button
    
    def apply_theme(self):
        """应用主题"""
        # 设置应用样式
        app = QApplication.instance()
        app.setStyle(config.THEME["style"])
        
        # 创建样式表
        colors = config.THEME["colors"]
        fonts = config.THEME["fonts"]
        
        stylesheet = f"""
            QMainWindow {{
                background-color: {colors['background']};
            }}
            
            QLabel {{
                color: {colors['text']};
            }}
            
            QPushButton {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 15px;
                text-align: left;
            }}
            
            QPushButton:hover {{
                background-color: {colors['border']};
                border: 1px solid {colors['primary']};
            }}
            
            QPushButton:pressed {{
                background-color: {colors['background']};
            }}
            
            QPushButton#primary_button {{
                border: 2px solid {colors['primary']};
            }}
            
            QPushButton#primary_button:hover {{
                background-color: {colors['primary']};
                color: {colors['background']};
            }}
            
            QPushButton#secondary_button {{
                border: 1px solid {colors['border']};
            }}
            
            QPushButton#secondary_button:hover {{
                border: 2px solid {colors['text_secondary']};
            }}
        """
        
        self.setStyleSheet(stylesheet)
    
    def setup_animations(self):
        """设置动画效果"""
        # 为按钮添加悬停动画
        for button in [self.sender_button, self.receiver_button]:
            button.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 用于按钮动画"""
        if obj in [self.sender_button, self.receiver_button]:
            if event.type() == event.Type.Enter:
                self.animate_button(obj, True)
            elif event.type() == event.Type.Leave:
                self.animate_button(obj, False)
        
        return super().eventFilter(obj, event)
    
    def animate_button(self, button: QPushButton, hover: bool):
        """
        按钮动画
        Args:
            button: 按钮对象
            hover: 是否悬停
        """
        # 这里可以添加动画效果
        pass
    
    def on_sender_clicked(self):
        """发送端按钮点击事件"""
        logger.info("用户选择了发送端")
        self.sender_selected.emit()
    
    def on_receiver_clicked(self):
        """接收端按钮点击事件"""
        logger.info("用户选择了接收端")
        self.receiver_selected.emit()
    
    def center_on_screen(self):
        """将窗口居中显示"""
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen_rect.center())
        self.move(window_rect.topLeft())