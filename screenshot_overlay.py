#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析 - 高级截图覆盖层
提供流畅的截图体验，包括区域选择、确认/取消等功能
"""

import logging
from PIL import ImageGrab
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, 
    QFontMetrics, QKeySequence, QShortcut
)
from PyQt6.QtWidgets import (
    QWidget, QApplication, QHBoxLayout, 
    QPushButton, QFrame
)


class ScreenshotOverlay(QWidget):
    """截图覆盖层窗口"""
    
    # 信号定义
    screenshot_confirmed = pyqtSignal(object)  # 确认截图信号
    screenshot_cancelled = pyqtSignal()  # 取消截图信号
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_variables()
        self.setup_shortcuts()
        
    def setup_ui(self):
        """设置UI"""
        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        # 设置鼠标追踪
        self.setMouseTracking(True)
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        self.screen_geometry = screen.geometry()
        self.setGeometry(self.screen_geometry)
        
        # 截取屏幕背景
        self.background_pixmap = screen.grabWindow(0)
        
    def setup_variables(self):
        """设置变量"""
        self.is_selecting = False
        self.selection_start = QPoint()
        self.selection_end = QPoint()
        self.current_rect = QRect()
        self.is_dragging = False
        
        # 控制面板相关
        self.control_panel = None
        self.show_control_panel = False
        
    def setup_shortcuts(self):
        """设置快捷键"""
        # ESC键取消
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.escape_shortcut.activated.connect(self.cancel_screenshot)
        
        # Enter键确认
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.enter_shortcut.activated.connect(self.confirm_screenshot)
        
        # Space键确认
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.space_shortcut.activated.connect(self.confirm_screenshot)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = True
            self.selection_start = event.pos()
            self.selection_end = event.pos()
            self.current_rect = QRect()
            self.hide_control_panel()
            self.update()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_selecting:
            self.selection_end = event.pos()
            self.current_rect = QRect(self.selection_start, self.selection_end).normalized()
            self.update()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.selection_end = event.pos()
            self.current_rect = QRect(self.selection_start, self.selection_end).normalized()
            
            # 如果选择区域太小，则取消选择
            if self.current_rect.width() < 10 or self.current_rect.height() < 10:
                self.current_rect = QRect()
                self.update()
                return
                
            # 显示控制面板
            self.show_control_panel_at_selection()
            self.update()
            
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件 - 快速确认"""
        if not self.current_rect.isEmpty():
            self.confirm_screenshot()
            
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_screenshot()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if not self.current_rect.isEmpty():
                self.confirm_screenshot()
        super().keyPressEvent(event)
        
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景（半透明遮罩）
        painter.drawPixmap(0, 0, self.background_pixmap)
        
        # 绘制遮罩层
        overlay_color = QColor(0, 0, 0, 120)  # 半透明黑色
        painter.fillRect(self.rect(), overlay_color)
        
        # 如果有选择区域，绘制选择框
        if not self.current_rect.isEmpty():
            self.draw_selection_area(painter)
            self.draw_selection_instructions(painter)
        else:
            # 绘制初始提示信息
            self.draw_instructions(painter)
        
    def draw_selection_area(self, painter):
        """绘制选择区域"""
        # 清除选择区域的遮罩，显示原始截图
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.current_rect, QColor(0, 0, 0, 0))
        
        # 恢复正常绘制模式
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # 绘制选择框边框
        pen = QPen(QColor(0, 120, 215), 2)  # Windows蓝色
        painter.setPen(pen)
        painter.drawRect(self.current_rect)
        
        # 绘制选择框信息
        self.draw_selection_info(painter)
        
    def draw_selection_info(self, painter):
        """绘制选择框信息"""
        if self.current_rect.isEmpty():
            return
            
        # 设置字体（缩小字体）
        font = QFont("Microsoft YaHei", 10, QFont.Weight.Medium)
        painter.setFont(font)
        
        # 准备信息文本
        width = self.current_rect.width()
        height = self.current_rect.height()
        info_text = f"{width} × {height}"
        
        # 计算文本位置
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(info_text)
        
        # 放置在选择框外的右下角，距离选择框15像素
        info_x = self.current_rect.right() + 15
        info_y = self.current_rect.bottom() + 15
        
        # 确保信息框在屏幕范围内
        if info_x + text_rect.width() + 16 > self.width():
            # 如果右侧空间不够，放在左侧
            info_x = self.current_rect.left() - text_rect.width() - 31
            
        if info_y + text_rect.height() + 12 > self.height():
            # 如果下方空间不够，放在上方
            info_y = self.current_rect.top() - text_rect.height() - 27
            
        # 如果左侧也不够，强制放在屏幕内
        if info_x < 10:
            info_x = 10
        if info_y < 10:
            info_y = 10
            
        # 绘制信息背景（缩小的圆角矩形）
        info_bg_rect = QRect(
            info_x - 8, info_y - 6,
            text_rect.width() + 16, text_rect.height() + 12
        )
        
        # 绘制背景阴影
        shadow_rect = QRect(info_bg_rect.x() + 1, info_bg_rect.y() + 1, 
                           info_bg_rect.width(), info_bg_rect.height())
        painter.fillRect(shadow_rect, QColor(0, 0, 0, 100))
        
        # 绘制背景
        painter.fillRect(info_bg_rect, QColor(0, 120, 215, 200))  # Windows蓝色背景
        
        # 绘制背景边框
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.drawRoundedRect(info_bg_rect, 4, 4)
        
        # 绘制文本阴影
        painter.setPen(QPen(QColor(0, 0, 0, 120)))
        painter.drawText(info_x + 1, info_y + text_rect.height() + 1, info_text)
        
        # 绘制信息文本
        painter.setPen(QPen(QColor(255, 255, 255, 255)))
        painter.drawText(info_x, info_y + text_rect.height(), info_text)
        
    def draw_instructions(self, painter):
        """绘制操作提示"""
        # 只在没有选择区域时显示操作提示
        if not self.current_rect.isEmpty():
            return
            
        # 设置字体
        font = QFont("Microsoft YaHei", 14, QFont.Weight.Medium)
        painter.setFont(font)
        
        # 准备提示文本（只在未选择时显示）
        instructions = [
            "拖拽鼠标选择截图区域",
            "按 ESC 键取消"
        ]
            
        # 计算所有文本的总高度，用于垂直居中
        fm = QFontMetrics(font)
        total_height = 0
        text_rects = []
        
        for instruction in instructions:
            text_rect = fm.boundingRect(instruction)
            text_rects.append(text_rect)
            total_height += text_rect.height() + 20  # 20是行间距
        
        total_height -= 20  # 减去最后一行的行间距
        
        # 计算起始Y位置（垂直居中）
        start_y = (self.height() - total_height) // 2
        
        # 绘制每行文本
        y_offset = start_y
        for i, instruction in enumerate(instructions):
            text_rect = text_rects[i]
            
            # 计算水平居中位置
            x = (self.width() - text_rect.width()) // 2
            
            # 绘制文本阴影（多层阴影效果）
            shadow_offsets = [(2, 2), (1, 1), (3, 3)]
            shadow_colors = [QColor(0, 0, 0, 180), QColor(0, 0, 0, 120), QColor(0, 0, 0, 60)]
            
            for offset, shadow_color in zip(shadow_offsets, shadow_colors):
                painter.setPen(QPen(shadow_color))
                painter.drawText(x + offset[0], y_offset + text_rect.height() + offset[1], instruction)
            
            # 绘制文本背景（圆角矩形，更好的视觉效果）
            bg_rect = QRect(
                x - 15, y_offset - 5,
                text_rect.width() + 30, text_rect.height() + 15
            )
            
            # 绘制背景阴影
            shadow_rect = QRect(bg_rect.x() + 3, bg_rect.y() + 3, bg_rect.width(), bg_rect.height())
            painter.fillRect(shadow_rect, QColor(0, 0, 0, 100))
            
            # 绘制背景（渐变效果）
            painter.fillRect(bg_rect, QColor(0, 0, 0, 200))
            
            # 绘制背景边框
            painter.setPen(QPen(QColor(255, 255, 255, 80), 1))
            painter.drawRoundedRect(bg_rect, 8, 8)
            
            # 绘制主文本（白色）
            painter.setPen(QPen(QColor(255, 255, 255, 255)))
            painter.drawText(x, y_offset + text_rect.height(), instruction)
            
            y_offset += text_rect.height() + 20
             
    def draw_selection_instructions(self, painter):
        """绘制选择区域时的操作提示"""
        # 设置字体
        font = QFont("Microsoft YaHei", 13, QFont.Weight.Medium)
        painter.setFont(font)
        
        # 准备提示文本
        instructions = [
            "双击或按 Enter/Space 确认截图",
            "按 ESC 键取消"
        ]
        
        # 计算文本位置（屏幕顶部居中）
        fm = QFontMetrics(font)
        y_offset = 25
        
        for instruction in instructions:
            text_rect = fm.boundingRect(instruction)
            x = (self.width() - text_rect.width()) // 2
            
            # 绘制文本背景（简化版，不遮挡选择区域）
            bg_rect = QRect(
                x - 12, y_offset - 6,
                text_rect.width() + 24, text_rect.height() + 12
            )
            
            # 绘制背景阴影
            shadow_rect = QRect(bg_rect.x() + 2, bg_rect.y() + 2, bg_rect.width(), bg_rect.height())
            painter.fillRect(shadow_rect, QColor(0, 0, 0, 100))
            
            # 绘制背景
            painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
            
            # 绘制背景边框
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.drawRoundedRect(bg_rect, 6, 6)
            
            # 绘制文本阴影
            painter.setPen(QPen(QColor(0, 0, 0, 150)))
            painter.drawText(x + 1, y_offset + text_rect.height() + 1, instruction)
            
            # 绘制主文本
            painter.setPen(QPen(QColor(255, 255, 255, 255)))
            painter.drawText(x, y_offset + text_rect.height(), instruction)
            
            y_offset += text_rect.height() + 15
            
    def show_control_panel_at_selection(self):
        """在选择区域附近显示控制面板"""
        if self.current_rect.isEmpty():
            return
            
        # 创建控制面板
        if not self.control_panel:
            self.control_panel = ScreenshotControlPanel(self)
            
        # 计算控制面板位置
        panel_x = self.current_rect.right() - self.control_panel.width()
        panel_y = self.current_rect.bottom() + 10
        
        # 确保面板在屏幕范围内
        if panel_x < 0:
            panel_x = self.current_rect.x()
        if panel_x + self.control_panel.width() > self.width():
            panel_x = self.width() - self.control_panel.width()
            
        if panel_y + self.control_panel.height() > self.height():
            panel_y = self.current_rect.y() - self.control_panel.height() - 10
            
        # 显示控制面板
        self.control_panel.move(panel_x, panel_y)
        self.control_panel.show()
        self.show_control_panel = True
        
    def hide_control_panel(self):
        """隐藏控制面板"""
        if self.control_panel:
            self.control_panel.hide()
        self.show_control_panel = False
        
    def confirm_screenshot(self):
        """确认截图"""
        if self.current_rect.isEmpty():
            return
            
        try:
            # 截取选择区域
            x = self.current_rect.x()
            y = self.current_rect.y()
            width = self.current_rect.width()
            height = self.current_rect.height()
            
            # 使用PIL截取指定区域
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            
            if screenshot:
                logging.info(f"截图确认: {width}x{height} at ({x}, {y})")
                self.screenshot_confirmed.emit(screenshot)
            else:
                logging.error("截图失败")
                
        except Exception as e:
            logging.error(f"确认截图时出错: {e}")
            
        finally:
            self.close()
            
    def cancel_screenshot(self):
        """取消截图"""
        logging.info("截图已取消")
        self.screenshot_cancelled.emit()
        self.close()
        
    def closeEvent(self, event):
        """关闭事件"""
        self.hide_control_panel()
        super().closeEvent(event)


class ScreenshotControlPanel(QFrame):
    """截图控制面板"""
    
    def __init__(self, parent_overlay):
        super().__init__(parent_overlay)
        self.parent_overlay = parent_overlay
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setFixedSize(200, 60)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 220);
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 8px;
            }
            QPushButton {
                background-color: rgba(0, 120, 215, 180);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 215, 220);
            }
            QPushButton:pressed {
                background-color: rgba(0, 100, 180, 255);
            }
            QPushButton#cancel_btn {
                background-color: rgba(180, 50, 50, 180);
            }
            QPushButton#cancel_btn:hover {
                background-color: rgba(180, 50, 50, 220);
            }
        """)
        
        # 创建布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.clicked.connect(self.parent_overlay.cancel_screenshot)
        layout.addWidget(self.cancel_btn)
        
        # 确认按钮
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.clicked.connect(self.parent_overlay.confirm_screenshot)
        layout.addWidget(self.confirm_btn)


class AdvancedScreenshotManager:
    """高级截图管理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.overlay = None
        
    def start_screenshot(self) -> None:
        """开始截图"""
        try:
            # 如果已有覆盖层，先关闭
            if self.overlay:
                self.overlay.close()
                
            # 创建新的覆盖层
            self.overlay = ScreenshotOverlay()
            
            # 连接信号
            self.overlay.screenshot_confirmed.connect(self._on_screenshot_confirmed)
            self.overlay.screenshot_cancelled.connect(self._on_screenshot_cancelled)
            
            # 显示覆盖层
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
            
            logging.info("高级截图模式已启动")
            
        except Exception as e:
            logging.error(f"启动截图失败: {e}")
            
    def _on_screenshot_confirmed(self, screenshot):
        """截图确认回调"""
        # 这里可以添加回调函数或信号
        logging.info("截图已确认")
        
    def _on_screenshot_cancelled(self):
        """截图取消回调"""
        logging.info("截图已取消")
        
    def cleanup(self):
        """清理资源"""
        if self.overlay:
            self.overlay.close()
            self.overlay = None