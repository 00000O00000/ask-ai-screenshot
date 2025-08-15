# ai.py
# pip install requests flask flask-cors oss2

# 使用Qwen3 Coder写的chat.qwen.ai网页API逆向，AI的刀先插在自己身上了说是。
# 扒源码的哥们，网页端token数上传限制为96000，我没有对大于这个token的请求做错误处理，别被坑了。

import requests
import uuid
import time
import json
import os
import warnings
import base64
import hashlib
import random
from urllib.parse import urlparse
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import oss2

# ==================== 配置区域 ====================
# 负载均衡token池
# 来扒源码的人就别抄这个Token了，你随便去chat.qwen.ai注册几个新号，都比用下面这些万人token好。
# 逆向源码摆在这了，就被用这个token了。
# 后面代码的注释全是AI写的，我也懒得管这个逆向有哪些报错，你看着办吧。
QWEN_AUTH_TOKENS = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjlkYzNkNGI0LWE2ZGYtNGNjMi1iM2U4LWQwM2MzZGRhOWJlYSIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzU1MTM1NzQwLCJleHAiOjE3NTc3Mjc3ODV9.BbLfc-uPkiuXg5EtGQ8PBk9OEYAeTGunr043feyPxm4",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjMTI2NjU0LTNiN2ItNDhhYi1hMDlkLTdjYWRhYmIzMWNiOCIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzU1MTQwOTgyLCJleHAiOjE3NTc3MzMwMTd9.grDFRe5JEg_q2NAy7rFIRQXhph3T8VmUpkgeJMC4nBY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjNlNWYzZTQ4LWNmMGYtNDE0Yy04Yzc0LWRlZjA1YWUxNzZhMyIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzU1MTQxMTA4LCJleHAiOjE3NTc3MzMxMzJ9.e2zfnKgLHXPeEYr4fHz9wP_IF4UeAUqXJZh4bxX9XdQ"
]

# 随机选择一个token
QWEN_AUTH_TOKEN = random.choice(QWEN_AUTH_TOKENS)
PORT = 58888  # 服务端绑定的端口
DEBUG_STATUS = False  # 是否输出debug信息
# =================================================

os.environ['FLASK_ENV'] = 'production'
warnings.filterwarnings("ignore", message=".*development server.*")

def debug_print(message):
    if DEBUG_STATUS:
        print(f"[DEBUG] {message}")

class QwenSimpleClient:
    def __init__(self, auth_token: str, base_url: str = "https://chat.qwen.ai"):
        self.auth_token = auth_token
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/json",
            "source": "web",
            "authorization": f"Bearer {self.auth_token}"
        })
        self.models_info = {}
        self._fetch_models()

    def _fetch_models(self):
        try:
            models_res = self.session.get(f"{self.base_url}/api/models")
            models_res.raise_for_status()
            self.models_info = {model['id']: model for model in models_res.json()['data']}
            debug_print(f"获取到 {len(self.models_info)} 个模型")
        except Exception as e:
            print(f"获取模型列表失败: {e}")

    def _get_qwen_model_id(self, openai_model: str) -> str:
        if openai_model in self.models_info:
            return openai_model
        else:
            default_model = "qwen3-235b-a22b"
            print(f"模型 '{openai_model}' 未找到，使用默认模型 '{default_model}'")
            return default_model

    def create_chat(self, model_id: str, title: str = "API临时对话") -> str:
        url = f"{self.base_url}/api/v2/chats/new"
        payload = {
            "title": title,
            "models": [model_id],
            "chat_mode": "normal",
            "chat_type": "t2t",
            "timestamp": int(time.time() * 1000)
        }
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            chat_id = response.json()['data']['id']
            debug_print(f"成功创建对话: {chat_id}")
            return chat_id
        except requests.exceptions.RequestException as e:
            debug_print(f"创建对话失败: {e}")
            raise

    def delete_chat(self, chat_id: str):
        url = f"{self.base_url}/api/v2/chats/{chat_id}"
        try:
            delete_session = requests.Session()
            delete_session.headers.update({
                "authorization": f"Bearer {self.auth_token}",
                "content-type": "application/json"
            })
            response = delete_session.delete(url)
            response.raise_for_status()
            res_data = response.json()
            if res_data.get('success', False):
                debug_print(f"成功删除对话: {chat_id}")
            else:
                debug_print(f"删除对话 {chat_id} 可能未成功: {res_data}")
        except requests.exceptions.RequestException as e:
            debug_print(f"删除对话失败 {chat_id} (可能已自动删除): {e}")
        except json.JSONDecodeError:
            debug_print(f"删除对话时无法解析 JSON 响应 {chat_id}")

    def get_sts_token(self, filename: str, filesize: int, filetype: str):
        """获取用于上传图片的STS令牌"""
        url = f"{self.base_url}/api/v2/files/getstsToken"
        # 为每个请求生成唯一的 x-request-id
        x_request_id = str(uuid.uuid4())
        headers = {
            "authorization": f"Bearer {self.auth_token}",
            "content-type": "application/json",
            "source": "web",
            "x-request-id": x_request_id
        }
        data = {
            "filename": filename,
            "filesize": filesize,
            "filetype": filetype
        }
        try:
            response = self.session.post(url, headers=headers, json=data)
            response.raise_for_status()
            res_data = response.json()
            if res_data.get("success") and "data" in res_data:
                debug_print(f"成功获取STS令牌 for {filename}")
                # 返回整个 data 字典，包含所有上传所需信息
                return res_data["data"]
            else:
                raise Exception(f"获取STS令牌失败: {res_data}")
        except requests.exceptions.RequestException as e:
            debug_print(f"获取STS令牌请求失败: {e}")
            raise

    def upload_image_via_sts(self, image_data: bytes, sts_info: dict):
        """使用STS信息上传图片到OSS"""
        # oss2.StsAuth 用于使用临时凭证
        auth = oss2.StsAuth(
            sts_info['access_key_id'],
            sts_info['access_key_secret'],
            sts_info['security_token']
        )
        # 注意：sts_info['endpoint'] 可能是 'oss-accelerate.aliyuncs.com'
        # 而 bucket.endpoint 通常需要完整的 'http://' 或 'https://' 前缀
        # 这里我们假设 sts_info['endpoint'] 是域名部分
        bucket_endpoint = f"https://{sts_info['endpoint']}"
        bucket = oss2.Bucket(auth, bucket_endpoint, sts_info['bucketname'])

        object_name = sts_info['file_path']
        
        # 上传文件对象 (BytesIO)
        result = bucket.put_object(object_name, image_data)
        
        if result.status == 200:
            debug_print(f"图片上传成功: {sts_info['file_url']}")
            return sts_info # 返回包含URL等信息的原始 sts_info
        else:
            raise Exception(f"图片上传到OSS失败, 状态码: {result.status}")

    def prepare_qwen_files(self, openai_messages: list):
        """解析OpenAI消息中的图片，准备Qwen的files数组"""
        qwen_files = []
        for message in openai_messages:
            if message.get("role") == "user" and isinstance(message.get("content"), list):
                for content_item in message["content"]:
                    if content_item.get("type") == "image_url":
                        image_url = content_item["image_url"]["url"]
                        # 解析 image_url
                        # 支持两种格式：
                        # 1. data:image/png;base64,...
                        # 2. https://... (由 /v1/uploads 返回的完整URL，需从中提取file_id)
                        
                        if image_url.startswith("data:image/"):
                            # Base64 数据 (客户端直接发送图片数据)
                            header, encoded = image_url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1] # e.g., image/png
                            file_extension = mime_type.split("/")[-1] # e.g., png
                            try:
                                image_data = base64.b64decode(encoded)
                                file_size = len(image_data)
                                # 生成一个临时文件名
                                file_hash = hashlib.md5(image_data[:100]).hexdigest()[:8]
                                temp_filename = f"temp_upload_{file_hash}.{file_extension}"

                                # 1. 获取 STS 令牌
                                sts_info = self.get_sts_token(temp_filename, file_size, "image")
                                # 2. 上传图片
                                upload_result = self.upload_image_via_sts(image_data, sts_info)
                                
                                # 3. 构造 Qwen 格式的 file 对象
                                qwen_file_obj = self._build_qwen_file_object(upload_result, temp_filename, file_size, mime_type)
                                qwen_files.append(qwen_file_obj)

                            except Exception as e:
                                print(f"处理Base64图片数据失败: {e}")
                                # 可以选择跳过此图片或返回错误
                        
                        elif image_url.startswith(("http://", "https://")):
                            # 假设这是由 /v1/uploads 返回的URL，需要从中提取信息
                            # 实际上，更稳健的方法是客户端在调用 /v1/chat/completions 时，
                            # 直接提供从 /v1/uploads 返回的 file_id 或完整对象。
                            # 这里我们简化处理，假设 URL 结构可以解析出 file_id
                            # 但这很脆弱。更好的方式是客户端传递 file_id。
                            
                            # 为了兼容性，我们假设客户端会传递一个特殊的标识符或结构
                            # 例如，一个包含 file_id 的 JSON 对象字符串化后作为 URL
                            # 或者，客户端直接在 image_url 中放入 file_id
                            # 这里我们采用一种更直接的假设：URL 参数中包含 file_id
                            # 但这需要与前端约定。
                            
                            # *** 更推荐的方式：***
                            # 客户端在调用 /v1/chat/completions 时，对于已上传的图片，
                            # `image_url` 字段直接使用从 `/v1/uploads` 返回的 `file_id`
                            # 例如: "image_url": {"url": "file-id-returned-by-uploads"}
                            
                            # 为了演示，我们假设 URL 最后一部分是 file_id
                            # (这在实际中可能不成立，需要根据实际情况调整)
                            try:
                                parsed_url = urlparse(image_url)
                                path_parts = parsed_url.path.strip("/").split("/")
                                if path_parts:
                                    file_id_from_url = path_parts[-1].split("_")[0] # 简单提取
                                    # 这里缺少了从 file_id 反查完整信息的步骤
                                    # 在实际应用中，你需要在 /v1/uploads 时将 file_id 和 info 存储起来
                                    # 例如在内存字典或临时缓存中
                                    # 为简化，我们这里无法直接从 file_id 构造 qwen_file_obj
                                    # 因此，此路径下的处理是不完整的，除非有额外的存储机制
                                    print("警告：通过URL解析file_id的方式不推荐且不完整。请在客户端传递完整的file对象或file_id并由服务端维护映射。")
                                    # 如果有存储机制，可以这样：
                                    # stored_info = self.get_stored_file_info(file_id_from_url)
                                    # if stored_info:
                                    #     qwen_files.append(stored_info)
                                    # else:
                                    #     print(f"未找到file_id {file_id_from_url} 对应的信息")
                                    
                            except Exception as e:
                                print(f"解析图片URL失败: {e}")
                        else:
                            print(f"不支持的图片URL格式: {image_url}")
        
        return qwen_files

    def _build_qwen_file_object(self, upload_result: dict, filename: str, filesize: int, content_type: str):
        """根据上传结果构建Qwen API需要的文件对象"""
        # upload_result 包含了 getstsToken 返回的所有 data 字段
        return {
            "type": "image",
            "file": {
                "created_at": int(time.time() * 1000),
                "data": {}, # 通常为空
                "filename": filename,
                "hash": None, # 通常由服务端计算
                "id": upload_result["file_id"],
                "user_id": "...", # 用户ID，如果需要可以从token解析或由服务端管理
                "meta": {
                    "name": filename,
                    "size": filesize,
                    "content_type": content_type
                },
                "update_at": int(time.time() * 1000)
            },
            "id": upload_result["file_id"],
            "url": upload_result["file_url"],
            "name": filename,
            "collection_name": "",
            "progress": 0,
            "status": "uploaded",
            "greenNet": "success", # 假设审核通过
            "size": filesize,
            "error": "",
            "itemId": str(uuid.uuid4()), # 临时ID
            "file_type": content_type,
            "showType": "image",
            "file_class": "vision",
            "uploadTaskId": str(uuid.uuid4()) # 临时任务ID
        }


    def chat_completions(self, openai_request: dict):
        model = openai_request.get("model", "qwen3")
        messages = openai_request.get("messages", [])
        stream = openai_request.get("stream", False)
        
        qwen_model_id = self._get_qwen_model_id(model)
        debug_print(f"处理请求: 模型={qwen_model_id}, 消息数={len(messages)}, 流式={stream}")

        # 处理图片上传
        qwen_files = self.prepare_qwen_files(messages)

        # 准备文本内容和最终消息列表
        final_messages = []
        for msg in messages:
            if isinstance(msg.get("content"), list):
                # 过滤掉图片内容，只保留文本
                text_content_parts = [item for item in msg["content"] if item.get("type") == "text"]
                text_content = "\n".join([item["text"] for item in text_content_parts])
                new_msg = msg.copy()
                new_msg["content"] = text_content
                final_messages.append(new_msg)
            else:
                final_messages.append(msg)

        # 拼接所有文本消息作为输入
        formatted_history = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in final_messages])
        if final_messages and final_messages[0]['role'] != "system":
            formatted_history = "system:\n\n" + formatted_history
        user_input = formatted_history

        chat_id = self.create_chat(qwen_model_id, title=f"API_对话_{int(time.time())}")
        debug_print(f"为请求创建新会话: {chat_id}")

        try:
            timestamp_ms = int(time.time() * 1000)
            payload = {
                "stream": True,
                "incremental_output": True,
                "chat_id": chat_id,
                "chat_mode": "normal",
                "model": qwen_model_id,
                "parent_id": None,
                "messages": [{
                    "fid": str(uuid.uuid4()),
                    "parentId": None,
                    "childrenIds": [str(uuid.uuid4())],
                    "role": "user",
                    "content": user_input,
                    "user_action": "chat",
                    "files": qwen_files, # 注入处理好的文件列表
                    "timestamp": timestamp_ms,
                    "models": [qwen_model_id],
                    "chat_type": "t2t",
                    "feature_config": {"output_schema": "phase"},
                    "extra": {"meta": {"subChatType": "t2t"}},
                    "sub_chat_type": "t2t",
                    "parent_id": None
                }],
                "timestamp": timestamp_ms
            }

            headers = { "x-accel-buffering": "no" }
            url = f"{self.base_url}/api/v2/chat/completions?chat_id={chat_id}"
            
            if stream:
                def generate():
                    try:
                        with self.session.post(url, json=payload, headers=headers, stream=True) as r:
                            r.raise_for_status()
                            finish_reason = "stop"
                            for line in r.iter_lines(decode_unicode=True):
                                if line.startswith("data: "):
                                    data_str = line[6:]
                                    if data_str.strip() == "[DONE]":
                                        final_chunk = {
                                            "id": f"chatcmpl-{chat_id[:10]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(time.time()),
                                            "model": model,
                                            "choices": [{ "index": 0, "delta": {}, "finish_reason": finish_reason }]
                                        }
                                        yield f"data: {json.dumps(final_chunk)}\n\n"
                                        yield "data: [DONE]\n\n"
                                        break
                                    try:
                                        data = json.loads(data_str)
                                        if "choices" in data and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            delta = choice.get("delta", {})
                                            content = delta.get("content", "")
                                            if content:
                                                openai_chunk = {
                                                    "id": f"chatcmpl-{chat_id[:10]}",
                                                    "object": "chat.completion.chunk",
                                                    "created": int(time.time()),
                                                    "model": model,
                                                    "choices": [{ "index": 0, "delta": {"content": content}, "finish_reason": None }]
                                                }
                                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                                            if delta.get("status") == "finished":
                                                finish_reason = delta.get("finish_reason", "stop")
                                    except json.JSONDecodeError:
                                        continue
                    except requests.exceptions.RequestException as e:
                        debug_print(f"流式请求失败: {e}")
                        error_chunk = {
                            "id": f"chatcmpl-error", "object": "chat.completion.chunk",
                            "created": int(time.time()), "model": model,
                            "choices": [{ "index": 0, "delta": {"content": f"Error during streaming: {str(e)}"}, "finish_reason": "error" }]
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                    finally:
                        debug_print(f"流式请求结束，准备删除会话: {chat_id}")
                        self.delete_chat(chat_id)
                return generate()

            else:
                response_text = ""
                finish_reason = "stop"
                usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                try:
                    with self.session.post(url, json=payload, headers=headers, stream=True) as r:
                        r.raise_for_status()
                        for line in r.iter_lines(decode_unicode=True):
                            if line.startswith("data: "): 
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if delta.get("content"):
                                            response_text += delta["content"]
                                        if "usage" in data:
                                            qwen_usage = data["usage"]
                                            usage_data = {
                                                "prompt_tokens": qwen_usage.get("input_tokens", 0),
                                                "completion_tokens": qwen_usage.get("output_tokens", 0),
                                                "total_tokens": qwen_usage.get("total_tokens", 0),
                                            }
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if delta.get("status") == "finished":
                                            finish_reason = delta.get("finish_reason", "stop")
                                except json.JSONDecodeError:
                                    continue
                    
                    openai_response = {
                        "id": f"chatcmpl-{chat_id[:10]}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "message": { "role": "assistant", "content": response_text },
                            "finish_reason": finish_reason
                        }],
                        "usage": usage_data
                    }
                    return jsonify(openai_response)
                finally:
                    debug_print(f"非流式请求结束，准备删除会话: {chat_id}")
                    self.delete_chat(chat_id)

        except requests.exceptions.RequestException as e:
            debug_print(f"聊天补全失败: {e}")
            self.delete_chat(chat_id)
            return jsonify({
                "error": {
                    "message": f"内部服务器错误: {str(e)}",
                    "type": "server_error",
                    "param": None,
                    "code": None
                }
            }), 500


# --- Flask 应用 ---
app = Flask(__name__)
CORS(app) 
qwen_client = QwenSimpleClient(auth_token=QWEN_AUTH_TOKEN)

# 用于存储上传文件信息的简单内存字典 (生产环境请使用数据库或缓存)
# 格式: {file_id: {file_info}}
uploaded_files_store = {}

@app.route('/v1/models', methods=['GET'])
def list_models():
    try:
        openai_models = []
        for model_id, model_info in qwen_client.models_info.items():
            openai_models.append({
                "id": model_info['info']['id'],
                "object": "model",
                "created": model_info['info']['created_at'],
                "owned_by": model_info['owned_by']
            })
        return jsonify({"object": "list", "data": openai_models})
    except Exception as e:
        print(f"列出模型时出错: {e}")
        return jsonify({
            "error": { "message": f"获取模型列表失败: {e}", "type": "server_error", "param": None, "code": None }
        }), 500

@app.route('/v1/uploads', methods=['POST'])
def upload_file():
    """处理文件上传请求"""
    data = request.get_json()
    if not data:
        return jsonify({"error": {"message": "请求体无效", "type": "invalid_request_error"}}), 400

    # 期望客户端发送 base64 编码的图片数据
    # 例如: {"file_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA..."}
    file_data_url = data.get("file_data")
    
    if not file_data_url or not file_data_url.startswith("data:image/"):
        return jsonify({"error": {"message": "缺少有效的 base64 图片数据 (file_data)", "type": "invalid_request_error"}}), 400

    try:
        header, encoded = file_data_url.split(",", 1)
        mime_type = header.split(";")[0].split(":")[1]
        file_extension = mime_type.split("/")[-1]
        
        image_data = base64.b64decode(encoded)
        file_size = len(image_data)
        file_hash = hashlib.md5(image_data[:100]).hexdigest()[:8]
        temp_filename = f"uploaded_via_api_{file_hash}.{file_extension}"

        # 1. 获取 STS 令牌
        sts_info = qwen_client.get_sts_token(temp_filename, file_size, "image")
        
        # 2. 上传图片
        upload_result = qwen_client.upload_image_via_sts(image_data, sts_info)
        
        # 3. 存储文件信息 (简化版内存存储)
        file_id = upload_result["file_id"]
        file_info_to_store = {
            "file_id": file_id,
            "url": upload_result["file_url"],
            "name": temp_filename,
            "size": file_size,
            "type": mime_type
        }
        uploaded_files_store[file_id] = file_info_to_store
        
        # 4. 返回成功信息，包含 file_id，供后续 /v1/chat/completions 使用
        return jsonify({
            "id": file_id,
            "object": "file",
            "bytes": file_size,
            "created_at": int(time.time()),
            "filename": temp_filename,
            "purpose": "vision", # 或其他用途
            "status": "uploaded",
            "url": upload_result["file_url"] # 也可以只返回 file_id
        }), 200

    except Exception as e:
        print(f"文件上传处理失败: {e}")
        return jsonify({
            "error": { "message": f"文件上传失败: {str(e)}", "type": "server_error", "param": None, "code": None }
        }), 500


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    openai_request = request.get_json()
    if not openai_request:
        return jsonify({
            "error": { "message": "请求体中 JSON 无效", "type": "invalid_request_error", "param": None, "code": None }
        }), 400

    # --- 修改点：增强对图片消息的处理 ---
    messages = openai_request.get("messages", [])
    processed_messages = []
    for message in messages:
        if message.get("role") == "user" and isinstance(message.get("content"), list):
            processed_content = []
            for item in message["content"]:
                if item.get("type") == "text":
                    processed_content.append(item)
                elif item.get("type") == "image_url":
                    image_url = item["image_url"]["url"]
                    # --- 关键逻辑：处理图片 ---
                    # 假设客户端在 image_url 中直接提供了从 /v1/uploads 返回的 file_id
                    if image_url in uploaded_files_store:
                        # 如果 URL 看起来像一个 file_id (简单检查)
                        # 在实际应用中，你可能需要更严格的验证
                        stored_file_info = uploaded_files_store[image_url]
                        # 我们不需要在这里做太多，因为 prepare_qwen_files 会处理
                        # 但我们可以记录或转换格式
                        # 为了兼容性，我们保持 image_url 不变，让 prepare_qwen_files 处理
                        processed_content.append(item)
                    else:
                        # 如果不是已知的 file_id，则假定是 base64 data URL
                        # 并在 prepare_qwen_files 中处理上传
                         processed_content.append(item)
                else:
                    # 未知类型，跳过或原样保留？
                    # 为了安全，最好跳过未知类型
                    print(f"警告：消息中包含未知内容类型 {item.get('type')}, 已跳过。")
            new_message = message.copy()
            new_message["content"] = processed_content
            processed_messages.append(new_message)
        else:
            processed_messages.append(message)
    
    # 更新请求中的 messages
    openai_request["messages"] = processed_messages
    # --- 修改点结束 ---

    stream = openai_request.get("stream", False)
    
    try:
        result = qwen_client.chat_completions(openai_request)
        if stream:
            return Response(stream_with_context(result), content_type='text/event-stream')
        else:
            return result
    except Exception as e:
        debug_print(f"处理聊天补全请求时发生未预期错误: {e}")
        return jsonify({
            "error": { "message": f"内部服务器错误: {str(e)}", "type": "server_error", "param": None, "code": None }
        }), 500

@app.route('/v1/chats/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    try:
        qwen_client.delete_chat(chat_id)
        return jsonify({"message": f"尝试删除会话 {chat_id}", "success": True})
    except Exception as e:
        debug_print(f"删除会话时发生错误: {e}")
        return jsonify({
            "error": { "message": f"删除会话失败: {str(e)}", "type": "server_error", "param": None, "code": None }
        }), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "message": "简化版千问 (Qwen) OpenAI API 代理正在运行 (支持图片上传)。",
        "docs": "https://platform.openai.com/docs/api-reference/chat"
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # 显示选择的token信息（只显示前8位和后8位，保护隐私）
    token_index = QWEN_AUTH_TOKENS.index(QWEN_AUTH_TOKEN) + 1
    token_preview = f"{QWEN_AUTH_TOKEN[:8]}...{QWEN_AUTH_TOKEN[-8:]}"
    
    print(f"正在启动简化版服务器于端口 {PORT}...")
    print(f"Debug模式: {'开启' if DEBUG_STATUS else '关闭'}")
    print(f"负载均衡: 使用Token #{token_index}/{len(QWEN_AUTH_TOKENS)} ({token_preview})")
    app.run(host='0.0.0.0', port=PORT, debug=False)
