#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析 - 核心功能模块
包含截图、OCR、AI客户端、邮件管理等功能
"""

import io
import json
import logging
import smtplib
import time
import hashlib
import hmac
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests
from PIL import Image
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import QApplication

# 导入高级截图功能
from screenshot_overlay import AdvancedScreenshotManager


class ScreenshotManager(QObject):
    """截图管理器 - 重写版本，提供流畅的截图体验"""
    
    screenshot_taken = pyqtSignal(object)  # 截图完成信号
    screenshot_failed = pyqtSignal(str)  # 截图失败信号
    hotkey_conflict = pyqtSignal(str)  # 快捷键冲突信号
    screenshot_cancelled = pyqtSignal()  # 截图取消信号
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.listener = None
        self.is_capturing = False
        self.current_hotkey = None
        
        # 初始化高级截图管理器
        self.advanced_manager = AdvancedScreenshotManager(config_manager)
        self._setup_advanced_connections()
        
        # 只使用高级截图模式
        
    def _setup_advanced_connections(self):
        """设置高级截图管理器的信号连接"""
        if hasattr(self.advanced_manager, 'overlay'):
            # 连接信号会在overlay创建时进行
            pass
        
    def setup_hotkey(self) -> bool:
        """设置全局快捷键"""
        try:
            hotkey_str = self.config_manager.get_config("hotkey.screenshot")
            if not hotkey_str or hotkey_str.strip() == "":
                hotkey_str = "alt+shift+d"
            
            # 停止之前的监听器
            if self.listener:
                self.listener.stop()
            
            # 验证快捷键格式
            if not self._validate_hotkey(hotkey_str):
                logging.error(f"无效的快捷键格式: {hotkey_str}")
                return False
            
            # 创建新的监听器
            # 转换快捷键格式为pynput格式
            pynput_hotkey = self._convert_to_pynput_format(hotkey_str)
            self.listener = keyboard.GlobalHotKeys({
                pynput_hotkey: self._on_hotkey_pressed
            })
            
            self.listener.start()
            self.current_hotkey = hotkey_str
            logging.info(f"快捷键设置成功: {hotkey_str}")
            return True
            
        except Exception as e:
            logging.error(f"设置快捷键失败: {e}")
            self.hotkey_conflict.emit(str(e))
            return False
    
    def _validate_hotkey(self, hotkey_str: str) -> bool:
        """验证快捷键格式"""
        try:
            if not hotkey_str or hotkey_str.strip() == "":
                return False
            
            # 检查基本格式
            parts = hotkey_str.lower().split('+')
            if len(parts) < 1:
                return False
            
            # 验证修饰键和主键
            valid_modifiers = {'ctrl', 'alt', 'shift', 'cmd', 'super'}
            valid_keys = {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 
                         'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                         'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
                         'space', 'enter', 'tab', 'esc', 'escape'}
            
            for part in parts:
                part = part.strip()
                if not part:
                    return False
                # 最后一个部分可以是主键，其他必须是修饰键
                if part == parts[-1]:
                    if part not in valid_modifiers and part not in valid_keys:
                        return False
                else:
                    if part not in valid_modifiers:
                        return False
            
            return True
        except Exception:
            return False
    
    def _convert_to_pynput_format(self, hotkey_str: str) -> str:
        """转换快捷键格式为pynput格式"""
        try:
            parts = hotkey_str.lower().split('+')
            converted_parts = []
            
            for part in parts:
                part = part.strip()
                # 转换修饰键
                if part == 'ctrl':
                    converted_parts.append('<ctrl>')
                elif part == 'alt':
                    converted_parts.append('<alt>')
                elif part == 'shift':
                    converted_parts.append('<shift>')
                elif part == 'cmd' or part == 'super':
                    converted_parts.append('<cmd>')
                else:
                    # 普通按键
                    converted_parts.append(part)
            
            return '+'.join(converted_parts)
        except Exception:
            return hotkey_str
    
    def _on_hotkey_pressed(self):
        """快捷键按下回调"""
        if not self.is_capturing:
            # 使用QTimer延迟执行，避免阻塞快捷键线程
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self.start_screenshot)
    
    def start_screenshot(self):
        """开始截图"""
        try:
            self.is_capturing = True
            
            # 只使用高级截图模式
            self._start_advanced_screenshot()
                
        except Exception as e:
            logging.error(f"截图失败: {e}")
            self.screenshot_failed.emit(str(e))
            self.is_capturing = False
    
    def _start_advanced_screenshot(self):
        """启动高级截图模式"""
        try:
            # 启动高级截图
            self.advanced_manager.start_screenshot()
            
            # 连接信号
            if self.advanced_manager.overlay:
                self.advanced_manager.overlay.screenshot_confirmed.connect(self._on_advanced_screenshot_confirmed)
                self.advanced_manager.overlay.screenshot_cancelled.connect(self._on_advanced_screenshot_cancelled)
            else:
                logging.error("高级截图覆盖层创建失败")
                self.is_capturing = False
                
        except Exception as e:
            logging.error(f"启动高级截图失败: {e}")
            self.is_capturing = False
    

    
    def _on_advanced_screenshot_confirmed(self, screenshot):
        """高级截图确认回调"""
        try:
            self.screenshot_taken.emit(screenshot)
            logging.info("高级截图已确认")
        except Exception as e:
            logging.error(f"处理高级截图确认时出错: {e}")
        finally:
            self.is_capturing = False
    
    def _on_advanced_screenshot_cancelled(self):
        """高级截图取消回调"""
        try:
            self.screenshot_cancelled.emit()
            logging.info("高级截图已取消")
        except Exception as e:
            logging.error(f"处理高级截图取消时出错: {e}")
        finally:
            self.is_capturing = False
    

    
    def screenshot_from_clipboard(self) -> Optional[Image.Image]:
        """从剪贴板获取图片"""
        try:
            clipboard = QApplication.clipboard()
            pixmap = clipboard.pixmap()
            
            if not pixmap.isNull():
                # 将QPixmap转换为PIL Image
                buffer = io.BytesIO()
                pixmap.save(buffer, "PNG")
                buffer.seek(0)
                image = Image.open(buffer)
                logging.info("从剪贴板获取图片成功")
                return image
            else:
                logging.warning("剪贴板中没有图片")
                return None
                
        except Exception as e:
            logging.error(f"从剪贴板获取图片失败: {e}")
            return None
    
    def cleanup(self):
        """清理资源"""
        if self.listener:
            self.listener.stop()
            self.listener = None
            
        # 清理高级截图管理器
        if hasattr(self, 'advanced_manager'):
            self.advanced_manager.cleanup()


class OCRManager(QObject):
    """OCR管理器"""
    
    ocr_completed = pyqtSignal(str)  # OCR完成信号
    ocr_failed = pyqtSignal(str)  # OCR失败信号
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
    
    def recognize_image(self, image: Image.Image) -> str:
        """识别图片中的文字"""
        try:
            engine = self.config_manager.get_config("ocr.engine")
            
            if engine == "tencent":
                return self._tencent_ocr(image)
            elif engine == "xinyew":
                return self._xinyew_ocr(image)
            elif engine == "vision_model":
                return self._vision_model_ocr(image)
            else:
                # 默认使用新野OCR
                return self._xinyew_ocr(image)
                
        except Exception as e:
            error_msg = f"OCR识别失败: {e}"
            logging.error(error_msg)
            self.ocr_failed.emit(error_msg)
            return ""
    
    def _tencent_ocr(self, image: Image.Image) -> str:
        """腾讯云OCR"""
        try:
            # 获取配置
            secret_id = self.config_manager.get_config("ocr.tencent.secret_id")
            secret_key = self.config_manager.get_config("ocr.tencent.secret_key")
            
            if not secret_id or not secret_key:
                raise ValueError("腾讯云OCR配置不完整")
            
            # 将图片转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 构建请求
            url = "https://ocr.tencentcloudapi.com/"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Host": "ocr.tencentcloudapi.com",
                "X-TC-Action": "GeneralBasicOCR",
                "X-TC-Version": "2018-11-19",
                "X-TC-Region": "ap-beijing",
                "X-TC-Timestamp": str(int(time.time()))
            }
            
            payload = {
                "ImageBase64": image_base64
            }
            
            # 计算签名
            signature = self._calculate_tencent_signature(
                secret_id, secret_key, headers, json.dumps(payload)
            )
            headers["Authorization"] = signature
            
            # 发送请求
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if "Response" in result and "TextDetections" in result["Response"]:
                texts = [item["DetectedText"] for item in result["Response"]["TextDetections"]]
                ocr_text = "\n".join(texts)
                self.ocr_completed.emit(ocr_text)
                return ocr_text
            else:
                raise ValueError("OCR响应格式错误")
                
        except Exception as e:
            raise Exception(f"腾讯云OCR失败: {e}")
    
    def _calculate_tencent_signature(self, secret_id: str, secret_key: str, headers: dict, payload: str) -> str:
        """计算腾讯云签名"""
        # 这里是简化的签名计算，实际项目中需要完整的腾讯云签名算法
        # 由于篇幅限制，这里只是示例
        algorithm = "TC3-HMAC-SHA256"
        service = "ocr"
        host = "ocr.tencentcloudapi.com"
        
        # 构建规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{host}\n"
        signed_headers = "content-type;host"
        hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
        
        # 构建待签名字符串
        timestamp = headers["X-TC-Timestamp"]
        date = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
        credential_scope = f"{date}/{service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # 计算签名
        secret_date = hmac.new(("TC3" + secret_key).encode('utf-8'), date.encode('utf-8'), hashlib.sha256).digest()
        secret_service = hmac.new(secret_date, service.encode('utf-8'), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode('utf-8'), hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        return f"{algorithm} Credential={secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    
    def _xinyew_ocr(self, image: Image.Image) -> str:
        """新野图床+云智OCR识别（免费公益接口）"""
        try:
            # 1. 上传图片到新野图床
            upload_url = "https://api.xinyew.cn/api/360tc"
            
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            
            files = {'file': ('image.png', buffer, 'image/png')}
            upload_response = requests.post(upload_url, files=files, timeout=30)
            upload_response.raise_for_status()
            
            upload_result = upload_response.json()
            if upload_result.get("errno") != 0:
                raise ValueError(f"图片上传失败: {upload_result.get('error')}")
                
            image_url = upload_result.get("data", {}).get("url")
            if not image_url:
                raise ValueError("获取图片URL失败")
            
            # 2. 调用云智OCR接口
            ocr_url = "https://api.jkyai.top/API/ocrwzsb.php"
            ocr_response = requests.get(
                ocr_url,
                params={"url": image_url, "type": "json"},
                timeout=30
            )
            ocr_response.raise_for_status()
            
            ocr_result = ocr_response.json()
            
            # 3. 解析结果
            words_result = ocr_result.get("words_result", [])
            if not words_result:
                ocr_text = "未识别到文字内容"
            else:
                # 合并所有识别的文字
                text_lines = [item.get("words", "") for item in words_result]
                ocr_text = "\n".join(text_lines)
            
            self.ocr_completed.emit(ocr_text)
            return ocr_text
            
        except Exception as e:
            raise Exception(f"新野OCR识别失败: {e}")
    
    def _vision_model_ocr(self, image: Image.Image) -> str:
        """视觉模型OCR"""
        try:
            # 获取视觉模型配置
            vision_config = self.config_manager.get_config("ocr.vision_model")
            if not vision_config:
                raise Exception("视觉模型配置不存在")
            
            api_key = vision_config.get("api_key", "")
            if not api_key:
                raise Exception("视觉模型API密钥未配置")
            
            # 将图片转换为base64
            import io
            import base64
            
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 构建请求数据
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            prompt = vision_config.get("prompt", "请识别图片中的文字内容，并格式化后给我。只返回识别到的文字，不要添加任何解释或说明。")
            data = {
                "model": vision_config.get("model_id", ""),
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": vision_config.get("temperature", 0.3)
            }
            
            # 只有当max_tokens大于0时才添加此参数
            max_tokens = vision_config.get("max_tokens", 1000)
            if max_tokens > 0:
                data["max_tokens"] = max_tokens
            
            # 发送请求
            import requests
            response = requests.post(
                vision_config.get("api_endpoint", "") + "/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
            
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise Exception("API响应格式错误")
            
            ocr_text = result["choices"][0]["message"]["content"].strip()
            
            if not ocr_text:
                ocr_text = "未识别到文字内容"
            
            self.ocr_completed.emit(ocr_text)
            return ocr_text
            
        except Exception as e:
            raise Exception(f"视觉模型OCR识别失败: {e}")


class AIRequestThread(QThread):
    """AI请求工作线程"""
    
    response_completed = pyqtSignal(str)  # 响应完成信号
    request_failed = pyqtSignal(str)  # 请求失败信号
    streaming_response = pyqtSignal(str, str)  # 流式响应信号 (content_type, content)
    reasoning_content = pyqtSignal(str)  # 推理内容信号
    
    def __init__(self, model_config, request_data):
        super().__init__()
        self.model_config = model_config
        self.request_data = request_data
        self.should_stop = False
        self.accumulated_content = ""
        self.accumulated_reasoning = ""
    
    def run(self):
        """执行AI请求"""
        try:
            self._send_streaming_request()
        except Exception as e:
            if not self.should_stop:
                error_msg = f"AI请求失败: {e}"
                logging.error(error_msg)
                self.request_failed.emit(error_msg)
    
    def stop(self):
        """停止请求"""
        self.should_stop = True
        self.quit()
        self.wait()
    

    
    def _send_streaming_request(self):
        """发送流式请求"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.model_config['api_key']}"
        }
        
        # 添加流式请求参数
        stream_request_data = self.request_data.copy()
        stream_request_data["stream"] = True
        
        try:
            response = requests.post(
                self.model_config["api_endpoint"],
                headers=headers,
                json=stream_request_data,
                timeout=200,
                stream=True
            )
            
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}: {response.text}"
                logging.error(f"API请求失败 - {error_detail}")
                raise Exception(f"API请求失败: {error_detail}")
            
            response.raise_for_status()
            
            # 处理流式响应
            for line in response.iter_lines():
                if self.should_stop:
                    break
                    
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        data_text = line_text[6:]  # 移除 'data: ' 前缀
                        
                        if data_text.strip() == '[DONE]':
                            break
                            
                        try:
                            data = json.loads(data_text)
                            if 'choices' in data and len(data['choices']) > 0:
                                choice = data['choices'][0]
                                if 'delta' in choice:
                                    delta = choice['delta']
                                    
                                    # 处理推理内容（推理模型特有）
                                    if 'reasoning_content' in delta and delta['reasoning_content']:
                                        reasoning_content = delta['reasoning_content']
                                        self.accumulated_reasoning += reasoning_content
                                        self.reasoning_content.emit(reasoning_content)
                                    
                                    # 处理普通内容
                                    if 'content' in delta and delta['content']:
                                        content = delta['content']
                                        self._process_streaming_content(content)
                        except json.JSONDecodeError:
                            continue
            
            # 发送完成信号
            if not self.should_stop:
                final_content = self.accumulated_content
                if self.accumulated_reasoning:
                    final_content = f"**思考内容：**\n{self.accumulated_reasoning}\n\n**回复内容：**\n{self.accumulated_content}"
                self.response_completed.emit(final_content)
                
        except Exception as e:
            # 如果流式请求失败，尝试普通请求
            logging.warning(f"流式请求失败，尝试普通请求: {e}")
            self._send_normal_request_fallback()
    
    def _process_streaming_content(self, content):
        """处理流式内容"""
        # 检测是否是推理内容（支持多种格式）
        is_reasoning = False
        
        # 检查常见的推理标签格式
        reasoning_indicators = [
            '<thinking>', '</thinking>',  # 标准thinking标签
            '<thought>', '</thought>',    # thought标签
            '思考：', '推理：', '分析：',     # 中文推理标识
            'Thinking:', 'Reasoning:', 'Analysis:'  # 英文推理标识
        ]
        
        for indicator in reasoning_indicators:
            if indicator in content:
                is_reasoning = True
                break
        
        # 对于Thinking模型，如果内容看起来像推理过程，也归类为推理内容
        if not is_reasoning and hasattr(self, 'model_config'):
            model_name = self.model_config.get('name', '').lower()
            if 'thinking' in model_name:
                # 检查是否包含推理特征（如步骤、分析等）
                reasoning_patterns = ['步骤', '首先', '然后', '因此', '所以', '分析', '考虑']
                for pattern in reasoning_patterns:
                    if pattern in content:
                        is_reasoning = True
                        break
        
        if is_reasoning:
            self.accumulated_reasoning += content
            self.reasoning_content.emit(content)
        else:
            self.accumulated_content += content
            self.streaming_response.emit("content", content)
    
    def _send_normal_request_fallback(self):
        """发送普通请求（作为流式请求的备用方案）"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.model_config['api_key']}"
        }
        
        response = requests.post(
            self.model_config["api_endpoint"],
            headers=headers,
            json=self.request_data,
            timeout=200
        )
        
        if response.status_code != 200:
            error_detail = f"HTTP {response.status_code}: {response.text}"
            logging.error(f"API请求失败 - {error_detail}")
            raise Exception(f"API请求失败: {error_detail}")
        
        response.raise_for_status()
        
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            if not self.should_stop:
                self.response_completed.emit(content)
        else:
            raise ValueError("响应格式错误")


class AIClientManager(QObject):
    """AI客户端管理器"""
    
    response_completed = pyqtSignal(str)  # 响应完成信号
    request_failed = pyqtSignal(str)  # 请求失败信号
    streaming_response = pyqtSignal(str, str)  # 流式响应信号 (content_type, content)
    reasoning_content = pyqtSignal(str)  # 推理内容信号
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.current_thread = None
    
    def send_request(self, model_id: str, prompt: str, image: Optional[Image.Image] = None, ocr_text: str = ""):
        """发送AI请求"""
        try:
            # 停止之前的请求
            if self.current_thread and self.current_thread.isRunning():
                self.current_thread.stop()
            
            # 获取模型配置
            model_config = self.config_manager.get_config(f"ai_models.{model_id}")
            if not model_config:
                raise ValueError(f"模型配置不存在: {model_id}")
            
            # 构建消息
            messages = self._build_messages(prompt, image, ocr_text, model_config)
            
            # 构建请求数据
            request_data = {
                "model": model_config["model_id"],
                "messages": messages,
                "temperature": model_config.get("temperature", 0.3)
            }
            
            if model_config.get("max_tokens", 0) > 0:
                request_data["max_tokens"] = model_config["max_tokens"]
            
            # 创建并启动请求线程
            self.current_thread = AIRequestThread(model_config, request_data)
            
            # 连接信号
            self.current_thread.response_completed.connect(self.response_completed.emit)
            self.current_thread.request_failed.connect(self.request_failed.emit)
            self.current_thread.streaming_response.connect(self.streaming_response.emit)
            self.current_thread.reasoning_content.connect(self.reasoning_content.emit)
            
            # 启动线程
            self.current_thread.start()
                
        except Exception as e:
            error_msg = f"AI请求失败: {e}"
            logging.error(error_msg)
            logging.error(f"模型配置: {model_config if 'model_config' in locals() else 'N/A'}")
            logging.error(f"请求数据: {request_data if 'request_data' in locals() else 'N/A'}")
            self.request_failed.emit(error_msg)
    
    def _build_messages(self, prompt: str, image: Optional[Image.Image], ocr_text: str, model_config: dict) -> list:
        """构建消息列表"""
        messages = []
        
        # 构建用户消息
        if model_config.get("vision_support", False) and image:
            # 支持视觉的模型
            content = [{"type": "text", "text": prompt}]
            
            if ocr_text:
                content[0]["text"] += f"\n\n图片中的文字内容：\n{ocr_text}"
            
            # 将图片转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            })
            
            messages.append({"role": "user", "content": content})
        else:
            # 不支持视觉的模型，只发送文本
            text_content = prompt
            if ocr_text:
                text_content += f"\n\n图片中的文字内容：\n{ocr_text}"
            
            messages.append({"role": "user", "content": text_content})
        
        return messages
    

    
    def _send_normal_request(self, model_config: dict, request_data: dict):
        """发送普通请求"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {model_config['api_key']}"
            }
            
            response = requests.post(
                model_config["api_endpoint"],
                headers=headers,
                json=request_data,
                timeout=200
            )
            
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}: {response.text}"
                logging.error(f"API请求失败 - {error_detail}")
                raise Exception(f"API请求失败: {error_detail}")
            
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                self.response_completed.emit(content)
            else:
                raise ValueError("响应格式错误")
                
        except Exception as e:
            raise Exception(f"普通请求失败: {e}")
    
    def stop_request(self):
        """停止当前请求"""
        if self.current_thread and self.current_thread.isRunning():
            try:
                self.current_thread.stop()
            except Exception:
                pass
            self.current_thread = None


class EmailManager(QObject):
    """邮件管理器"""
    
    email_sent = pyqtSignal()
    email_failed = pyqtSignal(str)
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
    
    def send_email(self, subject: str, content: str):
        """发送邮件"""
        try:
            smtp_config = self.config_manager.get_config("notification.smtp")
            if not smtp_config or not all([
                smtp_config.get("server"),
                smtp_config.get("username"),
                smtp_config.get("password"),
                smtp_config.get("to_email")
            ]):
                raise ValueError("SMTP配置不完整")
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = smtp_config["username"]
            msg['To'] = smtp_config["to_email"]
            msg['Subject'] = subject
            
            # 添加邮件内容
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(smtp_config["server"], smtp_config.get("port", 587))
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.send_message(msg)
            server.quit()
            
            self.email_sent.emit()
            logging.info("邮件发送成功")
            
        except Exception as e:
            error_msg = f"邮件发送失败: {e}"
            logging.error(error_msg)
            self.email_failed.emit(error_msg)