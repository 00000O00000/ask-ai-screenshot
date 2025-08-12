#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析 - 主窗口界面
包含主程序界面和各个配置页面
"""

import os
import uuid
import time
import logging


from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QComboBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from custom_window import CustomMessageBox, NotificationWindow, MarkdownViewer
from util import TaskManager


class WorkerThread(QThread):
    """工作线程"""
    
    status_update = pyqtSignal(str)
    task_completed = pyqtSignal(str)
    task_failed = pyqtSignal(str)
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.task_func(*self.args, **self.kwargs)
            self.task_completed.emit(result)
        except Exception as e:
            self.task_failed.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, config_manager, screenshot_manager, ocr_manager, ai_client_manager, email_manager):
        super().__init__()
        self.config_manager = config_manager
        self.screenshot_manager = screenshot_manager
        self.ocr_manager = ocr_manager
        self.ai_client_manager = ai_client_manager
        self.email_manager = email_manager
        self.task_manager = TaskManager()
        
        self.current_image = None
        self.worker_thread = None
        
        self.init_ui()
        self.connect_signals()
        self.setup_hotkey()
        self.load_config_to_ui()  # 加载配置到界面控件
        

        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI截图分析")
        self.setGeometry(100, 100, 1000, 600)
        
        # 设置窗口图标
        try:
            from icon_data import get_icon_data
            icon_data = get_icon_data()
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except ImportError:
            # 如果icon_data模块不存在，回退到文件方式
            if os.path.exists('favicon.ico'):
                self.setWindowIcon(QIcon('favicon.ico'))
        
        # 设置主题颜色和全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fffe;
                font-size: 16px;  /* 全局字体放大2px */
            }
            QTabWidget::pane {
                border: 1px solid #c0c4cc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e8f5e8;
                padding: 10px 18px;  /* 增加内边距 */
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 16px;
            }
            QTabBar::tab:selected {
                background-color: #a8d8a8;
                color: white;
            }
            QPushButton {
                background-color: #a8d8a8;
                color: white;
                border: none;
                padding: 12px 20px;  /* 增加内边距 */
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
                min-height: 20px;  /* 增加最小高度 */
            }
            QPushButton:hover {
                background-color: #90c890;
            }
            QPushButton:pressed {
                background-color: #78b878;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton:focus {
                outline: none;  /* 去除焦点虚线框 */
                border: none;  /* 去除焦点边框 */
            }
            QListWidget {
                font-size: 15px;
                padding: 8px;  /* 增加内边距 */
                outline: none;  /* 去除焦点虚线框 */
            }
            QListWidget::item {
                padding: 8px 12px;  /* 增加列表项高度和内边距 */
                border-bottom: 1px solid #e0e0e0;
                min-height: 25px;  /* 增加选项高度5px */
            }
            QListWidget::item:selected {
                background-color: #a8d8a8;  /* 选中时绿色背景 */
                color: white;  /* 选中时白色文字 */
            }
            QListWidget::item:hover {
                background-color: #e8f5e8;  /* 悬停时浅绿色背景 */
            }
            QListWidget:focus {
                outline: none;  /* 去除焦点虚线框 */
                border: 1px solid #a8d8a8;  /* 焦点时绿色边框 */
            }
            QLineEdit {
                font-size: 16px;
                padding: 8px 12px;  /* 增加内边距 */
                min-height: 20px;  /* 增加最小高度 */
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QLineEdit:focus {
                outline: none;  /* 去除焦点虚线框 */
                border: 2px solid #a8d8a8;  /* 焦点时绿色边框 */
            }
            QComboBox {
                font-size: 16px;
                padding: 8px 12px;  /* 增加内边距 */
                min-height: 25px;  /* 增加最小高度5px */
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QComboBox:focus {
                outline: none;  /* 去除焦点虚线框 */
                border: 2px solid #a8d8a8;  /* 焦点时绿色边框 */
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                outline: none;  /* 去除下拉列表焦点虚线框 */
                selection-background-color: #a8d8a8;  /* 下拉选项选中时绿色背景 */
                selection-color: white;  /* 下拉选项选中时白色文字 */
            }
            QComboBox QAbstractItemView::item {
                min-height: 25px;  /* 下拉选项高度增加5px */
                padding: 5px 8px;  /* 下拉选项内边距 */
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #a8d8a8;  /* 选中时绿色背景 */
                color: white;  /* 选中时白色文字 */
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8f5e8;  /* 悬停时浅绿色背景 */
            }
            QLabel {
                font-size: 16px;
                padding: 4px;  /* 增加内边距 */
            }
            QTextEdit {
                font-size: 16px;
                padding: 8px;  /* 增加内边距 */
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTextEdit:focus {
                outline: none;  /* 去除焦点虚线框 */
                border: 2px solid #a8d8a8;  /* 焦点时绿色边框 */
            }
            QSpinBox, QDoubleSpinBox {
                font-size: 16px;
                padding: 8px 12px;  /* 增加内边距 */
                min-height: 20px;  /* 增加最小高度 */
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                outline: none;  /* 去除焦点虚线框 */
                border: 2px solid #a8d8a8;  /* 焦点时绿色边框 */
            }
            QCheckBox {
                font-size: 16px;
                padding: 4px;  /* 增加内边距 */
            }
            QCheckBox:focus {
                outline: none;  /* 去除焦点虚线框 */
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 添加各个页面
        self.create_home_page()
        self.create_ai_config_page()
        self.create_prompt_config_page()
        self.create_ocr_config_page()
        self.create_other_config_page()
        self.create_config_file_page()
        self.create_about_page()
    
    def create_home_page(self):
        """创建主页"""
        home_widget = QWidget()
        self.tab_widget.addTab(home_widget, "主页")
        
        layout = QHBoxLayout(home_widget)
        
        # 左侧控制台
        control_panel = QGroupBox("控制台")
        control_panel.setMaximumWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # 截图按钮
        self.screenshot_btn = QPushButton("开始截图")
        self.screenshot_btn.clicked.connect(self.start_screenshot)
        control_layout.addWidget(self.screenshot_btn)
        
        # 从剪贴板导入按钮
        self.clipboard_btn = QPushButton("从剪贴板导入图片")
        self.clipboard_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #333;
                border: 1px solid #ccc;
                padding: 12px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.clipboard_btn.clicked.connect(self.import_from_clipboard)
        control_layout.addWidget(self.clipboard_btn)
        
        # 图片处理方式选择
        process_group = QGroupBox("图片处理方式")
        process_layout = QVBoxLayout(process_group)
        
        self.process_combo = QComboBox()
        self.process_combo.addItems(["OCR图片为文字后提交", "直接提交图片"])
        process_layout.addWidget(self.process_combo)
        
        control_layout.addWidget(process_group)
        
        # 提示词选择
        prompt_group = QGroupBox("提示词选择")
        prompt_layout = QVBoxLayout(prompt_group)
        
        self.prompt_combo = QComboBox()
        self.update_prompt_combo()
        prompt_layout.addWidget(self.prompt_combo)
        
        control_layout.addWidget(prompt_group)
        
        # 强制停止按钮
        self.stop_btn = QPushButton("强制停止任务")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_task)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addStretch()
        layout.addWidget(control_panel)
        
        # 右侧输出区
        output_panel = QGroupBox("输出区")
        output_layout = QVBoxLayout(output_panel)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-weight: bold; color: #666;")
        output_layout.addWidget(self.status_label)
        
        # 输出文本区 - 使用MarkdownViewer支持Markdown渲染
        self.output_text = MarkdownViewer()
        self.output_text.setPlaceholderText("AI分析结果将在这里显示...")
        output_layout.addWidget(self.output_text)
        
        layout.addWidget(output_panel)
    
    def create_ai_config_page(self):
        """创建AI模型配置页面"""
        ai_widget = QWidget()
        self.tab_widget.addTab(ai_widget, "大模型配置")
        
        layout = QHBoxLayout(ai_widget)
        
        # 左侧模型列表
        list_panel = QWidget()
        list_panel.setMaximumWidth(250)
        list_layout = QVBoxLayout(list_panel)
        
        self.ai_model_list = QListWidget()
        self.update_ai_model_list()
        self.ai_model_list.currentItemChanged.connect(self.on_ai_model_selected)
        list_layout.addWidget(self.ai_model_list)
        
        # 按钮组 - 田字型排布
        btn_grid_layout = QGridLayout()
        self.add_ai_btn = QPushButton("增加")
        self.add_ai_btn.clicked.connect(self.add_ai_model)
        self.del_ai_btn = QPushButton("删除")
        self.del_ai_btn.clicked.connect(self.delete_ai_model)
        self.copy_ai_btn = QPushButton("复制")
        self.copy_ai_btn.clicked.connect(self.copy_ai_model)
        self.save_ai_btn = QPushButton("保存")
        self.save_ai_btn.clicked.connect(self.save_ai_model)
        
        # 田字型排布：2x2网格
        btn_grid_layout.addWidget(self.add_ai_btn, 0, 0)
        btn_grid_layout.addWidget(self.del_ai_btn, 0, 1)
        btn_grid_layout.addWidget(self.copy_ai_btn, 1, 0)
        btn_grid_layout.addWidget(self.save_ai_btn, 1, 1)
        list_layout.addLayout(btn_grid_layout)
        
        layout.addWidget(list_panel)
        
        # 右侧配置区
        config_panel = QGroupBox("模型配置")
        config_layout = QFormLayout(config_panel)
        
        self.ai_name_edit = QLineEdit()
        self.ai_model_id_edit = QLineEdit()
        self.ai_endpoint_edit = QLineEdit()
        self.ai_endpoint_edit.setText("https://api.siliconflow.cn/v1")
        self.ai_endpoint_edit.setPlaceholderText("请输入API基础URL，如：https://api.siliconflow.cn/v1")
        self.ai_key_edit = QLineEdit()
        self.ai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_max_tokens_spin = QSpinBox()
        self.ai_max_tokens_spin.setRange(0, 100000)
        self.ai_temperature_spin = QDoubleSpinBox()
        self.ai_temperature_spin.setRange(0.0, 2.0)
        self.ai_temperature_spin.setSingleStep(0.1)

        self.ai_vision_check = QCheckBox()
        
        config_layout.addRow("显示名称:", self.ai_name_edit)
        config_layout.addRow("模型ID:", self.ai_model_id_edit)
        config_layout.addRow("API端点:", self.ai_endpoint_edit)
        config_layout.addRow("API Key:", self.ai_key_edit)
        config_layout.addRow("最大令牌数:", self.ai_max_tokens_spin)
        config_layout.addRow("温度:", self.ai_temperature_spin)

        config_layout.addRow("支持视觉:", self.ai_vision_check)
        
        layout.addWidget(config_panel)
    
    def create_prompt_config_page(self):
        """创建提示词配置页面"""
        prompt_widget = QWidget()
        self.tab_widget.addTab(prompt_widget, "提示词配置")
        
        layout = QHBoxLayout(prompt_widget)
        
        # 左侧提示词列表
        list_panel = QWidget()
        list_panel.setMaximumWidth(250)
        list_layout = QVBoxLayout(list_panel)
        
        self.prompt_list = QListWidget()
        # 禁用水平滚动条以启用文本省略
        self.prompt_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.prompt_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.update_prompt_list()
        self.prompt_list.currentItemChanged.connect(self.on_prompt_selected)
        list_layout.addWidget(self.prompt_list)
        
        # 按钮组 - 田字型排布
        btn_grid_layout = QGridLayout()
        self.add_prompt_btn = QPushButton("增加")
        self.add_prompt_btn.clicked.connect(self.add_prompt)
        self.del_prompt_btn = QPushButton("删除")
        self.del_prompt_btn.clicked.connect(self.delete_prompt)
        self.copy_prompt_btn = QPushButton("复制")
        self.copy_prompt_btn.clicked.connect(self.copy_prompt)
        self.save_prompt_btn = QPushButton("保存")
        self.save_prompt_btn.clicked.connect(self.save_prompt)
        
        # 田字型排布：2x2网格
        btn_grid_layout.addWidget(self.add_prompt_btn, 0, 0)
        btn_grid_layout.addWidget(self.del_prompt_btn, 0, 1)
        btn_grid_layout.addWidget(self.copy_prompt_btn, 1, 0)
        btn_grid_layout.addWidget(self.save_prompt_btn, 1, 1)
        list_layout.addLayout(btn_grid_layout)
        
        layout.addWidget(list_panel)
        
        # 右侧配置区
        config_panel = QGroupBox("提示词配置")
        config_layout = QFormLayout(config_panel)
        
        self.prompt_name_edit = QLineEdit()
        self.prompt_content_edit = QTextEdit()
        self.prompt_model_combo = QComboBox()
        self.update_prompt_model_combo()
        
        config_layout.addRow("提示词名称:", self.prompt_name_edit)
        config_layout.addRow("使用模型:", self.prompt_model_combo)
        config_layout.addRow("提示词内容:", self.prompt_content_edit)
        
        layout.addWidget(config_panel)
    
    def create_ocr_config_page(self):
        """创建OCR配置页面"""
        ocr_widget = QWidget()
        self.tab_widget.addTab(ocr_widget, "OCR配置")
        
        layout = QHBoxLayout(ocr_widget)
        
        # 左侧配置列表
        list_panel = QWidget()
        list_panel.setMaximumWidth(250)
        list_layout = QVBoxLayout(list_panel)
        
        self.ocr_config_list = QListWidget()
        self.ocr_config_list.addItems(["OCR引擎选择", "腾讯云配置", "视觉模型配置", "引擎说明"])
        self.ocr_config_list.currentItemChanged.connect(self.on_ocr_config_selected)
        list_layout.addWidget(self.ocr_config_list)
        
        # 添加保存按钮
        self.save_ocr_btn = QPushButton("保存配置")
        self.save_ocr_btn.clicked.connect(self.save_current_config)
        list_layout.addWidget(self.save_ocr_btn)
        
        layout.addWidget(list_panel)
        
        # 右侧配置区
        self.ocr_config_stack = QWidget()
        self.ocr_config_layout = QVBoxLayout(self.ocr_config_stack)
        
        # OCR引擎选择
        self.ocr_engine_panel = QGroupBox("OCR引擎选择")
        engine_layout = QFormLayout(self.ocr_engine_panel)
        
        self.ocr_engine_combo = QComboBox()
        self.ocr_engine_combo.addItems(["新野图床+云智OCR（免费）", "腾讯云OCR", "视觉模型OCR"])
        self.ocr_engine_combo.currentTextChanged.connect(self.on_ocr_engine_changed)
        self.ocr_language_combo = QComboBox()
        self.ocr_language_combo.addItems(["中文", "英文", "中英文混合"])
        self.ocr_language_combo.currentTextChanged.connect(self.on_ocr_language_changed)
        
        engine_layout.addRow("OCR引擎:", self.ocr_engine_combo)
        engine_layout.addRow("识别语言:", self.ocr_language_combo)
        
        # 腾讯云配置
        self.tencent_config_panel = QGroupBox("腾讯云配置")
        tencent_layout = QFormLayout(self.tencent_config_panel)
        
        self.tencent_id_edit = QLineEdit()
        self.tencent_key_edit = QLineEdit()
        self.tencent_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        tencent_layout.addRow("Secret ID:", self.tencent_id_edit)
        tencent_layout.addRow("Secret Key:", self.tencent_key_edit)
        
        # 引擎说明
        self.engine_info_panel = QGroupBox("OCR引擎说明")
        engine_info_layout = QVBoxLayout(self.engine_info_panel)
        
        info_label = QLabel(
            "<h3>1. 新野图床+云智OCR</h3>"
            "<p><b>[方便]</b> 使用公益接口，免费无限制，无需额外配置</p>"
            "<p><b>缺点：</b> 无隐私保护、质量不高、不稳定，有相关要求请勿选择</p>"
            "<br>"
            "<h3>2. 腾讯云OCR</h3>"
            "<p><b>[通用]</b> 质量平衡，速度快，隐私性更好</p>"
            "<p><b>缺点：</b> 需要配置私有密钥，有 1000次/月 免费额度</p>"
            "<br>"
            "<h3>3. 视觉模型OCR</h3>"
            "<p><b>[质量]</b> 使用视觉模型，质量好</p>"
            "<p><b>缺点：</b> 速度慢，高成本，不适合即时响应情境</p>"
        )
        info_label.setStyleSheet("color: #333; font-size: 12px; padding: 15px; line-height: 1.4;")
        info_label.setWordWrap(True)
        engine_info_layout.addWidget(info_label)
        
        # 视觉模型配置
        self.vision_model_config_panel = QGroupBox("视觉模型配置")
        vision_layout = QFormLayout(self.vision_model_config_panel)
        
        self.vision_model_name_edit = QLineEdit()
        self.vision_model_id_edit = QLineEdit()
        self.vision_api_endpoint_edit = QLineEdit()
        self.vision_api_key_edit = QLineEdit()
        self.vision_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.vision_max_tokens_spin = QSpinBox()
        self.vision_max_tokens_spin.setRange(0, 100000)
        self.vision_temperature_spin = QDoubleSpinBox()
        self.vision_temperature_spin.setRange(0.0, 2.0)
        self.vision_temperature_spin.setSingleStep(0.1)
        self.vision_temperature_spin.setDecimals(1)
        
        self.vision_prompt_edit = QTextEdit()
        self.vision_prompt_edit.setMaximumHeight(80)
        self.vision_prompt_edit.setPlaceholderText("请输入OCR识别的提示词...")
        
        vision_layout.addRow("模型名称:", self.vision_model_name_edit)
        vision_layout.addRow("模型ID:", self.vision_model_id_edit)
        vision_layout.addRow("API端点:", self.vision_api_endpoint_edit)
        vision_layout.addRow("API密钥:", self.vision_api_key_edit)
        vision_layout.addRow("最大令牌数:", self.vision_max_tokens_spin)
        vision_layout.addRow("温度:", self.vision_temperature_spin)
        vision_layout.addRow("OCR提示词:", self.vision_prompt_edit)
        
        self.ocr_config_layout.addWidget(self.ocr_engine_panel)
        self.ocr_config_layout.addWidget(self.tencent_config_panel)
        self.ocr_config_layout.addWidget(self.vision_model_config_panel)
        self.ocr_config_layout.addWidget(self.engine_info_panel)
        self.ocr_config_layout.addStretch()
        
        # 初始化时隐藏所有面板
        self.tencent_config_panel.hide()
        self.vision_model_config_panel.hide()
        self.engine_info_panel.hide()
        
        layout.addWidget(self.ocr_config_stack)
        
        # 默认选择OCR引擎选择
        self.ocr_config_list.setCurrentRow(0)
    
    def create_other_config_page(self):
        """创建其他配置页面"""
        other_widget = QWidget()
        self.tab_widget.addTab(other_widget, "其他配置")
        
        layout = QHBoxLayout(other_widget)
        
        # 左侧配置列表
        list_panel = QWidget()
        list_panel.setMaximumWidth(250)
        list_layout = QVBoxLayout(list_panel)
        
        self.other_config_list = QListWidget()
        self.other_config_list.addItems(["通知方式配置", "SMTP配置", "快捷键配置", "截图配置", "日志等级配置"])
        self.other_config_list.currentItemChanged.connect(self.on_other_config_selected)
        list_layout.addWidget(self.other_config_list)
        
        # 添加保存按钮
        self.save_other_btn = QPushButton("保存配置")
        self.save_other_btn.clicked.connect(self.save_current_config)
        list_layout.addWidget(self.save_other_btn)
        
        layout.addWidget(list_panel)
        
        # 右侧配置区
        self.other_config_stack = QWidget()
        self.other_config_layout = QVBoxLayout(self.other_config_stack)
        
        # 通知方式配置
        self.notification_panel = QGroupBox("通知方式配置")
        notification_layout = QFormLayout(self.notification_panel)
        
        self.notification_type_combo = QComboBox()
        self.notification_type_combo.addItems(["不额外显示", "小弹窗显示", "大弹窗显示", "SMTP发送"])
        self.notification_type_combo.currentTextChanged.connect(self.on_notification_type_changed)
        
        notification_layout.addRow("通知方式:", self.notification_type_combo)
        
        # SMTP配置
        self.smtp_panel = QGroupBox("SMTP配置")
        smtp_layout = QFormLayout(self.smtp_panel)
        
        self.smtp_server_edit = QLineEdit()
        self.smtp_server_edit.setText("smtp.qq.com")
        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_port_spin.setValue(587)
        self.smtp_username_edit = QLineEdit()
        self.smtp_password_edit = QLineEdit()
        self.smtp_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.smtp_to_edit = QLineEdit()
        
        smtp_layout.addRow("SMTP服务器:", self.smtp_server_edit)
        smtp_layout.addRow("端口:", self.smtp_port_spin)
        smtp_layout.addRow("用户名:", self.smtp_username_edit)
        smtp_layout.addRow("密码:", self.smtp_password_edit)
        smtp_layout.addRow("收件人:", self.smtp_to_edit)
        
        # 快捷键配置
        self.hotkey_panel = QGroupBox("快捷键配置")
        hotkey_layout = QFormLayout(self.hotkey_panel)
        
        # 快捷键输入和更改按钮的水平布局
        hotkey_input_layout = QHBoxLayout()
        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setReadOnly(True)
        self.hotkey_edit.setPlaceholderText("点击更改按钮设置快捷键")
        hotkey_input_layout.addWidget(self.hotkey_edit)
        
        self.change_hotkey_btn = QPushButton("更改")
        self.change_hotkey_btn.setFixedWidth(120)
        self.change_hotkey_btn.clicked.connect(self.start_hotkey_capture)
        hotkey_input_layout.addWidget(self.change_hotkey_btn)
        
        hotkey_layout.addRow("截图快捷键:", hotkey_input_layout)
        
        # 快捷键捕获状态
        self.is_capturing_hotkey = False
        self.captured_keys = set()
        
        # 截图配置
        self.screenshot_panel = QGroupBox("截图配置")
        screenshot_layout = QFormLayout(self.screenshot_panel)
        
        # 只保留高级截图模式，移除模式选择
        self.screenshot_quality_combo = QComboBox()
        self.screenshot_quality_combo.addItems(["高质量", "中等质量", "低质量"])
        self.screenshot_quality_combo.currentTextChanged.connect(self.on_screenshot_quality_changed)
        self.screenshot_format_combo = QComboBox()
        self.screenshot_format_combo.addItems(["PNG", "JPEG", "BMP"])
        self.screenshot_format_combo.currentTextChanged.connect(self.on_screenshot_format_changed)
        
        screenshot_layout.addRow("图片质量:", self.screenshot_quality_combo)
        screenshot_layout.addRow("图片格式:", self.screenshot_format_combo)
        
        # 日志等级配置
        self.log_panel = QGroupBox("日志等级配置")
        log_layout = QFormLayout(self.log_panel)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.currentTextChanged.connect(self.on_log_level_changed)
        log_layout.addRow("日志等级:", self.log_level_combo)
        
        # 初始化时隐藏所有面板
        self.notification_panel.hide()
        self.smtp_panel.hide()
        self.hotkey_panel.hide()
        self.screenshot_panel.hide()
        self.log_panel.hide()
        
        self.other_config_layout.addWidget(self.notification_panel)
        self.other_config_layout.addWidget(self.smtp_panel)
        self.other_config_layout.addWidget(self.hotkey_panel)
        self.other_config_layout.addWidget(self.screenshot_panel)
        self.other_config_layout.addWidget(self.log_panel)
        self.other_config_layout.addStretch()
        
        layout.addWidget(self.other_config_stack)
        
        # 默认选择通知方式配置
        self.other_config_list.setCurrentRow(0)
        self.notification_panel.show()
    
    def create_config_file_page(self):
        """创建配置文件设置页面"""
        config_file_widget = QWidget()
        self.tab_widget.addTab(config_file_widget, "配置文件设置")
        
        layout = QVBoxLayout(config_file_widget)
        
        # 配置文件操作
        file_group = QGroupBox("配置文件操作")
        file_layout = QVBoxLayout(file_group)
        
        self.export_config_btn = QPushButton("导出配置文件")
        self.export_config_btn.clicked.connect(self.export_config)
        
        self.import_config_btn = QPushButton("导入配置文件")
        self.import_config_btn.clicked.connect(self.import_config)
        
        self.reset_config_btn = QPushButton("重置为默认配置")
        self.reset_config_btn.clicked.connect(self.reset_config)
        
        self.delete_config_btn = QPushButton("删除本地配置文件")
        self.delete_config_btn.clicked.connect(self.delete_config)
        self.delete_config_btn.setStyleSheet("QPushButton { background-color: #ff6b6b; }")
        
        file_layout.addWidget(self.export_config_btn)
        file_layout.addWidget(self.import_config_btn)
        file_layout.addWidget(self.reset_config_btn)
        file_layout.addWidget(self.delete_config_btn)
        
        layout.addWidget(file_group)
        layout.addStretch()
    
    def create_about_page(self):
        """创建关于页面"""
        about_widget = QWidget()
        self.tab_widget.addTab(about_widget, "关于")
        
        layout = QVBoxLayout(about_widget)
        
        # 程序信息
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <style>
        table {
        border-collapse: collapse;
        width: 100%;
        }
        table, th, td {
        border: 1px solid black;
        padding: 8px;
        }
        </style>
        <h2 style="color: #a8d8a8;">AI截图分析 v1.0.0</h2>
        <p>一个方便的AI截图分析工具，快速使用AI解释你在屏幕上看到的东西，或让他帮你解题。</p>
        <p>软件目前处于测试版，可能存在Bug，若有问题，欢迎前往 Github 提交 issue。</p>
        <p>本软件完全使用 Trae + Claude 4 编写，然后由我和 Claude 4 共同进行用户体验优化。</p>
        <h2>功能特点</h2>
        <ul>
        <li><strong>核心功能</strong>：截图后，将图片OCR为文字或直接提交给AI，并自动显示AI回复结果</li>
        <li><strong>可扩展性</strong>：使用提示词自定义功能，例如 一键截图做题、解释、翻译 等功能</li>
        <li><strong>高度自由</strong>：可自行配置使用的AI接口、OCR接口、提示词</li>
        </ul>
        <h2>注意事项</h2>
        <ul>
        <li>只有多模态模型允许直接提交图片，目前常用的多模态模型有 Claude 3/4 ，gpt-4o，QvQ-72B。而Qwen3全系列、Deepseek系列、Kimi-K2都不是多模态模型，需要先OCR后再提交。若发现模型报错400，请检查此配置是否正确。</li>
        <li>若需要联网功能，请使用秘塔API，赠送额度不少，且付费很便宜。</li>
        </ul>
        <h2>推荐AI服务商</h2>
        <table style="width: 100%;border-collapse: collapse;">
        <thead>
        <tr>
        <th>名称</th>
        <th>推荐理由</th>
        <th>链接地址</th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td>硅基流动</td>
        <td>模型齐全，稳定，价格合理</td>
        <td>https://cloud.siliconflow.cn/models</td>
        </tr>
        <tr>
        <td>魔搭社区</td>
        <td>Qwen3全系列，每日2000次免费</td>
        <td>https://www.modelscope.cn/my/myaccesstoken</td>
        </tr>
        <tr>
        <td>秘塔AI</td>
        <td>超强、超快联网搜索</td>
        <td>https://metaso.cn/search-api/playground</td>
        </tr>
        <tr>
        <td>V3 API</td>
        <td>最全中转商，400+模型</td>
        <td>https://api.gpt.ge/register?aff=TVyz</td>
        </tr>
        </tbody>
        </table>
        <h2>腾讯OCR配置步骤</h2>
        <p>腾讯云OCR每月有1000次OCR调用次数，如果对精度有要求，推荐使用此OCR</p>
        <ol>
        <li>
        <p><strong>登录腾讯云</strong>：前往链接，登录控制台。https://console.cloud.tencent.com</p>
        </li>
        <li>
        <p><strong>开通OCR服务</strong>：前往链接，开通OCR服务。https://console.cloud.tencent.com/ocr/overview</p>
        </li>
        <li>
        <p><strong>获取密钥对</strong>：前往链接，获取 <code>SecretID</code> 和 <code>SecretKey</code> ，保存到本地。https://console.cloud.tencent.com/cam/capi</p>
        </li>
        <li>
        <p><strong>等待额度到账</strong>：回到开通服务界面，持续刷新，等待免费的1000额度到账，然后在软件中配置密钥对，开始使用OCR服务。</p>
        </li>
        </ol>
        <h2>许可证</h2>
        <p>MIT License</p>
        <p>本项目仅供学习和个人使用，不得用于任何商业化用途。</p>
        <p>Github项目地址：https://github.com/00000O00000/ask-ai-screenshot</p>
        <p>软件图标来源：iconfont</p>
        <p>https://www.iconfont.cn/collections/detail?spm=a313x.user_detail.i1.dc64b3430.6b413a81uspeMj&amp;cid=17714</p>
        <h2>更新日志</h2>
        <h3>v1.0.0</h3>
        <ul>
        <li>初始版本发布</li>
        <li>支持基本的截图、OCR和AI分析功能</li>
        <li>完整的配置管理系统</li>
        <li>多种通知方式</li>
        <li>现代化的用户界面</li>
        </ul>
        """)
        
        layout.addWidget(info_text)
    
    def connect_signals(self):
        """连接信号"""
        # 配置管理器信号
        self.config_manager.config_changed.connect(self.on_config_changed)
        
        # 截图管理器信号
        self.screenshot_manager.screenshot_taken.connect(self.on_screenshot_taken)
        self.screenshot_manager.hotkey_conflict.connect(self.on_hotkey_conflict)
        
        # OCR管理器信号
        self.ocr_manager.ocr_completed.connect(self.on_ocr_completed)
        self.ocr_manager.ocr_failed.connect(self.on_ocr_failed)
        
        # AI客户端管理器信号
        self.ai_client_manager.response_completed.connect(self.on_ai_response_completed)
        self.ai_client_manager.request_failed.connect(self.on_ai_request_failed)
        self.ai_client_manager.streaming_response.connect(self.on_ai_streaming_response)
        self.ai_client_manager.reasoning_content.connect(self.on_ai_reasoning_content)
        
        # 邮件管理器信号
        self.email_manager.email_sent.connect(self.on_email_sent)
        self.email_manager.email_failed.connect(self.on_email_failed)
        
        # 任务管理器信号
        self.task_manager.task_started.connect(self.on_task_started)
        self.task_manager.task_finished.connect(self.on_task_finished)
    
    def setup_hotkey(self):
        """设置快捷键"""
        if not self.screenshot_manager.setup_hotkey():
            CustomMessageBox.warning(self, "警告", "快捷键设置失败，请检查配置")
    
    def start_screenshot(self):
        """开始截图"""
        if self.task_manager.is_running():
            CustomMessageBox.warning(self, "警告", "有任务正在运行，请等待完成后再试")
            return
        
        self.screenshot_manager.start_screenshot()
    
    def import_from_clipboard(self):
        """从剪贴板导入图片"""
        if self.task_manager.is_running():
            CustomMessageBox.warning(self, "警告", "有任务正在运行，请等待完成后再试")
            return
        
        image = self.screenshot_manager.screenshot_from_clipboard()
        if image:
            self.on_screenshot_taken(image)
        else:
            CustomMessageBox.warning(self, "警告", "剪贴板中没有图片")
    
    def stop_task(self):
        """停止任务"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        
        self.ai_client_manager.stop_request()
        self.task_manager.finish_task()
        self.status_label.setText("任务已停止")
    
    def on_screenshot_taken(self, image):
        """截图完成处理"""
        self.current_image = image
        self.process_image()
    
    def process_image(self):
        """处理图片"""
        if not self.current_image:
            return
        
        if not self.task_manager.start_task("图片处理"):
            CustomMessageBox.warning(self, "警告", "有任务正在运行，请等待完成后再试")
            return
        

        
        # 获取当前选择的提示词
        prompt_name = self.prompt_combo.currentText()
        if not prompt_name:
            CustomMessageBox.warning(self, "警告", "请选择提示词")
            self.task_manager.finish_task()
            return
        
        # 获取提示词配置
        prompt_config = None
        prompts = self.config_manager.get_config("prompts")
        if prompts:
            for prompt_id, config in prompts.items():
                if config["name"] == prompt_name:
                    prompt_config = config
                    break
        
        if not prompt_config:
            # 如果没有找到对应的提示词，尝试使用默认提示词
            default_prompt_id = self.config_manager.get_default_prompt_id()
            if default_prompt_id:
                prompt_config = self.config_manager.get_config(f"prompts.{default_prompt_id}")
        
        if not prompt_config:
            CustomMessageBox.warning(self, "警告", "提示词配置不存在")
            self.task_manager.finish_task()
            return
        
        # 检查处理方式
        process_type = self.process_combo.currentIndex()
        
        if process_type == 0:  # OCR后提交
            self.status_label.setText("OCR识别中...")
            self.output_text.set_markdown("")
            
            # 启动OCR工作线程
            self.worker_thread = WorkerThread(self.ocr_manager.recognize_image, self.current_image)
            self.worker_thread.task_completed.connect(lambda text: self.on_ocr_completed(text))
            self.worker_thread.task_completed.connect(lambda text: self.send_ai_request(prompt_config, text, None))
            self.worker_thread.task_failed.connect(self.on_ocr_failed)
            self.worker_thread.start()
        else:  # 直接提交图片
            self.send_ai_request(prompt_config, "", self.current_image)  # 传递图片
    
    def send_ai_request(self, prompt_config, ocr_text="", image=None):
        """发送AI请求"""
        self.status_label.setText("AI分析中...")
        
        # 获取模型ID
        model_id = prompt_config.get("model_id")
        if not model_id:
            CustomMessageBox.warning(self, "警告", "提示词未指定模型")
            self.task_manager.finish_task()
            return
        
        # 清空输出区域，准备接收流式内容
        self.output_text.set_markdown("")
        self.current_reasoning_content = ""
        self.current_response_content = ""
        
        # 初始化性能优化相关属性
        self._update_pending = False
        self._update_timer = getattr(self, '_update_timer', None)
        if not self._update_timer:
            from PyQt6.QtCore import QTimer
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._batch_update_display)
            self._update_timer.setInterval(100)  # 100ms批量更新
        
        # 根据通知配置准备大通知弹窗（如果需要）
        notification_type = self.config_manager.get_config("notification.type")
        if notification_type == "large_popup":
            self.prepare_large_notification()
        
        # 发送请求
        self.ai_client_manager.send_request(
            model_id,
            prompt_config["content"],
            image,  # 使用传入的image参数而不是self.current_image
            ocr_text
        )
    

    
    def on_ai_response_completed(self, response):
        """AI响应完成"""
        self.status_label.setText("分析完成")
        self.task_manager.finish_task()
        
        # 更新主窗口显示（如果没有流式内容，则显示完整响应）
        if not hasattr(self, 'current_response_content') or not self.current_response_content:
            self.output_text.set_markdown(response)
        
        # 根据通知配置显示结果
        self.show_notification(response)
    
    def on_ai_streaming_response(self, content_type, content):
        """处理AI流式响应"""
        if content_type == "content":
            self.current_response_content += content
            self._update_display_content()
            
            # 更新大通知弹窗（如果存在）
            if hasattr(self, 'current_large_notification') and self.current_large_notification:
                self.current_large_notification.append_content(content)
    
    def on_ai_reasoning_content(self, reasoning):
        """处理AI推理内容"""
        self.current_reasoning_content += reasoning
        self._update_display_content()
        
        # 更新大通知弹窗（如果存在）
        if hasattr(self, 'current_large_notification') and self.current_large_notification:
            self.current_large_notification.append_reasoning_content(reasoning)
    
    def _update_display_content(self):
        """更新显示内容（使用批量更新优化）"""
        if not self._update_pending:
            self._update_pending = True
            self._update_timer.start()
    
    def _batch_update_display(self):
        """批量更新显示内容"""
        self._update_pending = False
        
        display_content = ""
        
        if self.current_reasoning_content:
            display_content += f"<div style='background-color: #f0f8ff; padding: 10px; border-left: 4px solid #4a90e2; margin-bottom: 15px; border-radius: 4px;'>\n"
            display_content += f"<h4 style='color: #4a90e2; margin: 0 0 8px 0; font-family: \"Microsoft YaHei\", sans-serif;'>🤔 思考内容</h4>\n"
            display_content += f"<div style='font-family: \"Consolas\", \"Monaco\", monospace; font-size: 13px; color: #666;'>{self.current_reasoning_content}</div>\n"
            display_content += f"</div>\n\n"
        
        if self.current_response_content:
            display_content += f"<div style='background-color: #f8fff8; padding: 10px; border-left: 4px solid #28a745; border-radius: 4px;'>\n"
            display_content += f"<h4 style='color: #28a745; margin: 0 0 8px 0; font-family: \"Microsoft YaHei\", sans-serif;'>💬 回复内容</h4>\n"
            display_content += f"<div style='font-family: \"Microsoft YaHei\", sans-serif;'>{self.current_response_content}</div>\n"
            display_content += f"</div>"
        
        self.output_text.set_markdown(display_content)
    
    def prepare_large_notification(self):
        """准备大通知弹窗"""
        from custom_window import NotificationWindow
        self.current_large_notification = NotificationWindow.show_large_notification_streaming("", self)
    
    def show_notification(self, content):
        """显示通知"""
        notification_type = self.config_manager.get_config("notification.type")
        
        if notification_type == "small_popup":
            # 小弹窗只显示最终回答内容，不显示推理内容
            final_content = getattr(self, 'current_response_content', '') or content
            NotificationWindow.show_small_notification(final_content)
        elif notification_type == "large_popup":
            # 大弹窗已经在流式过程中显示，这里不需要额外操作
            pass
        elif notification_type == "smtp":
            self.email_manager.send_email("AI分析结果", content)
    

    

    
    def on_ocr_completed(self, text):
        """OCR完成"""
        logging.info(f"OCR识别完成: {len(text)} 字符")
    
    def on_ocr_failed(self, error):
        """OCR失败"""
        self.status_label.setText("OCR失败")
        self.task_manager.finish_task()
        CustomMessageBox.critical(self, "错误", f"OCR识别失败: {error}")
    
    def on_ai_request_failed(self, error):
        """AI请求失败"""
        self.status_label.setText("AI请求失败")
        self.task_manager.finish_task()
        CustomMessageBox.critical(self, "错误", f"AI请求失败: {error}")
    
    def on_email_sent(self):
        """邮件发送成功"""
        logging.info("邮件发送成功")
    
    def on_email_failed(self, error):
        """邮件发送失败"""
        CustomMessageBox.warning(self, "警告", f"邮件发送失败: {error}")
    
    def on_hotkey_conflict(self, error):
        """快捷键冲突"""
        CustomMessageBox.warning(self, "警告", f"快捷键冲突: {error}\n请修改快捷键配置")
    
    def on_task_started(self):
        """任务开始"""
        self.stop_btn.setEnabled(True)
        self.screenshot_btn.setEnabled(False)
        self.clipboard_btn.setEnabled(False)
    
    def on_task_finished(self):
        """任务结束"""
        self.stop_btn.setEnabled(False)
        self.screenshot_btn.setEnabled(True)
        self.clipboard_btn.setEnabled(True)
    
    def on_config_changed(self):
        """配置改变"""
        # 只更新下拉框，不重新加载整个UI配置
        # 避免在保存配置时触发UI重载导致配置丢失
        self.update_prompt_combo()
        self.update_prompt_model_combo()
        # 注释掉 load_config_to_ui() 以避免循环更新
        # self.load_config_to_ui()
    
    def update_prompt_combo(self):
        """更新提示词下拉框"""
        self.prompt_combo.clear()
        prompts = self.config_manager.get_config("prompts")
        if prompts:
            for prompt_config in prompts.values():
                self.prompt_combo.addItem(prompt_config["name"])
            # 自动选择第一个提示词
            if self.prompt_combo.count() > 0:
                self.prompt_combo.setCurrentIndex(0)
    
    def update_ai_model_list(self):
        """更新AI模型列表"""
        self.ai_model_list.clear()
        models = self.config_manager.get_config("ai_models")
        if models:
            for model_config in models.values():
                item = QListWidgetItem(model_config["name"])
                item.setData(Qt.ItemDataRole.UserRole, model_config["id"])
                self.ai_model_list.addItem(item)
    
    def update_prompt_list(self):
        """更新提示词列表"""
        self.prompt_list.clear()
        prompts = self.config_manager.get_config("prompts")
        if prompts:
            for prompt_config in prompts.values():
                item = QListWidgetItem(prompt_config["name"])
                item.setData(Qt.ItemDataRole.UserRole, prompt_config["id"])
                # 设置工具提示显示完整文本
                item.setToolTip(prompt_config["name"])
                self.prompt_list.addItem(item)
    
    def update_prompt_model_combo(self):
        """更新提示词模型下拉框"""
        self.prompt_model_combo.clear()
        models = self.config_manager.get_config("ai_models")
        if models:
            for model_id, model_config in models.items():
                self.prompt_model_combo.addItem(model_config["name"], model_id)
    
    def load_config_to_ui(self):
        """加载配置到界面"""
        # 加载OCR配置
        ocr_config = self.config_manager.get_config("ocr")
        if ocr_config:
            engine_map = {"xinyew": 0, "tencent": 1, "vision_model": 2}
            self.ocr_engine_combo.setCurrentIndex(engine_map.get(ocr_config.get("engine"), 0))
            
            # 加载OCR语言配置
            language_map = {"zh": 0, "en": 1, "zh-en": 2}
            self.ocr_language_combo.setCurrentIndex(language_map.get(ocr_config.get("language"), 2))
            
            tencent_config = ocr_config.get("tencent", {})
            self.tencent_id_edit.setText(tencent_config.get("secret_id", ""))
            self.tencent_key_edit.setText(tencent_config.get("secret_key", ""))
            
            # 加载视觉模型配置
            vision_config = ocr_config.get("vision_model", {})
            self.vision_model_name_edit.setText(vision_config.get("name", ""))
            self.vision_model_id_edit.setText(vision_config.get("model_id", ""))
            self.vision_api_endpoint_edit.setText(vision_config.get("api_endpoint", ""))
            self.vision_api_key_edit.setText(vision_config.get("api_key", ""))
            self.vision_max_tokens_spin.setValue(vision_config.get("max_tokens", 0))
            self.vision_temperature_spin.setValue(vision_config.get("temperature", 0.3))
            self.vision_prompt_edit.setPlainText(vision_config.get("prompt", "请识别图片中的文字内容，并格式化后给我。只返回识别到的文字，不要添加任何解释或说明。"))
        
        # 加载通知配置
        notification_config = self.config_manager.get_config("notification")
        if notification_config:
            # 修正映射：下拉框选项是["不额外显示", "小弹窗显示", "大弹窗显示", "SMTP发送"]
            type_map = {"none": 0, "small_popup": 1, "large_popup": 2, "smtp": 3}
            self.notification_type_combo.setCurrentIndex(type_map.get(notification_config.get("type"), 0))
            
            smtp_config = notification_config.get("smtp", {})
            self.smtp_server_edit.setText(smtp_config.get("server", ""))
            self.smtp_port_spin.setValue(smtp_config.get("port", 587))
            self.smtp_username_edit.setText(smtp_config.get("username", ""))
            self.smtp_password_edit.setText(smtp_config.get("password", ""))
            self.smtp_to_edit.setText(smtp_config.get("to_email", ""))
        
        # 加载快捷键配置
        hotkey_config = self.config_manager.get_config("hotkey")
        if hotkey_config:
            hotkey_text = hotkey_config.get("screenshot", "alt+shift+d")
            if hotkey_text:
                self.hotkey_edit.setText(hotkey_text)
            else:
                self.hotkey_edit.setText("alt+shift+d")
        
        # 加载截图配置（只保留质量和格式）
        screenshot_config = self.config_manager.get_config("screenshot")
        if screenshot_config:
            quality_map = {"high": 0, "medium": 1, "low": 2}
            self.screenshot_quality_combo.setCurrentIndex(quality_map.get(screenshot_config.get("quality"), 0))
            
            format_map = {"PNG": 0, "JPEG": 1, "BMP": 2}
            self.screenshot_format_combo.setCurrentIndex(format_map.get(screenshot_config.get("format"), 0))
        
        # 加载日志配置
        logging_config = self.config_manager.get_config("logging")
        if logging_config:
            level_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
            self.log_level_combo.setCurrentIndex(level_map.get(logging_config.get("level"), 1))
        
        # 更新截图按钮文本显示当前快捷键
        self.update_screenshot_button_text()
    

    

    

    
    def update_screenshot_button_text(self):
        """更新截图按钮文本以显示当前快捷键"""
        hotkey_config = self.config_manager.get_config("hotkey")
        if hotkey_config:
            hotkey_text = hotkey_config.get("screenshot", "alt+shift+d")
        else:
            hotkey_text = "alt+shift+d"
        
        self.screenshot_btn.setText(f"开始截图 ({hotkey_text})")
    
    # AI模型配置相关方法
    def on_ai_model_selected(self, current, previous):
        """AI模型选择改变"""
        # 自动保存之前选中的模型配置
        if previous and hasattr(self, 'ai_name_edit'):
            previous_model_id = previous.data(Qt.ItemDataRole.UserRole)
            if previous_model_id:
                self._auto_save_ai_model(previous_model_id)
        
        if current:
            model_id = current.data(Qt.ItemDataRole.UserRole)
            model_config = self.config_manager.get_config(f"ai_models.{model_id}")
            if model_config:
                self.ai_name_edit.setText(model_config.get("name", ""))
                self.ai_model_id_edit.setText(model_config.get("model_id", ""))
                
                # 显示API端点时去掉/chat/completions后缀
                api_endpoint = model_config.get("api_endpoint", "")
                if api_endpoint.endswith('/chat/completions'):
                    api_endpoint = api_endpoint[:-len('/chat/completions')]
                self.ai_endpoint_edit.setText(api_endpoint)
                
                self.ai_key_edit.setText(model_config.get("api_key", ""))
                self.ai_max_tokens_spin.setValue(model_config.get("max_tokens", 0))
                self.ai_temperature_spin.setValue(model_config.get("temperature", 0.3))

                self.ai_vision_check.setChecked(model_config.get("vision_support", True))
    
    def add_ai_model(self):
        """添加AI模型"""
        model_id = f"model_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        model_config = {
            "id": model_id,
            "name": "新模型",
            "model_id": "",
            "api_endpoint": "https://api.siliconflow.cn/v1",
            "api_key": "",
            "max_tokens": 0,
            "temperature": 0.3,

            "vision_support": True
        }
        
        self.config_manager.set_config(f"ai_models.{model_id}", model_config)
        self.config_manager.save_config()
        self.update_ai_model_list()
        self.update_prompt_model_combo()
        
        # 选择新添加的模型
        for i in range(self.ai_model_list.count()):
            item = self.ai_model_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == model_id:
                self.ai_model_list.setCurrentItem(item)
                break
    
    def delete_ai_model(self):
        """删除AI模型"""
        current_item = self.ai_model_list.currentItem()
        if not current_item:
            CustomMessageBox.warning(self, "警告", "请选择要删除的模型")
            return
        
        if CustomMessageBox.question(self, "确认", "确定要删除选中的模型吗？"):
            model_id = current_item.data(Qt.ItemDataRole.UserRole)
            # 直接删除指定的模型配置
            self.config_manager.set_config(f"ai_models.{model_id}", None)
            self.config_manager.save_config()
            self.update_ai_model_list()
            self.update_prompt_model_combo()
    
    def copy_ai_model(self):
        """复制AI模型"""
        current_item = self.ai_model_list.currentItem()
        if not current_item:
            CustomMessageBox.warning(self, "警告", "请选择要复制的模型")
            return
        
        model_id = current_item.data(Qt.ItemDataRole.UserRole)
        model_config = self.config_manager.get_config(f"ai_models.{model_id}")
        if model_config:
            new_model_id = f"model_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            new_config = model_config.copy()
            new_config["id"] = new_model_id
            new_config["name"] = f"{model_config['name']}_副本"
            
            self.config_manager.set_config(f"ai_models.{new_model_id}", new_config)
            self.config_manager.save_config()
            self.update_ai_model_list()
            self.update_prompt_model_combo()
            
            # 选择新添加的模型
            for i in range(self.ai_model_list.count()):
                item = self.ai_model_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == new_model_id:
                    self.ai_model_list.setCurrentItem(item)
                    break
    
    def save_ai_model(self):
        """保存AI模型"""
        current_item = self.ai_model_list.currentItem()
        if not current_item:
            CustomMessageBox.warning(self, "警告", "请选择要保存的模型")
            return
        
        # 验证配置
        if not all([
            self.ai_name_edit.text().strip(),
            self.ai_model_id_edit.text().strip(),
            self.ai_endpoint_edit.text().strip(),
            self.ai_key_edit.text().strip()
        ]):
            CustomMessageBox.warning(self, "警告", "请填写完整的模型配置")
            return
        
        model_id = current_item.data(Qt.ItemDataRole.UserRole)
        
        # 处理API端点，自动添加/chat/completions
        api_endpoint = self.ai_endpoint_edit.text().strip()
        if api_endpoint and not api_endpoint.endswith('/chat/completions'):
            if api_endpoint.endswith('/'):
                api_endpoint = api_endpoint.rstrip('/') + '/chat/completions'
            else:
                api_endpoint = api_endpoint + '/chat/completions'
        
        model_config = {
            "id": model_id,
            "name": self.ai_name_edit.text().strip(),
            "model_id": self.ai_model_id_edit.text().strip(),
            "api_endpoint": api_endpoint,
            "api_key": self.ai_key_edit.text().strip(),
            "max_tokens": self.ai_max_tokens_spin.value(),
            "temperature": self.ai_temperature_spin.value(),

            "vision_support": self.ai_vision_check.isChecked()
        }
        
        self.config_manager.set_config(f"ai_models.{model_id}", model_config)
        self.config_manager.save_config()
        self.update_ai_model_list()
        CustomMessageBox.information(self, "成功", "模型配置已保存")
    
    # 提示词配置相关方法
    def on_prompt_selected(self, current, previous):
        """提示词选择改变"""
        # 自动保存之前选择的提示词（如果有的话）
        if previous and hasattr(self, 'prompt_name_edit'):
            self._auto_save_prompt(previous)
        
        if current:
            prompt_id = current.data(Qt.ItemDataRole.UserRole)
            prompt_config = self.config_manager.get_config(f"prompts.{prompt_id}")
            if prompt_config:
                self.prompt_name_edit.setText(prompt_config.get("name", ""))
                self.prompt_content_edit.setPlainText(prompt_config.get("content", ""))
                
                # 设置模型选择
                model_id = prompt_config.get("model_id", "")
                for i in range(self.prompt_model_combo.count()):
                    if self.prompt_model_combo.itemData(i) == model_id:
                        self.prompt_model_combo.setCurrentIndex(i)
                        break
    
    def add_prompt(self):
        """添加提示词"""
        prompt_id = f"prompt_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        # 获取默认模型ID
        default_model_id = self.config_manager.get_default_model_id() or ""
        prompt_config = {
            "id": prompt_id,
            "name": "新提示词",
            "content": "请分析这张图片的内容。",
            "model_id": default_model_id
        }
        
        self.config_manager.set_config(f"prompts.{prompt_id}", prompt_config)
        self.config_manager.save_config()
        self.update_prompt_list()
        self.update_prompt_combo()
        
        # 选择新添加的提示词
        for i in range(self.prompt_list.count()):
            item = self.prompt_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == prompt_id:
                self.prompt_list.setCurrentItem(item)
                break
    
    def delete_prompt(self):
        """删除提示词"""
        current_item = self.prompt_list.currentItem()
        if not current_item:
            CustomMessageBox.warning(self, "警告", "请选择要删除的提示词")
            return
        
        if CustomMessageBox.question(self, "确认", "确定要删除选中的提示词吗？"):
            prompt_id = current_item.data(Qt.ItemDataRole.UserRole)
            # 直接删除指定的提示词配置
            self.config_manager.set_config(f"prompts.{prompt_id}", None)
            self.config_manager.save_config()
            self.update_prompt_list()
            self.update_prompt_combo()
    
    def copy_prompt(self):
        """复制提示词"""
        current_item = self.prompt_list.currentItem()
        if not current_item:
            CustomMessageBox.warning(self, "警告", "请选择要复制的提示词")
            return
        
        prompt_id = current_item.data(Qt.ItemDataRole.UserRole)
        prompt_config = self.config_manager.get_config(f"prompts.{prompt_id}")
        if prompt_config:
            new_prompt_id = f"prompt_{uuid.uuid4().hex[:8]}_{int(time.time())}"
            new_config = prompt_config.copy()
            new_config["id"] = new_prompt_id
            new_config["name"] = f"{prompt_config['name']}_副本"
            
            self.config_manager.set_config(f"prompts.{new_prompt_id}", new_config)
            self.config_manager.save_config()
            self.update_prompt_list()
            self.update_prompt_combo()
            
            # 选择新添加的提示词
            for i in range(self.prompt_list.count()):
                item = self.prompt_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == new_prompt_id:
                    self.prompt_list.setCurrentItem(item)
                    break
    
    def save_prompt(self):
        """保存提示词"""
        current_item = self.prompt_list.currentItem()
        if not current_item:
            CustomMessageBox.warning(self, "警告", "请选择要保存的提示词")
            return
        
        # 验证配置
        if not all([
            self.prompt_name_edit.text().strip(),
            self.prompt_content_edit.toPlainText().strip()
        ]):
            CustomMessageBox.warning(self, "警告", "请填写完整的提示词配置")
            return
        
        prompt_id = current_item.data(Qt.ItemDataRole.UserRole)
        prompt_config = {
            "id": prompt_id,
            "name": self.prompt_name_edit.text().strip(),
            "content": self.prompt_content_edit.toPlainText().strip(),
            "model_id": self.prompt_model_combo.currentData() or ""
        }
        
        self.config_manager.set_config(f"prompts.{prompt_id}", prompt_config)
        self.config_manager.save_config()
        self.update_prompt_list()
        CustomMessageBox.information(self, "成功", "提示词配置已保存")
    
    def _auto_save_prompt(self, item):
        """自动保存提示词（不显示弹窗）"""
        if not item:
            return
        
        # 检查是否有内容需要保存
        if not hasattr(self, 'prompt_name_edit') or not hasattr(self, 'prompt_content_edit'):
            return
            
        name = self.prompt_name_edit.text().strip()
        content = self.prompt_content_edit.toPlainText().strip()
        
        # 如果有内容则自动保存
        if name and content:
            prompt_id = item.data(Qt.ItemDataRole.UserRole)
            prompt_config = {
                "id": prompt_id,
                "name": name,
                "content": content,
                "model_id": self.prompt_model_combo.currentData() or ""
            }
            
            self.config_manager.set_config(f"prompts.{prompt_id}", prompt_config)
            self.config_manager.save_config()
            # 更新列表项显示的名称
            item.setText(name)
            item.setToolTip(name)
    
    # OCR配置相关方法
    def on_ocr_config_selected(self, current, previous):
        """OCR配置选择改变"""
        # 自动保存之前的配置
        if previous and hasattr(self, 'ocr_engine_combo'):
            self._auto_save_ocr_config()
        
        if current:
            config_name = current.text()
            # 隐藏所有面板
            self.ocr_engine_panel.hide()
            self.tencent_config_panel.hide()
            self.vision_model_config_panel.hide()
            self.engine_info_panel.hide()
            
            # 显示对应面板
            if config_name == "OCR引擎选择":
                self.ocr_engine_panel.show()
            elif config_name == "腾讯云配置":
                self.tencent_config_panel.show()
            elif config_name == "视觉模型配置":
                self.vision_model_config_panel.show()
            elif config_name == "引擎说明":
                self.engine_info_panel.show()
    
    # 其他配置相关方法
    def on_other_config_selected(self, current, previous):
        """其他配置选择改变"""
        # 自动保存之前的配置
        if previous and hasattr(self, 'notification_combo'):
            self._auto_save_other_config()
        
        if current:
            config_name = current.text()
            # 隐藏所有面板
            self.notification_panel.hide()
            self.smtp_panel.hide()
            self.hotkey_panel.hide()
            self.screenshot_panel.hide()
            self.log_panel.hide()
            
            # 显示对应面板
            if config_name == "通知方式配置":
                self.notification_panel.show()
            elif config_name == "SMTP配置":
                self.smtp_panel.show()
            elif config_name == "快捷键配置":
                self.hotkey_panel.show()
            elif config_name == "截图配置":
                self.screenshot_panel.show()
            elif config_name == "日志等级配置":
                self.log_panel.show()
    
    # 配置文件操作方法
    def export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置文件", "config.json", "JSON文件 (*.json)"
        )
        if file_path:
            if self.config_manager.export_config(file_path):
                CustomMessageBox.information(self, "成功", "配置文件导出成功")
            else:
                CustomMessageBox.critical(self, "错误", "配置文件导出失败")
    
    def import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", "", "JSON文件 (*.json)"
        )
        if file_path:
            if self.config_manager.import_config(file_path):
                CustomMessageBox.information(self, "成功", "配置文件导入成功，正在重新初始化界面...")
                # 完整重新初始化界面
                self._reinitialize_after_config_import()
            else:
                CustomMessageBox.critical(self, "错误", "配置文件导入失败")
    
    def _reinitialize_after_config_import(self):
        """配置导入后重新初始化界面"""
        try:
            # 1. 重新连接信号（确保配置变更信号正常工作）
            self.connect_signals()
            
            # 2. 重新设置快捷键
            self.setup_hotkey()
            
            # 3. 重新加载UI配置
            self.load_config_to_ui()
            
            # 4. 重新初始化各个管理器的配置
            self._reinitialize_managers()
            
            # 5. 更新主页按钮文本
            self.update_screenshot_button_text()
            
            logging.info("配置导入后界面重新初始化完成")
            
        except Exception as e:
            logging.error(f"配置导入后重新初始化失败: {e}")
            CustomMessageBox.warning(self, "警告", f"界面重新初始化部分失败: {e}")
    
    def _reinitialize_managers(self):
        """重新初始化各个管理器的配置"""
        try:
            # 重新初始化截图管理器
            if hasattr(self.screenshot_manager, 'setup_hotkey'):
                self.screenshot_manager.setup_hotkey()
            
            # 重新初始化OCR管理器配置
            if hasattr(self.ocr_manager, 'reload_config'):
                self.ocr_manager.reload_config()
            
            # 重新初始化AI客户端管理器配置
            if hasattr(self.ai_client_manager, 'reload_config'):
                self.ai_client_manager.reload_config()
            
            # 重新初始化邮件管理器配置
            if hasattr(self.email_manager, 'reload_config'):
                self.email_manager.reload_config()
                
        except Exception as e:
            logging.error(f"重新初始化管理器失败: {e}")
    
    def reset_config(self):
        """重置配置"""
        if CustomMessageBox.question(self, "确认", "确定要重置为默认配置吗？这将清除所有自定义设置。"):
            if self.config_manager.reset_config():
                CustomMessageBox.information(self, "成功", "配置已重置为默认值，正在重新初始化界面...")
                # 完整重新初始化界面
                self._reinitialize_after_config_import()
            else:
                CustomMessageBox.critical(self, "错误", "重置配置失败")
    
    def delete_config(self):
        """删除配置文件"""
        if CustomMessageBox.question(self, "确认", "确定要删除本地配置文件吗？删除后程序将退出。"):
            if self.config_manager.delete_config():
                CustomMessageBox.information(self, "成功", "配置文件已删除，程序即将退出")
                self.close()
            else:
                CustomMessageBox.critical(self, "错误", "删除配置文件失败")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 静默保存配置（不显示弹窗）
        self.save_current_config_silent()
        
        # 清理资源
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        
        self.screenshot_manager.cleanup()
        event.accept()
    
    def save_current_config(self):
        """保存当前配置"""
        try:
            self._save_config_data()
            
            # 保存配置文件
            if self.config_manager.save_config():
                CustomMessageBox.information(self, "成功", "配置已保存")
            else:
                CustomMessageBox.warning(self, "警告", "配置保存失败")
            
        except Exception as e:
            logging.error(f"保存配置失败: {e}")
            CustomMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def save_current_config_silent(self):
        """静默保存当前配置（不显示弹窗）"""
        try:
            self._save_config_data()
            self.config_manager.save_config(emit_signal=False)  # 避免循环信号
        except Exception as e:
            logging.error(f"保存配置失败: {e}")
    
    def _auto_save_ai_model(self, model_id):
        """自动保存AI模型配置（不显示弹窗）"""
        try:
            name = self.ai_name_edit.text().strip()
            model_id_text = self.ai_model_id_edit.text().strip()
            
            if not name or not model_id_text:
                return
            
            # 获取API端点，如果不以/chat/completions结尾则添加
            api_endpoint = self.ai_endpoint_edit.text().strip()
            if api_endpoint and not api_endpoint.endswith('/chat/completions'):
                if api_endpoint.endswith('/'):
                    api_endpoint = api_endpoint.rstrip('/') + '/chat/completions'
                else:
                    api_endpoint = api_endpoint + '/chat/completions'
            
            model_config = {
                "id": model_id,
                "name": name,
                "model_id": model_id_text,
                "api_endpoint": api_endpoint,
                "api_key": self.ai_key_edit.text(),
                "max_tokens": self.ai_max_tokens_spin.value(),
                "temperature": self.ai_temperature_spin.value(),

                "vision_support": self.ai_vision_check.isChecked()
            }
            
            self.config_manager.set_config(f"ai_models.{model_id}", model_config)
            self.config_manager.save_config(emit_signal=False)  # 避免循环信号
            
            # 更新列表项显示的名称
            for i in range(self.ai_model_list.count()):
                item = self.ai_model_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == model_id:
                    item.setText(name)
                    break
        except Exception as e:
            logging.error(f"自动保存AI模型配置失败: {e}")
    
    def _auto_save_ocr_config(self):
        """自动保存OCR配置（不显示弹窗）"""
        try:
            # 保存OCR配置
            engine_map = {0: "xinyew", 1: "tencent", 2: "vision_model"}
            self.config_manager.set_config("ocr.engine", engine_map.get(self.ocr_engine_combo.currentIndex(), "xinyew"))
            
            self.config_manager.set_config("ocr.tencent.secret_id", self.tencent_id_edit.text())
            self.config_manager.set_config("ocr.tencent.secret_key", self.tencent_key_edit.text())
            
            # 保存视觉模型配置
            if hasattr(self, 'vision_model_name_edit'):
                self.config_manager.set_config("ocr.vision_model.name", self.vision_model_name_edit.text())
                self.config_manager.set_config("ocr.vision_model.model_id", self.vision_model_id_edit.text())
                self.config_manager.set_config("ocr.vision_model.api_endpoint", self.vision_api_endpoint_edit.text())
                self.config_manager.set_config("ocr.vision_model.api_key", self.vision_api_key_edit.text())
                self.config_manager.set_config("ocr.vision_model.max_tokens", self.vision_max_tokens_spin.value())
                self.config_manager.set_config("ocr.vision_model.temperature", self.vision_temperature_spin.value())
                self.config_manager.set_config("ocr.vision_model.prompt", self.vision_prompt_edit.toPlainText())
            
            self.config_manager.save_config()
        except Exception as e:
            logging.error(f"自动保存OCR配置失败: {e}")
    
    def _auto_save_other_config(self):
        """自动保存其他配置（不显示弹窗）"""
        try:
            # 保存通知配置
            type_map = {0: "none", 1: "small_popup", 2: "large_popup", 3: "smtp"}
            self.config_manager.set_config("notification.type", type_map.get(self.notification_type_combo.currentIndex(), "none"))
            
            self.config_manager.set_config("notification.smtp.server", self.smtp_server_edit.text())
            self.config_manager.set_config("notification.smtp.port", self.smtp_port_spin.value())
            self.config_manager.set_config("notification.smtp.username", self.smtp_username_edit.text())
            self.config_manager.set_config("notification.smtp.password", self.smtp_password_edit.text())
            self.config_manager.set_config("notification.smtp.to_email", self.smtp_to_edit.text())
            
            # 保存快捷键配置
            self.config_manager.set_config("hotkey.screenshot", self.hotkey_edit.text())
            
            # 保存截图配置（修正映射以保持一致性）
            quality_map = {0: "high", 1: "medium", 2: "low"}
            self.config_manager.set_config("screenshot.quality", quality_map.get(self.screenshot_quality_combo.currentIndex(), "high"))
            
            format_map = {0: "PNG", 1: "JPEG", 2: "BMP"}
            self.config_manager.set_config("screenshot.format", format_map.get(self.screenshot_format_combo.currentIndex(), "PNG"))
            
            # 保存日志配置（修正映射以保持一致性）
            level_map = {0: "DEBUG", 1: "INFO", 2: "WARNING", 3: "ERROR", 4: "CRITICAL"}
            self.config_manager.set_config("logging.level", level_map.get(self.log_level_combo.currentIndex(), "INFO"))
            
            self.config_manager.save_config(emit_signal=False)  # 避免循环信号
        except Exception as e:
            logging.error(f"自动保存其他配置失败: {e}")
    
    def _save_config_data(self):
        """保存配置数据的通用方法"""
        # 保存OCR配置 - 使用文本映射保持与自动保存一致
        ocr_engine_text = self.ocr_engine_combo.currentText()
        engine_map = {"新野图床+云智OCR（免费）": "xinyew", "腾讯云OCR": "tencent", "视觉模型OCR": "vision_model"}
        self.config_manager.set_config("ocr.engine", engine_map.get(ocr_engine_text, "xinyew"))
        
        # 保存OCR语言配置 - 使用文本映射保持与自动保存一致
        ocr_language_text = self.ocr_language_combo.currentText()
        language_map = {"中文": "zh", "英文": "en", "中英文混合": "zh-en"}
        self.config_manager.set_config("ocr.language", language_map.get(ocr_language_text, "zh-en"))
        
        self.config_manager.set_config("ocr.tencent.secret_id", self.tencent_id_edit.text())
        self.config_manager.set_config("ocr.tencent.secret_key", self.tencent_key_edit.text())
        
        # 保存视觉模型配置
        self.config_manager.set_config("ocr.vision_model.name", self.vision_model_name_edit.text())
        self.config_manager.set_config("ocr.vision_model.model_id", self.vision_model_id_edit.text())
        self.config_manager.set_config("ocr.vision_model.api_endpoint", self.vision_api_endpoint_edit.text())
        self.config_manager.set_config("ocr.vision_model.api_key", self.vision_api_key_edit.text())
        self.config_manager.set_config("ocr.vision_model.max_tokens", self.vision_max_tokens_spin.value())
        self.config_manager.set_config("ocr.vision_model.temperature", self.vision_temperature_spin.value())
        self.config_manager.set_config("ocr.vision_model.prompt", self.vision_prompt_edit.toPlainText())
        
        # 保存通知配置 - 使用文本映射保持与自动保存一致
        notification_text = self.notification_type_combo.currentText()
        type_map = {"不额外显示": "none", "小弹窗显示": "small_popup", "大弹窗显示": "large_popup", "SMTP发送": "smtp"}
        self.config_manager.set_config("notification.type", type_map.get(notification_text, "none"))
        
        self.config_manager.set_config("notification.smtp.server", self.smtp_server_edit.text())
        self.config_manager.set_config("notification.smtp.port", self.smtp_port_spin.value())
        self.config_manager.set_config("notification.smtp.username", self.smtp_username_edit.text())
        self.config_manager.set_config("notification.smtp.password", self.smtp_password_edit.text())
        self.config_manager.set_config("notification.smtp.to_email", self.smtp_to_edit.text())
        
        # 保存快捷键配置
        self.config_manager.set_config("hotkey.screenshot", self.hotkey_edit.text())
        
        # 更新截图按钮文本显示新的快捷键
        self.update_screenshot_button_text()
        
        # 保存截图配置 - 使用文本映射保持与自动保存一致
        quality_text = self.screenshot_quality_combo.currentText()
        quality_map = {"高质量": "high", "中等质量": "medium", "低质量": "low"}
        self.config_manager.set_config("screenshot.quality", quality_map.get(quality_text, "high"))
        
        # 截图格式直接使用文本值
        self.config_manager.set_config("screenshot.format", self.screenshot_format_combo.currentText())
        
        # 保存日志配置 - 直接使用文本值
        self.config_manager.set_config("logging.level", self.log_level_combo.currentText())
    
    def start_hotkey_capture(self):
        """开始捕获快捷键"""
        if self.is_capturing_hotkey:
            return
            
        # 先解绑当前的快捷键
        if hasattr(self.screenshot_manager, 'listener') and self.screenshot_manager.listener:
            self.screenshot_manager.listener.stop()
            self.screenshot_manager.listener = None
            
        self.is_capturing_hotkey = True
        self.captured_keys.clear()
        self.change_hotkey_btn.setText("按键...")
        self.change_hotkey_btn.setEnabled(False)
        self.hotkey_edit.setText("请按下快捷键组合...")
        
        # 设置焦点到主窗口以捕获按键
        self.setFocus()
        
    def keyPressEvent(self, event):
        """键盘按下事件 - 用于捕获快捷键"""
        if self.is_capturing_hotkey:
            # 获取按键名称
            key_name = self._get_key_name(event.key())
            if key_name:
                self.captured_keys.add(key_name)
                
                # 检查修饰键
                modifiers = []
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    modifiers.append("ctrl")
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    modifiers.append("alt")
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    modifiers.append("shift")
                if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
                    modifiers.append("cmd")
                
                # 组合快捷键字符串
                all_keys = modifiers + [key_name]
                hotkey_str = "+".join(all_keys)
                
                # 显示当前按键组合
                self.hotkey_edit.setText(hotkey_str)
                
                # 如果是有效的快捷键组合（至少包含一个修饰键），则完成捕获
                if modifiers and key_name not in ["ctrl", "alt", "shift", "cmd"]:
                    QTimer.singleShot(500, lambda: self._finish_hotkey_capture(hotkey_str))
                    
            event.accept()
            return
            
        super().keyPressEvent(event)
        
    def _get_key_name(self, key_code):
        """获取按键名称"""
        key_map = {
            Qt.Key.Key_A: "a", Qt.Key.Key_B: "b", Qt.Key.Key_C: "c", Qt.Key.Key_D: "d",
            Qt.Key.Key_E: "e", Qt.Key.Key_F: "f", Qt.Key.Key_G: "g", Qt.Key.Key_H: "h",
            Qt.Key.Key_I: "i", Qt.Key.Key_J: "j", Qt.Key.Key_K: "k", Qt.Key.Key_L: "l",
            Qt.Key.Key_M: "m", Qt.Key.Key_N: "n", Qt.Key.Key_O: "o", Qt.Key.Key_P: "p",
            Qt.Key.Key_Q: "q", Qt.Key.Key_R: "r", Qt.Key.Key_S: "s", Qt.Key.Key_T: "t",
            Qt.Key.Key_U: "u", Qt.Key.Key_V: "v", Qt.Key.Key_W: "w", Qt.Key.Key_X: "x",
            Qt.Key.Key_Y: "y", Qt.Key.Key_Z: "z",
            Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2", Qt.Key.Key_3: "3",
            Qt.Key.Key_4: "4", Qt.Key.Key_5: "5", Qt.Key.Key_6: "6", Qt.Key.Key_7: "7",
            Qt.Key.Key_8: "8", Qt.Key.Key_9: "9",
            Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3", Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6", Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9", Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
            Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Escape: "esc", Qt.Key.Key_Tab: "tab", Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete", Qt.Key.Key_Insert: "insert", Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end", Qt.Key.Key_PageUp: "pageup", Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right"
        }
        return key_map.get(key_code)
        
    def _finish_hotkey_capture(self, hotkey_str):
        """完成快捷键捕获"""
        self.is_capturing_hotkey = False
        self.change_hotkey_btn.setText("更改")
        self.change_hotkey_btn.setEnabled(True)
        
        # 保存快捷键
        self.config_manager.set_config("hotkey.screenshot", hotkey_str)
        
        # 重新设置快捷键
        self.setup_hotkey()
        
        # 更新主页按钮的快捷键显示文本
        self.update_screenshot_button_text()
        
        CustomMessageBox.information(self, "成功", f"快捷键已设置为: {hotkey_str}")
    
    def on_ocr_engine_changed(self, text):
        """OCR引擎选择变化时自动保存"""
        try:
            engine_map = {"新野图床+云智OCR（免费）": "xinyew", "腾讯云OCR": "tencent", "视觉模型OCR": "vision_model"}
            self.config_manager.set_config("ocr.engine", engine_map.get(text, "xinyew"))
            self.config_manager.save_config()
            logging.info(f"OCR引擎已自动保存为: {text}")
        except Exception as e:
            logging.error(f"保存OCR引擎配置失败: {e}")
    
    def on_ocr_language_changed(self, text):
        """OCR识别语言变化时自动保存"""
        try:
            language_map = {"中文": "zh", "英文": "en", "中英文混合": "zh-en"}
            self.config_manager.set_config("ocr.language", language_map.get(text, "zh-en"))
            self.config_manager.save_config()
            logging.info(f"OCR识别语言已自动保存为: {text}")
        except Exception as e:
            logging.error(f"保存OCR语言配置失败: {e}")
    
    def on_notification_type_changed(self, text):
        """通知方式变化时自动保存"""
        try:
            type_map = {"不额外显示": "none", "小弹窗显示": "small_popup", "大弹窗显示": "large_popup", "SMTP发送": "smtp"}
            self.config_manager.set_config("notification.type", type_map.get(text, "none"))
            self.config_manager.save_config(emit_signal=False)  # 避免循环信号
            logging.info(f"通知方式已自动保存为: {text}")
        except Exception as e:
            logging.error(f"保存通知方式配置失败: {e}")
    
    def on_screenshot_quality_changed(self, text):
        """截图质量变化时自动保存"""
        try:
            quality_map = {"高质量": "high", "中等质量": "medium", "低质量": "low"}
            self.config_manager.set_config("screenshot.quality", quality_map.get(text, "high"))
            self.config_manager.save_config()
            logging.info(f"截图质量已自动保存为: {text}")
        except Exception as e:
            logging.error(f"保存截图质量配置失败: {e}")
    
    def on_screenshot_format_changed(self, text):
        """截图格式变化时自动保存"""
        try:
            self.config_manager.set_config("screenshot.format", text)
            self.config_manager.save_config()
            logging.info(f"截图格式已自动保存为: {text}")
        except Exception as e:
            logging.error(f"保存截图格式配置失败: {e}")
    
    def on_log_level_changed(self, text):
        """日志等级变化时自动保存"""
        try:
            self.config_manager.set_config("logging.level", text)
            self.config_manager.save_config()
            logging.info(f"日志等级已自动保存为: {text}")
        except Exception as e:
            logging.error(f"保存日志等级配置失败: {e}")