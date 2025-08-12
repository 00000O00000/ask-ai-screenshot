#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析 - 主程序入口
作者: AI Assistant
版本: 1.0.0
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow
from util import ConfigManager, LogManager, ErrorHandler
from core import ScreenshotManager, OCRManager, AIClientManager, EmailManager


class Application:
    """应用程序主类"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.config_manager = ConfigManager()
        self.log_manager = LogManager()
        self.error_handler = ErrorHandler()
        self.screenshot_manager = None
        self.ocr_manager = None
        self.ai_client_manager = None
        self.email_manager = None
        
    def initialize(self):
        """初始化应用程序"""
        try:
            # 初始化日志
            self.log_manager.setup_logging()
            logging.info("应用程序启动")
            
            # 加载配置（初始化时不发射信号）
            self.config_manager.load_config(emit_signal=False)
            
            # 初始化各个管理器
            self.screenshot_manager = ScreenshotManager(self.config_manager)
            self.ocr_manager = OCRManager(self.config_manager)
            self.ai_client_manager = AIClientManager(self.config_manager)
            self.email_manager = EmailManager(self.config_manager)
            
            # 创建Qt应用
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AI截图分析")
            self.app.setApplicationVersion("1.0.0")
            
            # 创建主窗口
            self.main_window = MainWindow(
                self.config_manager,
                self.screenshot_manager,
                self.ocr_manager,
                self.ai_client_manager,
                self.email_manager
            )
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(e, "应用程序初始化失败")
            return False
    
    def run(self):
        """运行应用程序"""
        if not self.initialize():
            return 1
            
        try:
            self.main_window.show()
            return self.app.exec()
        except Exception as e:
            self.error_handler.handle_error(e, "应用程序运行失败")
            return 1
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.screenshot_manager:
                self.screenshot_manager.cleanup()
            logging.info("应用程序退出")
        except Exception as e:
            self.error_handler.handle_error(e, "清理资源失败")


def main():
    """主函数"""
    app = Application()
    try:
        exit_code = app.run()
    finally:
        app.cleanup()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()