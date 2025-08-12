# ui/chat_room.py - 聊天室界面
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QFrame, QDialog, QGridLayout, QScrollArea,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QIcon, QTextOption
from datetime import datetime
import config
from utils.logger import get_logger

logger = get_logger(__name__)

class EmojiDialog(QDialog):
    """Emoji选择对话框"""
    
    emoji_selected = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("选择表情")
        self.setModal(True)
        self.resize(450, 350)  # 增大对话框尺寸
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        scroll_layout.setSpacing(8)  # 增加间距
        
        # 添加emoji按钮
        emojis = config.EMOJI_LIST
        cols = 8  # 减少列数，让每个按钮更大
        
        for i, emoji in enumerate(emojis):
            row = i // cols
            col = i % cols
            
            button = QPushButton(emoji)
            button.setFixedSize(45, 45)  # 增大按钮尺寸
            button.setStyleSheet("""
                QPushButton {
                    font-size: 24px;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    background-color: #2d2d2d;
                    padding: 0px;
                    line-height: 45px;
                }
                QPushButton:hover {
                    background-color: #4a9eff;
                    border: 2px solid #5aa6ff;
                }
                QPushButton:pressed {
                    background-color: #3a8eef;
                }
            """)
            button.clicked.connect(lambda checked, e=emoji: self.on_emoji_clicked(e))
            
            scroll_layout.addWidget(button, row, col)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                width: 12px;
                background-color: #2d2d2d;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a9eff;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5aa6ff;
            }
        """)
        layout.addWidget(scroll_area)
    
    def on_emoji_clicked(self, emoji):
        """Emoji点击事件"""
        self.emoji_selected.emit(emoji)
        self.accept()


class ChatRoomWindow(QMainWindow):
    """聊天室窗口"""
    
    # 信号
    message_sent = Signal(str)      # 发送消息信号
    window_closing = Signal()       # 窗口关闭信号
    
    def __init__(self, role: str = "receiver", nickname: str = ""):
        """
        初始化聊天室窗口
        Args:
            role: 角色类型 ("sender" 或 "receiver")
            nickname: 用户昵称
        """
        super().__init__()
        self.role = role
        self.nickname = nickname
        self.members = []
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """初始化UI"""
        # 窗口设置
        title = f"{config.APP_NAME} - {'发送端' if self.role == 'sender' else '接收端'} - {self.nickname}"
        self.setWindowTitle(title)
        size = config.WINDOW_SIZES["chat_room"]
        self.resize(size["width"], size["height"])
        self.setMinimumSize(size["min_width"], size["min_height"])
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：成员列表
        member_widget = QWidget()
        member_layout = QVBoxLayout(member_widget)
        member_layout.setContentsMargins(0, 0, 0, 0)
        
        # 成员列表标题
        member_title = QLabel("在线成员")
        member_title.setAlignment(Qt.AlignCenter)
        member_title.setStyleSheet("""
            QLabel {
                font-weight: bold;
                padding: 10px;
                background-color: #2d2d2d;
                border-radius: 4px;
            }
        """)
        member_layout.addWidget(member_title)
        
        # 成员列表
        self.member_list = QListWidget()
        self.member_list.setMinimumWidth(150)
        self.member_list.setMaximumWidth(200)
        member_layout.addWidget(self.member_list)
        
        splitter.addWidget(member_widget)
        
        # 右侧：聊天区域
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # 聊天记录显示区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(300)
        
        # 设置文档格式，确保正确换行
        self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)
        self.chat_display.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        
        # 设置字体和tab停止距离
        chat_font = QFont(config.THEME["fonts"]["default"], config.THEME["fonts"]["size_normal"])
        self.chat_display.setFont(chat_font)
        self.chat_display.setTabStopDistance(40)  # 设置tab停止距离
        
        # 设置文档边距
        self.chat_display.document().setDocumentMargin(5)
        
        chat_layout.addWidget(self.chat_display)
        
        # 输入区域
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 5, 0, 0)
        
        # 消息输入框
        self.message_input = QLineEdit()
        self.message_input.setMinimumHeight(35)
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        # Emoji按钮
        self.emoji_button = QPushButton("😊")
        self.emoji_button.setFixedSize(40, 35)  # 宽度稍大以确保emoji完整显示
        self.emoji_button.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 2px solid #4a9eff;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.emoji_button.clicked.connect(self.show_emoji_dialog)
        input_layout.addWidget(self.emoji_button)
        
        # 发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.setMinimumHeight(35)
        self.send_button.setMinimumWidth(80)
        self.send_button.setObjectName("primary_button")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addWidget(input_widget)
        
        splitter.addWidget(chat_widget)
        
        # 设置分割器比例
        splitter.setSizes([200, 700])
        
        main_layout.addWidget(splitter)
        
        # 设置焦点
        self.message_input.setFocus()
    
    def apply_theme(self):
        """应用主题"""
        colors = config.THEME["colors"]
        fonts = config.THEME["fonts"]
        
        stylesheet = f"""
            QMainWindow {{
                background-color: {colors['background']};
            }}
            
            QTextEdit {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 10px;
                font-size: {fonts['size_normal']}px;
                font-family: {fonts['default']};
                line-height: 1.6;
                selection-background-color: {colors['primary']};
            }}
            
            QListWidget {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 5px;
                font-size: {fonts['size_normal']}px;
            }}
            
            QListWidget::item {{
                padding: 5px;
                border-radius: 3px;
                margin: 2px;
            }}
            
            QListWidget::item:hover {{
                background-color: {colors['border']};
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
                padding: 8px 15px;
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
                font-weight: bold;
            }}
            
            QPushButton#primary_button:hover {{
                background-color: #5aa6ff;
            }}
            
            QLabel {{
                color: {colors['text']};
            }}
            
            QSplitter::handle {{
                background-color: {colors['border']};
                width: 2px;
            }}
        """
        
        self.setStyleSheet(stylesheet)
    
    def clear_messages(self):
        """清空聊天记录"""
        self.chat_display.clear()
    
    def add_message(self, nickname: str, message: str, is_system: bool = False):
        """
        添加消息到聊天记录
        Args:
            nickname: 发送者昵称
            message: 消息内容
            is_system: 是否为系统消息
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 移动光标到末尾
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)
        
        # 如果不是第一条消息，添加换行分隔
        if not self.chat_display.document().isEmpty():
            cursor.insertText("\n")
        
        if is_system or nickname == "系统":
            # 系统消息 - 使用斜体和不同颜色
            formatted_text = f"[{timestamp}] {message}"
            
            # 创建格式
            format = QTextCharFormat()
            format.setForeground(QColor(config.THEME["colors"]["warning"]))
            format.setFontItalic(True)
            
            # 插入文本
            cursor.insertText(formatted_text, format)
        else:
            # 普通消息 - 分段插入不同格式的文本
            
            # 时间戳
            time_format = QTextCharFormat()
            time_format.setForeground(QColor(config.THEME["colors"]["text_secondary"]))
            cursor.insertText(f"[{timestamp}] ", time_format)
            
            # 昵称
            nickname_format = QTextCharFormat()
            nickname_color = config.THEME["colors"]["primary"] if nickname == self.nickname else config.THEME["colors"]["text"]
            nickname_format.setForeground(QColor(nickname_color))
            nickname_format.setFontWeight(700)  # 使用数值代替QFont.Bold
            cursor.insertText(f"{nickname}: ", nickname_format)
            
            # 消息内容
            message_format = QTextCharFormat()
            message_format.setForeground(QColor(config.THEME["colors"]["text"]))
            cursor.insertText(message, message_format)
        
        # 确保滚动到底部
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def update_member_list(self, members: list):
        """
        更新成员列表
        Args:
            members: 成员列表 [{"nickname": str, "role": str}, ...]
        """
        self.members = members
        self.member_list.clear()
        
        for member in members:
            nickname = member.get("nickname", "")
            role = member.get("role", "")
            
            # 创建列表项
            item = QListWidgetItem()
            
            # 设置显示文本
            if role == "sender":
                display_text = f"👑 {nickname}"
            else:
                display_text = f"👤 {nickname}"
            
            item.setText(display_text)
            
            # 高亮自己
            if nickname == self.nickname:
                item.setBackground(QColor(config.THEME["colors"]["primary"]).darker(180))
            
            self.member_list.addItem(item)
    
    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if not message:
            return
        
        # 清空输入框
        self.message_input.clear()
        
        # 发送消息信号
        self.message_sent.emit(message)
        
        # 如果是发送端，消息会通过回调显示，避免重复
        # 如果是接收端，消息会通过服务器广播回来显示
    
    def show_emoji_dialog(self):
        """显示emoji选择对话框"""
        dialog = EmojiDialog(self)
        dialog.emoji_selected.connect(self.insert_emoji)
        
        # 设置对话框位置
        button_pos = self.emoji_button.mapToGlobal(self.emoji_button.rect().topLeft())
        dialog.move(button_pos.x(), button_pos.y() - dialog.height())
        
        dialog.exec()
    
    def insert_emoji(self, emoji):
        """插入emoji到输入框"""
        current_text = self.message_input.text()
        cursor_pos = self.message_input.cursorPosition()
        
        new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
        self.message_input.setText(new_text)
        self.message_input.setCursorPosition(cursor_pos + len(emoji))
        self.message_input.setFocus()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出放映室吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.window_closing.emit()
            event.accept()
        else:
            event.ignore()
    
    def center_on_screen(self):
        """将窗口居中显示"""
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen_rect.center())
        self.move(window_rect.topLeft())