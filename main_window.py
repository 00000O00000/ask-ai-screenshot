#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析主窗口界面
只包含主页、配置文件选择、关于页
"""

import os
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QLineEdit, QGroupBox, 
    QFileDialog, QComboBox, QFormLayout
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

from custom_window import CustomMessageBox, MarkdownViewer, NotificationWindow
from util import TaskManager
from core import EmailManager


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
    
    def __init__(self, config_manager, screenshot_manager, ocr_manager, ai_client_manager):
        super().__init__()
        self.config_manager = config_manager
        self.screenshot_manager = screenshot_manager
        self.ocr_manager = ocr_manager
        self.ai_client_manager = ai_client_manager
        self.task_manager = TaskManager()
        
        # 初始化邮件管理器和通知窗口
        self.email_manager = EmailManager(config_manager)
        self.notification_window = NotificationWindow()
        
        self.current_image = None
        self.worker_thread = None
        
        self.init_ui()
        self.connect_signals()
        self.setup_hotkey()
        self.load_config_to_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("AI截图分析")
        self.setGeometry(100, 100, 800, 500)
        
        # 设置窗口图标
        try:
            from icon_data import get_icon_data
            icon_data = get_icon_data()
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except ImportError:
            if os.path.exists('favicon.ico'):
                self.setWindowIcon(QIcon('favicon.ico'))
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fffe;
                font-size: 16px;
            }
            QTabWidget::pane {
                border: 1px solid #c0c4cc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e8f5e8;
                padding: 10px 18px;
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
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 16px;
                min-height: 20px;
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
            QLineEdit {
                font-size: 16px;
                padding: 8px 12px;
                min-height: 20px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QLineEdit:focus {
                outline: none;
                border: 2px solid #a8d8a8;
            }
            QLabel {
                font-size: 16px;
                padding: 4px;
            }
            QTextEdit {
                font-size: 16px;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTextEdit:focus {
                outline: none;
                border: 2px solid #a8d8a8;
            }
            QSpinBox, QDoubleSpinBox {
                font-size: 16px;
                padding: 8px 12px;
                min-height: 20px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                outline: none;
                border: 2px solid #a8d8a8;
            }
            QCheckBox {
                font-size: 16px;
                padding: 4px;
            }
            QComboBox {
                font-size: 17px;
                padding: 8px 8px;
                min-height: 14px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:focus {
                outline: none;
                border: 2px solid #a8d8a8;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                font-size: 18px;
                background-color: white;
                border: 1px solid #ddd;
                selection-background-color: #a8d8a8;
                selection-color: white;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                height: 25px;
                padding: 8px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e8f5e8;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #a8d8a8;
                color: white;
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
        
        # 添加页面
        self.create_home_page()
        self.create_config_page()
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
        
        # 提示词选择
        prompt_group = QGroupBox("提示词选择")
        prompt_layout = QVBoxLayout(prompt_group)
        
        self.prompt_combo = QComboBox()
        self.prompt_combo.setToolTip("选择要使用的提示词")
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
        
        # 输出文本区
        self.output_text = MarkdownViewer()
        self.output_text.setPlaceholderText("AI分析结果将在这里显示...")
        output_layout.addWidget(self.output_text)
        
        layout.addWidget(output_panel)
    

    
    def create_config_page(self):
        """创建配置文件选择页面"""
        config_widget = QWidget()
        self.tab_widget.addTab(config_widget, "配置文件")
        
        layout = QVBoxLayout(config_widget)
        
        # 当前配置文件信息
        current_group = QGroupBox("当前配置文件")
        current_layout = QFormLayout(current_group)
        
        self.current_config_path = QLineEdit()
        self.current_config_path.setReadOnly(True)
        self.current_config_path.setText(self.config_manager.config_file_path)
        
        self.config_status_label = QLabel("配置有效")
        self.config_status_label.setStyleSheet("color: green; font-weight: bold;")
        
        current_layout.addRow("配置文件路径:", self.current_config_path)
        current_layout.addRow("配置状态:", self.config_status_label)
        
        layout.addWidget(current_group)
        
        # 配置文件操作
        file_group = QGroupBox("配置文件操作")
        file_layout = QVBoxLayout(file_group)
        
        # 选择配置文件
        select_layout = QHBoxLayout()
        self.select_config_btn = QPushButton("选择配置文件")
        self.select_config_btn.clicked.connect(self.select_config_file)
        self.validate_config_btn = QPushButton("验证配置")
        self.validate_config_btn.clicked.connect(self.validate_config)
        select_layout.addWidget(self.select_config_btn)
        select_layout.addWidget(self.validate_config_btn)
        file_layout.addLayout(select_layout)
        
        # 其他操作
        other_layout = QHBoxLayout()
        self.export_config_btn = QPushButton("导出配置")
        self.export_config_btn.clicked.connect(self.export_config)
        
        self.reset_config_btn = QPushButton("重置为默认")
        self.reset_config_btn.clicked.connect(self.reset_config)
        
        other_layout.addWidget(self.export_config_btn)
        other_layout.addWidget(self.reset_config_btn)
        file_layout.addLayout(other_layout)
        
        layout.addWidget(file_group)
        
        # 配置文件内容预览
        preview_group = QGroupBox("配置文件内容预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setMaximumHeight(200)
        self.config_preview.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace;")
        
        preview_layout.addWidget(self.config_preview)
        layout.addWidget(preview_group)
        
        layout.addStretch()
        
        # 加载当前配置预览
        self.load_config_preview()
    
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
        <h2 style="color: #a8d8a8;">AI截图分析 v2.0</h2>
        <p>一个方便的AI截图分析工具，快速使用AI解释你在屏幕上看到的东西，或让他帮你解题。</p>
        <p><strong>移除可能导致问题的前端配置部分，请自行编辑config.toml文件以自定义配置</strong></p>
        <p><strong>新增：内置原创 Qwen API 逆向，允许开箱即用</strong></p>
        <p>软件目前处于测试版，可能存在Bug，若有问题，欢迎前往 Github 提交 issue。</p>
        <p>本软件完全使用 Trae + Claude 4 编写，然后由我和 Claude 4 共同进行用户体验优化。</p>
        <h2>功能特点</h2>
        <ul>
        <li><strong>核心功能</strong>：截图后，将图片OCR为文字或直接提交给AI，并自动显示AI回复结果</li>
        <li><strong>可扩展性</strong>：使用提示词自定义功能，例如 一键截图做题、解释、翻译 等功能</li>
        <li><strong>开箱即用</strong>：内置原创 Qwen API 逆向，开箱即用</li>
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
        # 截图管理器信号
        self.screenshot_manager.screenshot_taken.connect(self.on_screenshot_taken)
        self.screenshot_manager.screenshot_failed.connect(self.on_screenshot_failed)
        self.screenshot_manager.screenshot_cancelled.connect(self.on_screenshot_cancelled)
        
        # OCR管理器信号
        self.ocr_manager.ocr_completed.connect(self.on_ocr_completed)
        self.ocr_manager.ocr_failed.connect(self.on_ocr_failed)
        
        # AI客户端管理器信号
        self.ai_client_manager.response_completed.connect(self.on_ai_response_completed)
        self.ai_client_manager.request_failed.connect(self.on_ai_request_failed)
        self.ai_client_manager.streaming_response.connect(self.on_ai_streaming_response)
        self.ai_client_manager.reasoning_content.connect(self.on_ai_reasoning_content)
        
        # 任务管理器信号
        self.task_manager.task_started.connect(self.on_task_started)
        self.task_manager.task_finished.connect(self.on_task_finished)
        
        # 配置管理器信号
        self.config_manager.config_changed.connect(self.load_config_to_ui)
    
    def setup_hotkey(self):
        """设置快捷键"""
        self.screenshot_manager.setup_hotkey()
    
    def load_config_to_ui(self):
        """加载配置到界面"""
        # 更新配置文件路径显示
        if hasattr(self, 'current_config_path'):
            self.current_config_path.setText(self.config_manager.config_file_path)
        
        # 验证配置并更新状态
        self.validate_config()
        
        # 更新配置预览
        self.load_config_preview()
        
        # 加载提示词到下拉框
        self.load_prompts_to_combo()

    def load_prompts_to_combo(self):
        """加载提示词到下拉框"""
        try:
            # 清空现有选项
            self.prompt_combo.clear()
            
            # 获取提示词配置
            prompts = self.config_manager.get_config("prompts")
            if prompts and isinstance(prompts, list):
                for prompt in prompts:
                    if isinstance(prompt, dict) and "name" in prompt:
                        self.prompt_combo.addItem(prompt["name"])
                
                # 默认选择第一个
                if self.prompt_combo.count() > 0:
                    self.prompt_combo.setCurrentIndex(0)
            else:
                # 如果没有配置或格式错误，添加默认选项
                self.prompt_combo.addItem("默认提示词")
                
        except Exception as e:
            logging.error(f"加载提示词失败: {e}")
            self.prompt_combo.clear()
            self.prompt_combo.addItem("默认提示词")
    
    def get_selected_prompt_content(self):
        """获取当前选中的提示词内容"""
        try:
            selected_name = self.prompt_combo.currentText()
            prompts = self.config_manager.get_config("prompts")
            
            if prompts and isinstance(prompts, list):
                for prompt in prompts:
                    if isinstance(prompt, dict) and prompt.get("name") == selected_name:
                        return prompt.get("content", "")
            
            # 如果没找到，返回默认内容
            return "请分析这张图片或OCR识别的文字内容，并提供详细的解释和分析。"
            
        except Exception as e:
            logging.error(f"获取提示词内容失败: {e}")
            return "请分析这张图片或OCR识别的文字内容，并提供详细的解释和分析。"
    
    def select_config_file(self):
        """选择配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "TOML files (*.toml);;All files (*.*)"
        )
        if file_path:
            if self.config_manager.load_config_from_file(file_path):
                self.current_config_path.setText(file_path)
                self.validate_config()
                self.load_config_preview()
                CustomMessageBox(self, "成功", "配置文件加载成功！", "success").exec()
            else:
                CustomMessageBox(self, "错误", "配置文件加载失败！请检查文件格式。", "error").exec()
    
    def validate_config(self):
        """验证配置"""
        try:
            # 检查必要的配置项
            ai_config = self.config_manager.get_config("ai_model")
            prompts_config = self.config_manager.get_config("prompts")
            
            if not ai_config:
                self.config_status_label.setText("配置无效：缺少AI模型配置")
                self.config_status_label.setStyleSheet("color: red; font-weight: bold;")
                return False
            
            if not prompts_config or not isinstance(prompts_config, list) or len(prompts_config) == 0:
                self.config_status_label.setText("配置无效：缺少提示词配置")
                self.config_status_label.setStyleSheet("color: red; font-weight: bold;")
                return False
            
            # 检查关键字段
            required_ai_fields = ['model_id', 'api_endpoint', 'api_key']
            for field in required_ai_fields:
                if not ai_config.get(field):
                    self.config_status_label.setText(f"配置无效：AI模型缺少{field}")
                    self.config_status_label.setStyleSheet("color: red; font-weight: bold;")
                    return False
            
            # 检查提示词配置格式
            for i, prompt in enumerate(prompts_config):
                if not isinstance(prompt, dict) or not prompt.get('name') or not prompt.get('content'):
                    self.config_status_label.setText(f"配置无效：第{i+1}个提示词格式错误")
                    self.config_status_label.setStyleSheet("color: red; font-weight: bold;")
                    return False
            
            self.config_status_label.setText("配置有效")
            self.config_status_label.setStyleSheet("color: green; font-weight: bold;")
            return True
            
        except Exception as e:
            self.config_status_label.setText(f"配置验证失败：{str(e)}")
            self.config_status_label.setStyleSheet("color: red; font-weight: bold;")
            return False
    
    def load_config_preview(self):
        """加载配置文件内容预览"""
        try:
            import os
            if os.path.exists(self.config_manager.config_file_path):
                with open(self.config_manager.config_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.config_preview.setPlainText(content)
            else:
                self.config_preview.setPlainText("配置文件不存在")
        except Exception as e:
            self.config_preview.setPlainText(f"读取配置文件失败：{str(e)}")
    
    def export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置文件", "config.toml", "TOML files (*.toml)"
        )
        if file_path:
            if self.config_manager.export_config(file_path):
                CustomMessageBox(self, "成功", "配置导出成功！", "success").exec()
            else:
                CustomMessageBox(self, "错误", "配置导出失败！", "error").exec()
    
    def import_config(self):
        """导入配置文件（复制到当前配置目录）"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", "", "TOML files (*.toml);;All files (*.*)"
        )
        if file_path:
            try:
                import shutil
                import os
                # 复制文件到当前配置目录
                config_dir = os.path.dirname(self.config_manager.config_file_path)
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                
                target_path = self.config_manager.config_file_path
                shutil.copy2(file_path, target_path)
                
                # 重新加载配置
                if self.config_manager.load_config():
                    self.load_config_to_ui()
                    CustomMessageBox(self, "成功", "配置文件导入成功！", "success").exec()
                else:
                    CustomMessageBox(self, "错误", "配置文件格式错误！", "error").exec()
            except Exception as e:
                CustomMessageBox(self, "错误", f"配置导入失败：{str(e)}", "error").exec()
    
    def reset_config(self):
        """重置配置"""
        reply = CustomMessageBox(
            self, "确认", "确定要重置为默认配置吗？这将恢复默认设置。", "question", ["确定", "取消"]
        ).exec()
        
        if reply == "确定":
            if self.config_manager.reset_config():
                self.load_config_to_ui()
                CustomMessageBox(self, "成功", "配置重置成功！", "success").exec()
            else:
                CustomMessageBox(self, "错误", "配置重置失败！", "error").exec()
    
    def start_screenshot(self):
        """开始截图"""
        if self.task_manager.start_task("截图"):
            self.screenshot_manager.start_screenshot()
    
    def import_from_clipboard(self):
        """从剪贴板导入图片"""
        if self.task_manager.start_task("剪贴板导入"):
            try:
                image = self.screenshot_manager.screenshot_from_clipboard()
                if image:
                    self.on_screenshot_taken(image)
                else:
                    self.update_status("剪贴板中没有图片")
                    self.task_manager.finish_task()
            except Exception as e:
                self.on_screenshot_failed(str(e))
    
    def stop_task(self):
        """停止任务"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.terminate()
            self.worker_thread.wait()
        
        if hasattr(self.ai_client_manager, 'stop_request'):
            self.ai_client_manager.stop_request()
        
        self.task_manager.finish_task()
        self.update_status("任务已停止")
    
    def on_screenshot_taken(self, image):
        """截图完成处理"""
        self.current_image = image
        
        # 获取OCR配置
        ocr_config = self.config_manager.get_config("ocr")
        ocr_type = ocr_config.get("type", "ocr_then_text") if ocr_config else "ocr_then_text"
        
        if ocr_type == "direct_image":
            # 直接提交图片给AI
            self.update_status("截图完成，正在请求AI分析...")
            self._send_ai_request_with_image()
        else:
            # OCR后提交文字
            self.update_status("截图完成，开始OCR识别...")
            # 启动OCR工作线程
            self.worker_thread = WorkerThread(self.ocr_manager.recognize_image, image)
            self.worker_thread.task_completed.connect(self.on_ocr_completed)
            self.worker_thread.task_failed.connect(self.on_ocr_failed)
            self.worker_thread.start()
    
    def on_screenshot_failed(self, error_msg):
        """截图失败处理"""
        self.update_status(f"截图失败: {error_msg}")
        self.task_manager.finish_task()
    
    def on_screenshot_cancelled(self):
        """截图取消处理"""
        self.update_status("截图已取消")
        self.task_manager.finish_task()
    
    def _send_ai_request_with_image(self):
        """直接发送图片给AI分析"""
        # 获取配置
        ai_config = self.config_manager.get_config("ai_model")
        
        if not ai_config:
            self.on_ai_request_failed("配置不完整，请检查AI模型配置")
            return
        
        # 获取选中的提示词内容
        prompt_content = self.get_selected_prompt_content()
        
        if ai_config.get("vision_support", False):
            # 支持视觉的模型直接发送图片
            self.ai_client_manager.send_request("default", prompt_content, self.current_image)
        else:
            self.on_ai_request_failed("当前AI模型不支持图像输入，请选择支持视觉的模型或使用OCR模式")
    

    
    def on_ocr_completed(self, ocr_text):
        """OCR完成处理"""
        self.update_status("OCR完成，正在请求AI分析...")
        
        # 获取配置
        ai_config = self.config_manager.get_config("ai_model")
        
        if not ai_config:
            self.on_ai_request_failed("配置不完整，请检查AI模型配置")
            return
        
        # 获取选中的提示词内容
        prompt_content = self.get_selected_prompt_content()
        
        # 发送AI请求（OCR后提交文字模式）
        full_prompt = f"{prompt_content}\n\n以下是OCR识别的文字内容：\n{ocr_text}"
        self.ai_client_manager.send_request("default", full_prompt)
    
    def on_ocr_failed(self, error_msg):
        """OCR失败处理"""
        self.update_status(f"OCR失败: {error_msg}")
        self.task_manager.finish_task()
    
    def on_ai_response_completed(self, response):
        """AI响应完成处理"""
        self.output_text.set_markdown(response)
        self.update_status("AI分析完成")
        
        # 显示通知
        self.show_notification("AI分析完成", response)
        
        # 如果有大窗口正在显示，完成最终渲染
        if hasattr(self, 'large_window') and self.large_window:
            # 流式请求完成后进行一次完整的markdown渲染
            if hasattr(self.large_window, 'current_response_content'):
                self.large_window._batch_update_display(force_markdown=True)
        
        self.task_manager.finish_task()
    
    def on_ai_reasoning_content(self, reasoning_content):
        """AI推理内容处理"""
        # 如果没有大窗口，创建一个
        if not hasattr(self, 'large_window') or not self.large_window:
            self.large_window = self.show_large_window("AI正在分析...")
        
        # 添加推理内容到大窗口
        if self.large_window and hasattr(self.large_window, 'append_reasoning_content'):
            self.large_window.append_reasoning_content(reasoning_content)
    
    def on_ai_streaming_response(self, content_type, content):
        """AI流式响应处理"""
        if content_type == "content":
            # 更新主窗口输出
            self.output_text.append_text(content)
            
            # 如果没有大窗口，创建一个
            if not hasattr(self, 'large_window') or not self.large_window:
                self.large_window = self.show_large_window("AI正在分析...")
            
            # 添加响应内容到大窗口
            if self.large_window and hasattr(self.large_window, 'append_response_content'):
                self.large_window.append_response_content(content)
    
    def on_ai_request_failed(self, error_msg):
        """AI请求失败处理"""
        self.output_text.set_markdown(f"**错误**: {error_msg}")
        self.update_status(f"AI请求失败: {error_msg}")
        self.task_manager.finish_task()
    

    
    def on_task_started(self):
        """任务开始处理"""
        self.screenshot_btn.setEnabled(False)
        self.clipboard_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 清空输出区域，准备显示新的AI分析结果
        self.output_text.set_markdown("")
        
        # 关闭之前的大窗口（如果存在）
        if hasattr(self, 'large_window') and self.large_window:
            self.large_window.close()
            self.large_window = None
    
    def on_task_finished(self):
        """任务完成处理"""
        self.screenshot_btn.setEnabled(True)
        self.clipboard_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.setText(message)
        logging.info(message)
    
    def show_notification(self, title: str, content: str):
        """显示通知 - 小窗口只显示AI回复内容"""
        notification_type = self.config_manager.get_config("notification.type") or "small_popup"
        
        if notification_type == "none":
            # 不显示通知
            return
        elif notification_type == "small_popup":
            # 显示小型弹窗通知 - 只显示AI回复内容，不显示推理内容
            self.notification_window.show_small_notification(content)
        elif notification_type == "large_popup":
            # 显示大型弹窗通知
            self.notification_window.show_large_notification(content)
        elif notification_type == "smtp":
            # 发送邮件通知
            self.send_email_notification(title, content)
        else:
            # 默认使用小型弹窗
            self.notification_window.show_small_notification(content)
    
    def show_large_window(self, initial_message: str):
        """显示大窗口（统一用于推理内容和流式响应）"""
        try:
            from custom_window import NotificationWindow
            # 关闭之前的大窗口
            if hasattr(self, 'large_window') and self.large_window:
                self.large_window.close()
            
            # 创建新的大窗口
            self.large_window = NotificationWindow.show_large_notification_streaming(initial_message, self)
            if self.large_window:
                self.large_window.setWindowTitle("AI分析结果")
            return self.large_window
        except Exception as e:
            logging.error(f"显示大窗口失败: {e}")
            return None
    
    def send_email_notification(self, title: str, content: str):
        """发送邮件通知"""
        try:
            # 连接邮件管理器信号
            self.email_manager.email_sent.connect(self.on_email_sent)
            self.email_manager.email_failed.connect(self.on_email_failed)
            
            # 发送邮件
            self.email_manager.send_email(title, content)
        except Exception as e:
            logging.error(f"邮件通知失败: {e}")
            # 邮件失败时回退到小型通知
            self.notification_window.show_small_notification(f"邮件发送失败: {e}")
    
    def on_email_sent(self):
        """邮件发送成功"""
        self.notification_window.show_small_notification("邮件通知已发送")
        logging.info("邮件通知发送成功")
    
    def on_email_failed(self, error_msg: str):
        """邮件发送失败"""
        self.notification_window.show_small_notification(f"邮件发送失败: {error_msg}")
        logging.error(f"邮件通知发送失败: {error_msg}")