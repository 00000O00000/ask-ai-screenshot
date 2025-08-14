#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI截图分析核心功能模块
包含截图、OCR、AI客户端等核心功能
"""

import os
import io
import base64
import json
import logging
import smtplib
import time
import hashlib
import hmac
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import requests
from PIL import Image, ImageGrab
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from pynput import keyboard

from screenshot_overlay import AdvancedScreenshotManager


class ScreenshotManager(QObject):
    """截图管理器"""
    
    screenshot_taken = pyqtSignal(object)  # 截图完成信号
    screenshot_failed = pyqtSignal(str)    # 截图失败信号
    screenshot_cancelled = pyqtSignal()    # 截图取消信号
    hotkey_triggered = pyqtSignal()        # 快捷键触发信号
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.advanced_manager = AdvancedScreenshotManager(config_manager)
        self.hotkey_listener = None
        
        # 连接快捷键信号到截图方法
        self.hotkey_triggered.connect(self.start_screenshot)
        
        # 连接高级截图管理器信号
        self.advanced_manager.overlay = None  # 初始化overlay属性
        # 注意：信号连接需要在overlay创建后进行
    
    def setup_hotkey(self):
        """设置全局快捷键"""
        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
            
            # 使用固定的快捷键 Alt+Shift+D
            hotkey_combination = {keyboard.Key.alt, keyboard.Key.shift, keyboard.KeyCode.from_char('d')}
            
            def on_hotkey():
                # 使用信号来避免在快捷键回调中直接调用UI操作
                self.hotkey_triggered.emit()
            
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<alt>+<shift>+d': on_hotkey
            })
            self.hotkey_listener.start()
            
            logging.info("全局快捷键设置成功: Alt+Shift+D")
            
        except Exception as e:
            logging.error(f"设置全局快捷键失败: {e}")
    
    def start_screenshot(self):
        """开始截图"""
        try:
            # 先断开之前的连接（如果存在）
            if self.advanced_manager.overlay:
                try:
                    self.advanced_manager.overlay.screenshot_confirmed.disconnect()
                    self.advanced_manager.overlay.screenshot_cancelled.disconnect()
                except:
                    pass
            
            # 启动截图
            self.advanced_manager.start_screenshot()
            
            # 连接信号（在overlay创建后）
            if self.advanced_manager.overlay:
                self.advanced_manager.overlay.screenshot_confirmed.connect(self.on_screenshot_confirmed)
                self.advanced_manager.overlay.screenshot_cancelled.connect(self.on_screenshot_cancelled)
                logging.info("截图信号连接成功")
            else:
                logging.error("截图overlay创建失败")
                self.screenshot_failed.emit("截图overlay创建失败")
                
        except Exception as e:
            logging.error(f"启动截图失败: {e}")
            self.screenshot_failed.emit(str(e))
    
    def screenshot_from_clipboard(self):
        """从剪贴板获取图片"""
        try:
            image = ImageGrab.grabclipboard()
            if image and isinstance(image, Image.Image):
                return image
            return None
        except Exception as e:
            logging.error(f"从剪贴板获取图片失败: {e}")
            return None
    
    def on_screenshot_confirmed(self, image):
        """截图确认处理"""
        self.screenshot_taken.emit(image)
    
    def on_screenshot_cancelled(self):
        """截图取消处理"""
        self.screenshot_cancelled.emit()
    
    def cleanup(self):
        """清理资源"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()


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
            # 在WorkerThread中不发射信号，直接抛出异常
            raise Exception(error_msg)
    
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
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if "Response" in result and "TextDetections" in result["Response"]:
                texts = [item["DetectedText"] for item in result["Response"]["TextDetections"]]
                ocr_text = "\n".join(texts)
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
            upload_response = requests.post(upload_url, files=files, timeout=10)
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
                timeout=10
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
            
            return ocr_text
            
        except Exception as e:
            raise Exception(f"新野OCR识别失败: {e}")
    
    def _vision_model_ocr(self, image: Image.Image) -> str:
        """视觉模型OCR"""
        try:
            # 获取OCR专用视觉模型配置
            vision_model = self.config_manager.get_config("ocr.vision_model")
            
            if not vision_model:
                raise ValueError("未配置OCR专用视觉模型")
            
            # 检查必要配置
            if not vision_model.get('model_id') or not vision_model.get('api_endpoint') or not vision_model.get('api_key'):
                raise ValueError("OCR视觉模型配置不完整")
            
            # 将图片转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 获取OCR提示词
            ocr_prompt = vision_model.get('prompt', '请识别图片中的文字内容，并格式化后给我。只返回识别到的文字，不要添加任何解释或说明。')
            
            # 构建请求
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ocr_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            request_data = {
                "model": vision_model.get('model_id', ''),
                "messages": messages,
                "max_tokens": vision_model.get('max_tokens', 1000),
                "temperature": vision_model.get('temperature', 0.1)
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {vision_model.get('api_key', '')}"
            }
            
            response = requests.post(
                vision_model.get('api_endpoint', ''),
                headers=headers,
                json=request_data,
                timeout=120
            )
            
            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.status_code} - {response.text}")
            
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise Exception("API响应格式错误")
            
            ocr_text = result['choices'][0]['message']['content'].strip()
            return ocr_text
            
        except Exception as e:
            raise Exception(f"视觉模型OCR失败: {e}")


class AIRequestThread(QThread):
    """AI请求线程"""
    
    response_completed = pyqtSignal(str)  # 响应完成信号
    request_failed = pyqtSignal(str)      # 请求失败信号
    streaming_response = pyqtSignal(str, str)  # 流式响应信号 (类型, 内容)
    reasoning_content = pyqtSignal(str)   # 推理内容信号
    
    def __init__(self, ai_config, prompt, image=None, ocr_text=None):
        super().__init__()
        self.ai_config = ai_config
        self.prompt = prompt
        self.image = image
        self.ocr_text = ocr_text
        self.should_stop = False
    
    def stop_request(self):
        """停止请求"""
        self.should_stop = True
    
    def run(self):
        """执行AI请求"""
        try:
            response = self._send_ai_request()
            if not self.should_stop:
                self.response_completed.emit(response)
        except Exception as e:
            if not self.should_stop:
                self.request_failed.emit(str(e))
    
    def _send_ai_request(self):
        """发送AI请求"""
        # 构建请求消息
        messages = []
        
        if self.image and self.ai_config.get('vision_support', False):
            # 支持视觉的模型
            # 将图片转换为base64
            img_byte_arr = io.BytesIO()
            self.image.save(img_byte_arr, format='PNG')
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    }
                ]
            })
        else:
            # 文本模型或包含OCR文本
            content = self.prompt
            if self.ocr_text:
                content += f"\n\n以下是图片中识别的文字内容：\n{self.ocr_text}"
            
            messages.append({
                "role": "user",
                "content": content
            })
        
        # 检查是否支持流式响应
        enable_streaming = self.ai_config.get('enable_streaming', False)
        
        # 构建请求数据
        request_data = {
            "model": self.ai_config.get('model_id', ''),
            "messages": messages,
            "max_tokens": self.ai_config.get('max_tokens', 4000),
            "temperature": self.ai_config.get('temperature', 0.3),
            "stream": enable_streaming
        }
        
        # 发送请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ai_config.get('api_key', '')}"
        }
        
        if enable_streaming:
            return self._handle_streaming_response(headers, request_data)
        else:
            return self._handle_normal_response(headers, request_data)
    
    def _handle_normal_response(self, headers, request_data):
        """处理普通响应"""
        response = requests.post(
            self.ai_config.get('api_endpoint', ''),
            headers=headers,
            json=request_data,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if 'choices' not in result or not result['choices']:
            raise Exception("API响应格式错误")
        
        content = result['choices'][0]['message']['content']
        
        # 尝试解析推理内容和回复内容
        reasoning_content, response_content = self._parse_reasoning_and_response(content)
        
        if reasoning_content:
            self.reasoning_content.emit(reasoning_content)
        
        return response_content or content
    
    def _handle_streaming_response(self, headers, request_data):
        """处理流式响应"""
        response = requests.post(
            self.ai_config.get('api_endpoint', ''),
            headers=headers,
            json=request_data,
            timeout=60,
            stream=True
        )
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")
        
        full_content = ""
        
        for line in response.iter_lines():
            if self.should_stop:
                break
                
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            
                            # 处理推理内容（只依据API返回的reasoning_content字段）
                            if 'reasoning_content' in delta and delta['reasoning_content']:
                                reasoning_content = delta['reasoning_content']
                                self.reasoning_content.emit(reasoning_content)
                            
                            # 处理普通响应内容
                            if 'content' in delta and delta['content']:
                                content = delta['content']
                                full_content += content
                                self.streaming_response.emit("content", content)
                                
                    except json.JSONDecodeError:
                        continue
        
        return full_content
    
    def _parse_reasoning_and_response(self, content):
        """解析推理内容和回复内容"""
        reasoning_content = ""
        response_content = content
        
        # 查找 <thinking> 标签
        import re
        thinking_pattern = r'<thinking>(.*?)</thinking>'
        matches = re.findall(thinking_pattern, content, re.DOTALL)
        
        if matches:
            reasoning_content = '\n'.join(matches).strip()
            # 移除推理内容，保留回复内容
            response_content = re.sub(thinking_pattern, '', content, flags=re.DOTALL).strip()
        
        return reasoning_content, response_content


class AIClientManager(QObject):
    """AI客户端管理器"""
    
    response_completed = pyqtSignal(str)  # 响应完成信号
    request_failed = pyqtSignal(str)      # 请求失败信号
    streaming_response = pyqtSignal(str, str)  # 流式响应信号
    reasoning_content = pyqtSignal(str)   # 推理内容信号
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.current_thread = None
    
    def send_request(self, model_name, prompt, image=None, ocr_text=None):
        """发送AI请求"""
        try:
            # 获取AI配置
            ai_config = self.config_manager.get_config("ai_model")
            if not ai_config:
                self.request_failed.emit("AI模型配置不存在")
                return
            
            # 停止之前的请求
            self.stop_request()
            
            # 创建新的请求线程
            self.current_thread = AIRequestThread(ai_config, prompt, image, ocr_text)
            self.current_thread.response_completed.connect(self.response_completed)
            self.current_thread.request_failed.connect(self.request_failed)
            self.current_thread.streaming_response.connect(self.streaming_response)
            self.current_thread.reasoning_content.connect(self.reasoning_content)
            
            # 启动线程
            self.current_thread.start()
            
        except Exception as e:
            self.request_failed.emit(str(e))
    
    def stop_request(self):
        """停止当前请求"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.stop_request()
            self.current_thread.wait()
    
    def cleanup(self):
        """清理资源"""
        self.stop_request()


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
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
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