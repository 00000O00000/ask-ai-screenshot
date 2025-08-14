#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析工具模块
包含配置管理、日志管理、错误处理等功能
"""

import os
import logging
import time
import glob
from datetime import datetime
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import tomllib
    import tomli_w
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False
    print("警告: tomllib/tomli_w 模块未安装，将使用默认配置")


class ConfigManager(QObject):
    """配置文件管理器"""
    
    config_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.config_file = "config.toml"
        self.config = self._get_hardcoded_config()
    
    @property
    def config_file_path(self) -> str:
        """获取配置文件路径"""
        return os.path.abspath(self.config_file)
        
    def _get_hardcoded_config(self) -> Dict[str, Any]:
        """获取硬编码配置（与_save_config_with_comments保持一致）"""
        return {
            # AI模型配置 - 定义使用的AI模型相关参数
            "ai_model": {
                "name": "内置Qwen3模型",  # 模型显示名称
                "model_id": "qwen3-235b-a22b",  # 模型标识符
                "api_endpoint": "http://127.0.0.1:58888/v1/chat/completions",  # API端点地址，支持本地Flask服务
                "api_key": "sk-example-key",  # API密钥
                "max_tokens": 0,  # 最大令牌数，0表示使用模型默认值
                "temperature": 0.3,  # 生成温度，控制回答的随机性(0-2)
                "vision_support": False,  # 是否支持图像输入
                "enable_streaming": True  # 是否启用流式响应
            },
            # 提示词配置 - 预定义的AI交互提示词模板
            "prompts": [
                {
                    "name": "OCR并解释内容",  # 提示词名称
                    "content": "请简要解释给出的文字内容。给出的内容由OCR获得，若不影响判断，则请忽略可能存在错误的换行符、空格与错别字。回复的内容请勿包含任何markdown标记，以简洁明了为主，不要长篇大论。"  # 提示词内容
                },
                {
                    "name": "OCR并解答题目",
                    "content": "请解答给出的题目。给出的题目内容由OCR获得，若不影响判断，则请忽略可能存在错误的换行符、空格与错别字。回复的内容请勿包含任何markdown标记，把答案放在最前面，且简短讲解即可。"
                },
                {
                    "name": "OCR并翻译文本",
                    "content": "请中英互译给出的文本。给出的题目内容由OCR获得，若不影响判断，则请忽略可能存在错误的换行符、空格与错别字。请按原格式输出。"
                },
                {
                    "name": "AI直接提取文字",
                    "content": "请识别图片中的文字内容，并格式化后给我。"
                },
                {
                    "name": "AI直接解答题目",
                    "content": "请解答给出的截图中的题目。回复的内容请勿包含任何markdown标记，把答案放在最前面，且简短讲解即可。"
                }
            ],
            # OCR配置 - 光学字符识别相关设置
            "ocr": {
                "engine": "vision_model",  # OCR引擎类型：xinyew(新野OCR)、tencent(腾讯云OCR)、vision_model(AI视觉模型)
                "type": "ocr_then_text",  # 处理类型：ocr_then_text(先OCR再分析)、direct_vision(直接视觉分析)
                # 腾讯云OCR配置
                "tencent": {
                    "secret_id": "",  # 腾讯云SecretId
                    "secret_key": "",  # 腾讯云SecretKey
                    "region": "ap-beijing",  # 服务区域
                    "language": "zh"  # 识别语言
                },
                # AI视觉模型OCR配置
                "vision_model": {
                    "name": "OCR专用模型",  # 模型名称
                    "model_id": "qwen2.5-vl-32b-instruct",  # 模型ID
                    "api_endpoint": "http://127.0.0.1:58888/v1/chat/completions",  # API端点
                    "api_key": "sk-example-key",  # API密钥
                    "max_tokens": 4096,  # 最大令牌数
                    "temperature": 0.1,  # 生成温度，OCR任务使用较低温度
                    "prompt": "请识别图片中的文字内容，并格式化后给我。只返回识别到的文字，不要添加任何解释或说明。"  # OCR专用提示词
                }
            },
            # 通知配置 - 结果展示方式设置
            "notification": {
                "type": "large_popup",  # 通知类型：none(不额外通知)、large_popup(大弹窗)、small_popup(小弹窗)、email(邮件)
                # SMTP邮件配置
                "smtp": {
                    "server": "smtp.qq.com",  # SMTP服务器地址
                    "port": 587,  # SMTP端口
                    "username": "",  # 邮箱用户名
                    "password": "",  # 邮箱密码或授权码
                    "to_email": ""  # 接收邮箱地址
                }
            },
            # 快捷键配置 - 全局热键设置
            "hotkey": {
                "screenshot": "alt+shift+d"  # 截图快捷键组合
            },
            # 截图配置 - 截图质量和格式设置
            "screenshot": {
                "quality": "high",  # 截图质量：high(高质量)、medium(中等)、low(低质量)
                "format": "PNG"  # 截图格式：PNG、JPEG
            },
            # 日志配置 - 应用程序日志记录设置
            "logging": {
                "level": "INFO"  # 日志级别：DEBUG、INFO、WARNING、ERROR、CRITICAL
            }
        }
        
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if not TOML_AVAILABLE:
                logging.warning("TOML模块不可用，使用默认配置")
                return True
                
            if os.path.exists(self.config_file):
                with open(self.config_file, 'rb') as f:
                    loaded_config = tomllib.load(f)
                self.config = self._merge_config(self._get_hardcoded_config(), loaded_config)
                logging.info("配置文件加载成功")
            else:
                logging.info("配置文件不存在，使用默认配置")
                self.save_config()
            
            self.config_changed.emit()
            return True
            
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return False
    
    def load_config_from_file(self, file_path: str) -> bool:
        """从指定文件加载配置"""
        try:
            if not TOML_AVAILABLE:
                logging.warning("TOML模块不可用，无法加载配置文件")
                return False
                
            if not os.path.exists(file_path):
                logging.error(f"配置文件不存在: {file_path}")
                return False
                
            with open(file_path, 'rb') as f:
                loaded_config = tomllib.load(f)
            
            # 更新当前配置文件路径
            self.config_file = file_path
            self.config = self._merge_config(self._get_hardcoded_config(), loaded_config)
            
            self.config_changed.emit()
            logging.info(f"从文件加载配置成功: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"从文件加载配置失败: {e}")
            return False
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            if not TOML_AVAILABLE:
                logging.warning("TOML模块不可用，无法保存配置")
                return False
            
            # 检查是否是首次创建配置文件
            is_first_time = not os.path.exists(self.config_file)
            
            if is_first_time:
                # 首次创建时生成带注释的配置文件
                self._save_config_with_comments()
            else:
                # 后续保存时使用标准方式
                with open(self.config_file, 'wb') as f:
                    tomli_w.dump(self.config, f)
            
            logging.info("配置文件保存成功")
            self.config_changed.emit()
            return True
            
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            return False
    
    def _save_config_with_comments(self) -> None:
        """保存带详细注释的配置文件"""
        # 使用硬编码配置生成带注释的TOML文件
        config = self._get_hardcoded_config()
        
        config_content = '''# AI截图分析工具配置文件
# 本文件包含应用程序的所有配置选项，每个选项都有详细说明

# ==================== AI模型配置 ====================
[ai_model]
# 定义使用的AI模型相关参数

# ◆ 模型显示名称
name = "{ai_model_name}"

# ◆ 模型标识符，用于API调用
model_id = "{ai_model_id}"

# ◆ API端点地址，支持本地Flask服务或远程API
# 内置服务：http://127.0.0.1:58888/v1/chat/completions
# 第三方服务示例：https://api.openai.com/v1/chat/completions
# 当您填写了第三方服务时，内置的服务将不会运行
api_endpoint = "{ai_api_endpoint}"

# ◆ API密钥，用于身份验证
# 使用内置服务时可以随便填
api_key = "{ai_api_key}"

# ◆ 最大令牌数，0表示使用模型默认值
max_tokens = {ai_max_tokens}

# ◆ 生成温度，控制回答的随机性(0-1)，值越低越确定
temperature = {ai_temperature}

# ◆ 模型是否有视觉
# 不知道就填false
vision_support = {ai_vision_support}

# ◆ 是否启用流式响应
# 秘塔AI请填false，响应速度较快的模型也推荐填false。深度思考一定填true。
enable_streaming = {ai_enable_streaming}

# ==================== 提示词配置 ====================
# ◆ 预定义的AI交互提示词模板，可根据不同场景，在软件内使用
{prompts_section}

# ==================== OCR配置 ====================
[ocr]
# ◆ 图片处理方式：
# - ocr_then_text: 先OCR提取文字再分析
# - direct_vision: 直接使用视觉AI分析图片
type = "{ocr_type}"

# ◆ OCR引擎类型：
# - xinyew: 新野OCR（免费，推荐）
# - tencent: 腾讯云OCR（需要配置密钥）
# - vision_model: AI视觉模型OCR
engine = "{ocr_engine}"

[ocr.tencent]
# 腾讯云OCR配置（仅当engine=tencent时需要）

# ◆ 腾讯云SecretId
secret_id = "{tencent_secret_id}"

# ◆ 腾讯云SecretKey
secret_key = "{tencent_secret_key}"

# ◆ 服务区域
# 推荐保持默认
region = "{tencent_region}"

# ◆ 识别语言：zh(中文)、en(英文)
# 推荐保持默认
language = "{tencent_language}"

[ocr.vision_model]
# AI视觉模型OCR配置（仅当engine=vision_model时需要）

# ◆ 模型名称
name = "{vision_model_name}"
# ◆ 模型ID
model_id = "{vision_model_id}"
# ◆ API端点
api_endpoint = "{vision_api_endpoint}"
# ◆ API密钥
api_key = "{vision_api_key}"
# ◆ 最大令牌数
max_tokens = {vision_max_tokens}
# ◆ 生成温度，OCR任务推荐使用较低温度
temperature = {vision_temperature}
# ◆ OCR专用提示词
prompt = "{vision_prompt}"

# ==================== 通知配置 ====================
[notification]
# 结果展示方式设置

# ◆ 通知类型：
# - none: 不额外通知
# - large_popup: 屏幕中心大弹窗
# - small_popup: 屏幕左下角小弹窗
# - email: 邮件通知
type = "{notification_type}"

[notification.smtp]
# SMTP邮件配置（仅当type=email时需要）
# 小贴士：邮件可以发给自己

# ◆ SMTP服务器地址
server = "{smtp_server}"

# ◆ SMTP端口
port = {smtp_port}

# ◆ 邮箱用户名
username = "{smtp_username}"

# ◆ 邮箱密码或授权码
password = "{smtp_password}"

# ◆ 接收邮箱地址
to_email = "{smtp_to_email}"

# ==================== 快捷键配置 ====================
[hotkey]
# 全局热键设置

# ◆ 截图快捷键组合
# 支持的修饰键：ctrl、alt、shift
# 示例："alt+shift+d"、"ctrl+alt+s"
# 建议事先验证您的快捷键是否已经被占用
screenshot = "{hotkey_screenshot}"

# ==================== 截图配置 ====================
[screenshot]
# 截图质量和格式设置

# ◆ 截图质量：high(高质量)、medium(中等)、low(低质量)
quality = "{screenshot_quality}"
# ◆ 截图格式：PNG、JPEG
format = "{screenshot_format}"

# ==================== 日志配置 ====================
[logging]
# ◆ 应用程序日志记录设置
# 日志级别：DEBUG、INFO、WARNING、ERROR、CRITICAL
# DEBUG: 详细调试信息
# INFO: 一般信息（推荐）
# WARNING: 警告信息
# ERROR: 错误信息
# CRITICAL: 严重错误
level = "{logging_level}"
'''
        
        # 生成提示词部分
        prompts_section = ""
        for prompt in config["prompts"]:
            prompts_section += f'''[[prompts]]
name = "{prompt["name"]}"
content = "{prompt["content"]}"

'''
        
        # 格式化配置内容
        formatted_content = config_content.format(
            ai_model_name=config["ai_model"]["name"],
            ai_model_id=config["ai_model"]["model_id"],
            ai_api_endpoint=config["ai_model"]["api_endpoint"],
            ai_api_key=config["ai_model"]["api_key"],
            ai_max_tokens=config["ai_model"]["max_tokens"],
            ai_temperature=config["ai_model"]["temperature"],
            ai_vision_support=str(config["ai_model"]["vision_support"]).lower(),
            ai_enable_streaming=str(config["ai_model"]["enable_streaming"]).lower(),
            prompts_section=prompts_section.strip(),
            ocr_type=config["ocr"]["type"],
            ocr_engine=config["ocr"]["engine"],
            tencent_secret_id=config["ocr"]["tencent"]["secret_id"],
            tencent_secret_key=config["ocr"]["tencent"]["secret_key"],
            tencent_region=config["ocr"]["tencent"]["region"],
            tencent_language=config["ocr"]["tencent"]["language"],
            vision_model_name=config["ocr"]["vision_model"]["name"],
            vision_model_id=config["ocr"]["vision_model"]["model_id"],
            vision_api_endpoint=config["ocr"]["vision_model"]["api_endpoint"],
            vision_api_key=config["ocr"]["vision_model"]["api_key"],
            vision_max_tokens=config["ocr"]["vision_model"]["max_tokens"],
            vision_temperature=config["ocr"]["vision_model"]["temperature"],
            vision_prompt=config["ocr"]["vision_model"]["prompt"],
            notification_type=config["notification"]["type"],
            smtp_server=config["notification"]["smtp"]["server"],
            smtp_port=config["notification"]["smtp"]["port"],
            smtp_username=config["notification"]["smtp"]["username"],
            smtp_password=config["notification"]["smtp"]["password"],
            smtp_to_email=config["notification"]["smtp"]["to_email"],
            hotkey_screenshot=config["hotkey"]["screenshot"],
            screenshot_quality=config["screenshot"]["quality"],
            screenshot_format=config["screenshot"]["format"],
            logging_level=config["logging"]["level"]
        )
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
    
    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """合并配置，确保所有默认键都存在"""
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
        """设置配置值"""
        try:
            keys = path.split('.')
            config = self.config
            
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            config[keys[-1]] = value
            return True
            
        except Exception as e:
            logging.error(f"设置配置失败: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """导出配置文件"""
        try:
            if not TOML_AVAILABLE:
                return False
                
            with open(file_path, 'wb') as f:
                tomli_w.dump(self.config, f)
            return True
        except Exception as e:
            logging.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """导入配置文件"""
        try:
            if not TOML_AVAILABLE:
                return False
                
            with open(file_path, 'rb') as f:
                imported_config = tomllib.load(f)
            
            self.config = self._merge_config(self._get_hardcoded_config(), imported_config)
            self.save_config()
            return True
            
        except Exception as e:
            logging.error(f"导入配置失败: {e}")
            return False
    
    def reset_config(self) -> bool:
        """重置为默认配置"""
        try:
            self.config = self._get_hardcoded_config()
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
                logging.info("配置文件已删除")
            return True
        except Exception as e:
            logging.error(f"删除配置文件失败: {e}")
            return False


class LogManager:
    """日志管理器"""
    
    def __init__(self):
        self.log_dir = "logs"
        
    def setup_logging(self, level: str = "INFO"):
        """设置日志"""
        # 创建日志目录
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # 清理旧日志
        self._cleanup_old_logs()
        
        # 设置日志格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 设置日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"app_{timestamp}.log")
        
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def _cleanup_old_logs(self):
        """清理旧日志文件，保留最近10个"""
        try:
            log_files = glob.glob(os.path.join(self.log_dir, "app_*.log"))
            log_files.sort(key=os.path.getmtime, reverse=True)
            
            # 删除超过10个的旧日志
            for old_log in log_files[10:]:
                os.remove(old_log)
                
        except Exception as e:
            print(f"清理日志文件失败: {e}")


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        pass
    
    def handle_error(self, error: Exception, context: str = "", show_dialog: bool = True):
        """处理错误"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        logging.error(error_msg, exc_info=True)
        
        if show_dialog:
            self.show_error_dialog(error_msg)
    
    def show_error_dialog(self, message: str):
        """显示错误对话框"""
        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("错误")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        except Exception as e:
            print(f"显示错误对话框失败: {e}")


class TaskManager(QObject):
    """任务管理器"""
    
    task_started = pyqtSignal()
    task_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._current_task = None
    
    def is_running(self) -> bool:
        """检查是否有任务在运行"""
        return self._is_running
    
    def start_task(self, task_name: str) -> bool:
        """开始任务"""
        if self._is_running:
            logging.warning(f"任务 {self._current_task} 正在运行，无法启动新任务 {task_name}")
            return False
        
        self._is_running = True
        self._current_task = task_name
        self.task_started.emit()
        logging.info(f"任务开始: {task_name}")
        return True
    
    def finish_task(self):
        """完成任务"""
        if self._is_running:
            logging.info(f"任务完成: {self._current_task}")
            self._is_running = False
            self._current_task = None
            self.task_finished.emit()
    
    def get_current_task(self) -> Optional[str]:
        """获取当前任务名称"""
        return self._current_task