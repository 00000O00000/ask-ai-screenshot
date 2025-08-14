#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析主程序
作者: AI Assistant
版本: 1.0.0-simplified
"""

import sys
import logging
import threading
import time
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow
from util import ConfigManager, LogManager, ErrorHandler
from core import ScreenshotManager, OCRManager, AIClientManager
from ai import app as flask_app


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
        self.flask_thread = None
        self.flask_port = 58888
    
    def start_flask_server(self):
        """在后台线程中启动Flask服务"""
        try:
            logging.info(f"正在启动Flask服务于端口 {self.flask_port}...")
            flask_app.run(host='127.0.0.1', port=self.flask_port, debug=False, use_reloader=False)
        except Exception as e:
            logging.error(f"Flask服务启动失败: {e}")
    
    def initialize(self):
        """初始化应用程序"""
        try:
            # 初始化日志
            self.log_manager.setup_logging()
            logging.info("应用程序启动")
            
            # 加载配置
            self.config_manager.load_config()
            
            # 检查是否需要启动Flask服务
            # 同时检测分析AI和OCR AI的API端点是否指向内置AI服务
            ai_config = self.config_manager.get_config("ai_model")
            ocr_config = self.config_manager.get_config("ocr.vision_model")
            
            local_endpoint = f"http://127.0.0.1:{self.flask_port}"
            
            # 检查分析AI是否指向内置服务
            ai_uses_local = ai_config and ai_config.get("api_endpoint", "").startswith(local_endpoint)
            
            # 检查OCR AI是否指向内置服务
            ocr_uses_local = ocr_config and ocr_config.get("api_endpoint", "").startswith(local_endpoint)
            
            if ai_uses_local or ocr_uses_local:
                # 至少有一个配置指向内置服务，启动Flask服务
                services_using_local = []
                if ai_uses_local:
                    services_using_local.append("分析AI")
                if ocr_uses_local:
                    services_using_local.append("OCR AI")
                
                logging.info(f"检测到以下服务使用内置AI: {', '.join(services_using_local)}，启动Flask服务...")
                
                self.flask_thread = threading.Thread(target=self.start_flask_server, daemon=True)
                self.flask_thread.start()
                
                # 等待Flask服务启动
                time.sleep(2)
            else:
                logging.info("分析AI和OCR AI均未指向内置服务，跳过Flask服务启动")
            
            # 初始化各个管理器
            self.screenshot_manager = ScreenshotManager(self.config_manager)
            self.ocr_manager = OCRManager(self.config_manager)
            self.ai_client_manager = AIClientManager(self.config_manager)
            
            # 创建Qt应用
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AI截图分析")
            self.app.setApplicationVersion("1.0.0-simplified")
            
            # 创建主窗口
            self.main_window = MainWindow(
                self.config_manager,
                self.screenshot_manager,
                self.ocr_manager,
                self.ai_client_manager
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