#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析 - 自定义窗口组件
包含自定义消息框、通知窗口、Markdown渲染器等
"""

import re
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QWidget, QFrame, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QBrush, QIcon

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logging.warning("Markdown模块未安装，将使用纯文本显示")


class CustomMessageBox(QDialog):
    """自定义消息框"""
    
    def __init__(self, parent=None, title="", message="", icon_type="info", buttons=None):
        super().__init__(parent)
        self.result = None
        self.init_ui(title, message, icon_type, buttons or ["确定"])
        
    def init_ui(self, title, message, icon_type, buttons):
        """初始化界面"""
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        # 设置窗口图标
        try:
            from icon_data import get_icon_data
            icon_data = get_icon_data()
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except ImportError:
            # 如果icon_data模块不存在，回退到文件方式
            import os
            if os.path.exists('favicon.ico'):
                self.setWindowIcon(QIcon('favicon.ico'))
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fffe;
                border: 2px solid #a8d8a8;
                border-radius: 8px;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
            }
            QPushButton {
                background-color: #a8d8a8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #90c890;
            }
            QPushButton:pressed {
                background-color: #78b878;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 图标和消息区域
        content_layout = QHBoxLayout()
        
        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 根据类型设置图标颜色
        icon_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "question": "#9b59b6",
            "success": "#27ae60"
        }
        
        icon_color = icon_colors.get(icon_type, "#3498db")
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {icon_color};
                border-radius: 24px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }}
        """)
        
        # 设置图标文字
        icon_texts = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✕",
            "question": "?",
            "success": "✓"
        }
        icon_label.setText(icon_texts.get(icon_type, "ℹ"))
        
        content_layout.addWidget(icon_label)
        
        # 消息文本
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(message_label, 1)
        
        layout.addLayout(content_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        for button_text in buttons:
            button = QPushButton(button_text)
            button.clicked.connect(lambda checked, text=button_text: self.button_clicked(text))
            button_layout.addWidget(button)
        
        layout.addLayout(button_layout)
        
        # 居中显示
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
    
    def button_clicked(self, button_text):
        """按钮点击处理"""
        self.result = button_text
        self.accept()
    
    @staticmethod
    def information(parent, title, message):
        """信息对话框"""
        dialog = CustomMessageBox(parent, title, message, "info")
        dialog.exec()
        return dialog.result
    
    @staticmethod
    def warning(parent, title, message):
        """警告对话框"""
        dialog = CustomMessageBox(parent, title, message, "warning")
        dialog.exec()
        return dialog.result
    
    @staticmethod
    def critical(parent, title, message):
        """错误对话框"""
        dialog = CustomMessageBox(parent, title, message, "error")
        dialog.exec()
        return dialog.result
    
    @staticmethod
    def question(parent, title, message):
        """询问对话框"""
        dialog = CustomMessageBox(parent, title, message, "question", ["是", "否"])
        dialog.exec()
        return dialog.result == "是"


class MarkdownViewer(QTextEdit):
    """Markdown渲染器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setup_style()
        
        # 性能优化：批量更新
        self._pending_content = None
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._do_update)
        self._update_timer.setInterval(50)  # 50ms延迟批量更新
    
    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Segoe UI Emoji', 'Microsoft YaHei', 'Noto Color Emoji', 'Apple Color Emoji', Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
    
    def set_markdown(self, markdown_text: str):
        """设置Markdown内容（支持批量更新优化）"""
        self._pending_content = markdown_text
        self._update_timer.start()  # 重启定时器
    
    def _do_update(self):
        """执行实际的内容更新"""
        if self._pending_content is None:
            return
            
        markdown_text = self._pending_content
        self._pending_content = None
        
        if MARKDOWN_AVAILABLE:
            try:
                # 配置markdown扩展
                html = markdown.markdown(
                    markdown_text,
                    extensions=['codehilite', 'fenced_code', 'tables', 'toc'],
                    extension_configs={
                        'codehilite': {
                            'css_class': 'highlight',
                            'use_pygments': False
                        }
                    }
                )
                
                # 添加CSS样式
                styled_html = f"""
                <style>
                    body {{
                        font-family: 'Microsoft YaHei', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{ font-size: 1.8em; border-bottom: 2px solid #a8d8a8; padding-bottom: 0.3em; }}
                    h2 {{ font-size: 1.5em; border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3em; }}
                    h3 {{ font-size: 1.3em; }}
                    p {{ margin: 0.8em 0; }}
                    code {{
                        background-color: #f8f8f8;
                        border: 1px solid #e0e0e0;
                        border-radius: 3px;
                        padding: 2px 4px;
                        font-family: 'Consolas', 'Monaco', monospace;
                        font-size: 0.9em;
                    }}
                    pre {{
                        background-color: #f8f8f8;
                        border: 1px solid #e0e0e0;
                        border-radius: 4px;
                        padding: 10px;
                        overflow-x: auto;
                        margin: 1em 0;
                    }}
                    pre code {{
                        background: none;
                        border: none;
                        padding: 0;
                    }}
                    blockquote {{
                        border-left: 4px solid #a8d8a8;
                        margin: 1em 0;
                        padding-left: 1em;
                        color: #666;
                        font-style: italic;
                    }}
                    ul, ol {{ margin: 0.8em 0; padding-left: 2em; }}
                    li {{ margin: 0.3em 0; }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    th, td {{
                        border: 1px solid #e0e0e0;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f8f8f8;
                        font-weight: bold;
                    }}
                    a {{
                        color: #a8d8a8;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
                {html}
                """
                
                self.setHtml(styled_html)
            except Exception as e:
                logging.error(f"Markdown渲染失败: {e}")
                self.setPlainText(markdown_text)
        else:
            self.setPlainText(markdown_text)
        
        # 滚动到底部
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def append_text(self, text: str):
        """追加文本（流式显示）"""
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.setTextCursor(cursor)
        
        # 滚动到底部
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class SmallNotificationWindow(QWidget):
    """小通知窗口"""
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
        self.init_ui()
        self.setup_animation()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 设置可变大小，支持滚动
        self.setMinimumSize(300, 80)
        self.setMaximumSize(400, 300)
        
        # 处理连续换行
        processed_message = self._process_text(self.message)
        
        # 设置样式 - 纯白背景，黑色文字，小字体
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #cccccc;
            }
            QScrollArea {
                background-color: white;
                border: none;
            }
            QLabel {
                color: black;
                font-size: 12px;
                padding: 8px;
                background-color: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 消息标签
        message_label = QLabel(processed_message)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(message_label)
        layout.addWidget(scroll_area)
        
        # 根据内容调整窗口大小
        self._adjust_size(message_label)
        
        # 定位到屏幕右下角
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 60
        self.move(x, y)
    
    def _process_text(self, text):
        """处理文本，将连续换行合并为一个"""
        import re
        # 将连续的换行符替换为单个换行符
        processed = re.sub(r'\n+', '\n', text.strip())
        return processed
    
    def _adjust_size(self, label):
        """固定窗口大小"""
        # 固定小窗大小为350x200
        self.setFixedSize(350, 200)
    
    def append_content(self, content):
        """追加内容到小窗"""
        # 获取当前的消息标签
        scroll_area = self.layout().itemAt(0).widget()
        message_label = scroll_area.widget()
        
        # 追加新内容
        current_text = message_label.text()
        new_text = current_text + content
        processed_text = self._process_text(new_text)
        message_label.setText(processed_text)
        
        # 重新调整大小
        self._adjust_size(message_label)
        
        # 滚动到底部
        scrollbar = scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # 重新定位到屏幕右下角
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 60
        self.move(x, y)
    
    def setup_animation(self):
        """设置动画"""
        # 淡入动画
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 淡出动画
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1)
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_animation.finished.connect(self.close)
        
        # 自动关闭定时器
        self.close_timer = QTimer()
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.start_fade_out)
        
    def show_notification(self):
        """显示通知"""
        self.show()
        self.fade_in_animation.start()
        self.close_timer.start(10000)  # 10秒后自动关闭
    
    def start_fade_out(self):
        """开始淡出"""
        self.fade_out_animation.start()
    
    def mousePressEvent(self, event):
        """鼠标点击关闭"""
        self.start_fade_out()


class LargeNotificationWindow(QDialog):
    """大通知窗口"""
    
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.message = message
        self.current_text = ""
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI分析结果")
        self.setModal(False)  # 设置为非模态窗口，允许主窗口操作
        # 设置为完全独立的窗口，不与任何父窗口关联
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self.resize(800, 600)
        
        # 设置窗口图标
        try:
            from icon_data import get_icon_data
            icon_data = get_icon_data()
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except ImportError:
            # 如果icon_data模块不存在，回退到文件方式
            import os
            if os.path.exists('favicon.ico'):
                self.setWindowIcon(QIcon('favicon.ico'))
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fffe;
            }
            QPushButton {
                background-color: #a8d8a8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #90c890;
            }
            QPushButton:pressed {
                background-color: #78b878;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("AI分析结果")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # 内容区域
        self.content_viewer = MarkdownViewer()
        layout.addWidget(self.content_viewer)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.copy_btn = QPushButton("复制内容")
        self.copy_btn.clicked.connect(self.copy_content)
        button_layout.addWidget(self.copy_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # 居中显示
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        
        # 设置初始内容
        self.set_content(self.message)
    
    def set_content(self, content: str):
        """设置内容"""
        self.current_text = content
        self.content_viewer.set_markdown(content)
    
    def append_content(self, content: str):
        """追加内容（流式显示）"""
        if not hasattr(self, 'current_response_content'):
            self.current_response_content = ""
        if not hasattr(self, 'current_reasoning_content'):
            self.current_reasoning_content = ""
        
        self.current_response_content += content
        self._update_display_content()
    
    def append_reasoning_content(self, reasoning: str):
        """追加推理内容"""
        if not hasattr(self, 'current_reasoning_content'):
            self.current_reasoning_content = ""
        if not hasattr(self, 'current_response_content'):
            self.current_response_content = ""
        
        self.current_reasoning_content += reasoning
        self._update_display_content()
    
    def _update_display_content(self, force_render=False):
        """更新显示内容（使用批量更新优化）"""
        if not hasattr(self, '_update_pending'):
            self._update_pending = False
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._batch_update_display)
            self._update_timer.setInterval(100)  # 100ms批量更新
        
        if force_render:
            # 强制立即渲染
            self._batch_update_display()
        elif not self._update_pending:
            self._update_pending = True
            self._update_timer.start()
    
    def _batch_update_display(self, force_markdown=False):
        """批量更新显示内容"""
        if hasattr(self, '_update_pending'):
            self._update_pending = False
        
        display_content = ""
        
        if hasattr(self, 'current_reasoning_content') and self.current_reasoning_content:
            display_content += f"<div style='background-color: #f0f8ff; padding: 15px; border-left: 4px solid #4a90e2; margin-bottom: 20px; border-radius: 6px;'>\n"
            display_content += f"<h3 style='color: #4a90e2; margin: 0 0 10px 0; font-family: \"Microsoft YaHei\", sans-serif;'>🤔 思考内容</h3>\n"
            display_content += f"<div style='font-family: \"Consolas\", \"Monaco\", monospace; font-size: 14px; color: #666; line-height: 1.6; white-space: pre-wrap;'>{self.current_reasoning_content}</div>\n"
            display_content += f"</div>\n\n"
        
        if hasattr(self, 'current_response_content') and self.current_response_content:
            if force_markdown:
                # 流式完成后，进行完整的markdown渲染
                display_content += f"<div style='background-color: #f8fff8; padding: 15px; border-left: 4px solid #28a745; border-radius: 6px;'>\n"
                display_content += f"<h3 style='color: #28a745; margin: 0 0 10px 0; font-family: \"Microsoft YaHei\", sans-serif;'>💬 回复内容</h3>\n"
                display_content += f"<div style='font-family: \"Microsoft YaHei\", sans-serif; line-height: 1.6; white-space: pre-wrap;'>{self.current_response_content}</div>\n"
                display_content += f"</div>"
            else:
                # 流式过程中，显示纯文本避免频繁渲染
                display_content += f"<div style='background-color: #f8fff8; padding: 15px; border-left: 4px solid #28a745; border-radius: 6px;'>\n"
                display_content += f"<h3 style='color: #28a745; margin: 0 0 10px 0; font-family: \"Microsoft YaHei\", sans-serif;'>💬 回复内容</h3>\n"
                display_content += f"<div style='font-family: \"Microsoft YaHei\", sans-serif; line-height: 1.6; white-space: pre-wrap;'>{self.current_response_content}</div>\n"
                display_content += f"</div>"
        
        self.current_text = display_content
        if force_markdown:
            # 强制进行markdown渲染
            self.content_viewer.set_markdown(display_content)
        else:
            # 流式过程中使用简单的HTML显示
            self.content_viewer.setHtml(display_content)
        
        # 确保滚动条始终在底部
        scrollbar = self.content_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def append_response_content(self, content):
        """追加回复内容（用于流式响应）"""
        if not hasattr(self, 'current_response_content'):
            self.current_response_content = ""
        
        self.current_response_content += content
        # 流式过程中不进行markdown渲染，只更新文本
        self._update_display_content(force_render=False)
    
    def append_reasoning_content(self, content):
        """追加推理内容"""
        if not hasattr(self, 'current_reasoning_content'):
            self.current_reasoning_content = ""
        
        self.current_reasoning_content += content
        # 推理内容立即显示
        self._update_display_content(force_render=False)
    
    def copy_content(self):
        """复制内容到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.current_text)
        
        # 临时改变按钮文字
        original_text = self.copy_btn.text()
        self.copy_btn.setText("已复制")
        QTimer.singleShot(1000, lambda: self.copy_btn.setText(original_text))


class NotificationWindow:
    """通知窗口管理器"""
    
    _small_notifications = []
    _large_notification = None
    
    @classmethod
    def show_small_notification(cls, message: str):
        """显示小通知"""
        try:
            # 清理已关闭的通知
            cls._small_notifications = [n for n in cls._small_notifications if n.isVisible()]
            
            # 限制同时显示的通知数量
            if len(cls._small_notifications) >= 3:
                oldest = cls._small_notifications.pop(0)
                oldest.start_fade_out()
            
            # 创建新通知
            notification = SmallNotificationWindow(message)
            cls._small_notifications.append(notification)
            
            # 调整位置（避免重叠）
            screen = QApplication.primaryScreen().geometry()
            x = screen.width() - notification.width() - 20
            y = screen.height() - notification.height() - 60 - (len(cls._small_notifications) - 1) * 110
            notification.move(x, y)
            
            notification.show_notification()
            
        except Exception as e:
            logging.error(f"显示小通知失败: {e}")
    
    @classmethod
    def show_large_notification(cls, message: str, parent=None):
        """显示大通知"""
        try:
            # 关闭之前的大通知
            if cls._large_notification and cls._large_notification.isVisible():
                cls._large_notification.close()
            
            # 创建新的大通知，不设置父窗口以确保完全独立
            cls._large_notification = LargeNotificationWindow(message, None)
            cls._large_notification.show()
            
        except Exception as e:
            logging.error(f"显示大通知失败: {e}")
    
    @classmethod
    def show_large_notification_streaming(cls, initial_message: str, parent=None):
        """显示流式大通知"""
        try:
            # 关闭之前的大通知
            if cls._large_notification and cls._large_notification.isVisible():
                cls._large_notification.close()
            
            # 创建新的大通知（用于流式显示），不设置父窗口以确保完全独立
            cls._large_notification = LargeNotificationWindow(initial_message, None)
            cls._large_notification.setWindowTitle("AI流式响应")
            cls._large_notification.current_reasoning_content = ""
            cls._large_notification.current_response_content = ""
            cls._large_notification.show()
            
            return cls._large_notification
            
        except Exception as e:
            logging.error(f"显示流式大通知失败: {e}")
            return None
    
    @classmethod
    def show_large_notification_reasoning(cls, reasoning_content: str, parent=None):
        """显示推理内容大通知"""
        try:
            # 创建新的推理内容窗口，不关闭现有窗口以支持同时显示
            reasoning_window = LargeNotificationWindow("", None)
            reasoning_window.setWindowTitle("AI推理过程")
            reasoning_window.current_reasoning_content = reasoning_content
            reasoning_window.current_response_content = ""
            reasoning_window._batch_update_display()
            reasoning_window.show()
            
            return reasoning_window
            
        except Exception as e:
            logging.error(f"显示推理内容大通知失败: {e}")
            return None
    

    
    @classmethod
    def close_all_notifications(cls):
        """关闭所有通知"""
        try:
            # 关闭小通知
            for notification in cls._small_notifications:
                if notification.isVisible():
                    notification.start_fade_out()
            cls._small_notifications.clear()
            
            # 关闭大通知
            if cls._large_notification and cls._large_notification.isVisible():
                cls._large_notification.close()
                cls._large_notification = None
                
        except Exception as e:
            logging.error(f"关闭通知失败: {e}")


class ThinkingIndicator(QWidget):
    """思考指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_animation()
        
    def init_ui(self):
        """初始化界面"""
        self.setFixedSize(200, 50)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.label = QLabel("正在深入思考")
        self.label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                font-style: italic;
            }
        """)
        
        layout.addWidget(self.label)
        
        # 动画点
        self.dots = []
        for i in range(3):
            dot = QLabel("●")
            dot.setStyleSheet("""
                QLabel {
                    color: #a8d8a8;
                    font-size: 16px;
                }
            """)
            self.dots.append(dot)
            layout.addWidget(dot)
        
        layout.addStretch()
    
    def setup_animation(self):
        """设置动画"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_dots)
        self.animation_step = 0
    
    def start_thinking(self):
        """开始思考动画"""
        self.show()
        self.animation_timer.start(500)  # 每500ms更新一次
    
    def stop_thinking(self):
        """停止思考动画"""
        self.animation_timer.stop()
        self.hide()
    
    def animate_dots(self):
        """动画点"""
        for i, dot in enumerate(self.dots):
            if i == self.animation_step % 3:
                dot.setStyleSheet("""
                    QLabel {
                        color: #a8d8a8;
                        font-size: 16px;
                    }
                """)
            else:
                dot.setStyleSheet("""
                    QLabel {
                        color: #e0e0e0;
                        font-size: 16px;
                    }
                """)
        
        self.animation_step += 1