#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析 - 工具模块
包含配置管理、日志管理、错误处理等功能
"""

import json
import os
import logging
import time
import uuid
import glob
from datetime import datetime
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal


class ConfigManager(QObject):
    """配置文件管理器"""
    
    config_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.config_file = "config.json"
        self.config = self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        default_model_id1 = f"model_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        default_model_id2 = f"model_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        default_model_id3 = f"model_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        default_prompt_id1 = f"prompt_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        default_prompt_id2 = f"prompt_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        default_prompt_id3 = f"prompt_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        default_prompt_id4 = f"prompt_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        return {
            "ai_models": {
                default_model_id1: {
                    "id": default_model_id1,
                    "name": "[硅基]Deepseek-V3",
                    "model_id": "deepseek-ai/DeepSeek-V3",
                    "api_endpoint": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "max_tokens": 0,
                    "temperature": 0.3,
                    "vision_support": False
                },
                default_model_id2: {
                    "id": default_model_id2,
                    "name": "[硅基]Qwen3-235B-Thinking",
                    "model_id": "Qwen/Qwen3-235B-A22B-Thinking-2507",
                    "api_endpoint": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "max_tokens": 0,
                    "temperature": 0.3,
                    "vision_support": False
                },
                default_model_id3: {
                    "id": default_model_id3,
                    "name": "[硅基]QvQ-72B-Preview",
                    "model_id": "Qwen/QVQ-72B-Preview",
                    "api_endpoint": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "max_tokens": 0,
                    "temperature": 0.3,
                    "vision_support": True
                },
            },
            "prompts": {
                default_prompt_id1: {
                    "id": default_prompt_id1,
                    "name": "[非多模态]OCR并解释内容",
                    "content": "请简要解释给出的文字内容。给出的内容由OCR获得，若不影响判断，则请忽略可能存在错误的换行符、空格与错别字。回复的内容请勿包含任何markdown标记，以简洁明了为主，不要长篇大论。",
                    "model_id": default_model_id1
                },
                default_prompt_id2: {
                    "id": default_prompt_id2,
                    "name": "[非多模态]OCR并解答题目",
                    "content": "请解答给出的题目。给出的题目内容由OCR获得，若不影响判断，则请忽略可能存在错误的换行符、空格与错别字。回复的内容请勿包含任何markdown标记，把答案放在最前面，且简短讲解即可。",
                    "model_id": default_model_id2
                },
                default_prompt_id3: {
                    "id": default_prompt_id3,
                    "name": "[多模态]AI直接提取文字",
                    "content": "请识别图片中的文字内容，并格式化后给我。",
                    "model_id": default_model_id3
                },
                default_prompt_id4: {
                    "id": default_prompt_id4,
                    "name": "[多模态]AI直接解答题目",
                    "content": "请解答给出的截图中的题目。回复的内容请勿包含任何markdown标记，把答案放在最前面，且简短讲解即可。",
                    "model_id": default_model_id3
                },
            },
            "ocr": {
                "type": "xinyew",
                "tencent": {
                    "secret_id": "",
                    "secret_key": "",
                    "region": "ap-beijing",
                    "language": "zh"
                },
                "vision_model": {
                    "name": "[硅基]QvQ-72B-Preview",
                    "model_id": "Qwen/QVQ-72B-Preview",
                    "api_endpoint": "https://api.siliconflow.cn/v1",
                    "api_key": "",
                    "max_tokens": 0,
                    "temperature": 0.3
                }
            },
            "notification": {
                "type": "none",  # none, small_popup, large_popup, smtp
                "smtp": {
                    "server": "smtp.qq.com",
                    "port": 587,
                    "username": "",
                    "password": "",
                    "to_email": ""
                }
            },
            "hotkey": {
                "screenshot": "alt+shift+d"
            },
            "screenshot": {
                "mode": "advanced",  # 'simple' 或 'advanced'
                "quality": "high",   # 截图质量
                "format": "PNG"      # 截图格式
            },
            "logging": {
                "level": "INFO"
            }
        }
    
    def load_config(self, emit_signal: bool = True) -> bool:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_file):
                # 配置文件不存在时，使用默认配置并保存
                self.config = self._get_default_config()
                self.save_config(emit_signal=False)  # 初始化时不发射信号
                return True
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                
            # 直接使用加载的配置，不再合并默认配置
            self.config = loaded_config
            if emit_signal:
                self.config_changed.emit()
            return True
            
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return False
    
    def save_config(self, emit_signal: bool = True) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            if emit_signal:
                self.config_changed.emit()
            return True
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            return False
    
    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """合并配置，确保所有必要的键都存在"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get_config(self, path: str = None) -> Any:
        """获取配置值"""
        if path is None:
            return self.config
            
        keys = path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def set_config(self, path: str, value: Any) -> bool:
        """设置配置值，如果value为None则删除对应的键"""
        try:
            keys = path.split('.')
            config = self.config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 如果值为None，删除对应的键
            if value is None:
                if keys[-1] in config:
                    del config[keys[-1]]
            else:
                config[keys[-1]] = value
            return True
        except Exception as e:
            logging.error(f"设置配置失败: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """导出配置文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """导入配置文件（直接覆盖原有配置）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            # 直接覆盖原有配置，不进行合并
            self.config = imported_config
            self.save_config()
            return True
        except Exception as e:
            logging.error(f"导入配置失败: {e}")
            return False
    
    def get_default_model_id(self) -> str:
        """获取默认模型ID（第一个可用的模型）"""
        models = self.get_config("ai_models")
        if models:
            return list(models.keys())[0]
        return None
    
    def get_default_prompt_id(self) -> str:
        """获取默认提示词ID（第一个可用的提示词）"""
        prompts = self.get_config("prompts")
        if prompts:
            return list(prompts.keys())[0]
        return None
    
    def reset_config(self) -> bool:
        """重置配置为默认值"""
        try:
            self.config = self._get_default_config()
            self.save_config()
            return True
        except Exception as e:
            logging.error(f"重置配置失败: {e}")
            return False
    
    def delete_config(self) -> bool:
        """删除配置文件"""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            return True
        except Exception as e:
            logging.error(f"删除配置文件失败: {e}")
            return False


class LogManager:
    """日志管理器"""
    
    def __init__(self):
        self.log_dir = "logs"
        self.max_log_files = 3
        
    def setup_logging(self, level: str = "INFO"):
        """设置日志"""
        try:
            # 创建日志目录
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
            
            # 清理旧日志文件
            self._cleanup_old_logs()
            
            # 设置日志文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, f"app_{timestamp}.log")
            
            # 配置日志
            log_level = getattr(logging, level.upper(), logging.INFO)
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            
            logging.info(f"日志系统初始化完成，日志文件: {log_file}")
            
        except Exception as e:
            print(f"日志系统初始化失败: {e}")
    
    def _cleanup_old_logs(self):
        """清理旧的日志文件"""
        try:
            log_files = glob.glob(os.path.join(self.log_dir, "app_*.log"))
            log_files.sort(key=os.path.getmtime, reverse=True)
            
            # 删除超过最大数量的日志文件
            for log_file in log_files[self.max_log_files:]:
                os.remove(log_file)
                
        except Exception as e:
            print(f"清理日志文件失败: {e}")


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.error_count = 0
        
    def handle_error(self, error: Exception, context: str = "", show_dialog: bool = True):
        """处理错误"""
        self.error_count += 1
        error_msg = f"{context}: {str(error)}" if context else str(error)
        
        # 记录错误日志
        logging.error(error_msg, exc_info=True)
        
        # 显示错误对话框
        if show_dialog:
            self.show_error_dialog(error_msg)
    
    def show_error_dialog(self, message: str):
        """显示错误对话框"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("错误")
            msg_box.setText("程序运行出现错误")
            msg_box.setDetailedText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception as e:
            logging.error(f"显示错误对话框失败: {e}")


class TaskManager(QObject):
    """任务管理器，确保同一时间只有一个任务运行"""
    
    task_started = pyqtSignal()
    task_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._current_task = None
    
    def is_running(self) -> bool:
        """检查是否有任务正在运行"""
        return self._is_running
    
    def start_task(self, task_name: str) -> bool:
        """开始任务"""
        if self._is_running:
            return False
        
        self._is_running = True
        self._current_task = task_name
        self.task_started.emit()
        logging.info(f"任务开始: {task_name}")
        return True
    
    def finish_task(self):
        """结束任务"""
        if self._is_running:
            logging.info(f"任务结束: {self._current_task}")
            self._is_running = False
            self._current_task = None
            self.task_finished.emit()
    
    def get_current_task(self) -> Optional[str]:
        """获取当前任务名称"""
        return self._current_task