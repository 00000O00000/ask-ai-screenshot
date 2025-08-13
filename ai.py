# simplified_qwen_proxy.py
# pip install requests flask flask-cors

import requests
import uuid
import time
import json
import os
import warnings
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

# ==================== 配置区域 ====================
QWEN_AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImMzZTc2MjVlLWZkMzQtNGRjYS1iYmM3LWEzY2I4ZDc5NDhlMSIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzUzNTk1ODA2LCJleHAiOjE3NTc2Njc1NzV9.dkSpP_zHbMNyE88zi3MTpWyApYApelNPlYXAbMVFA8M"
PORT = 58888  # 服务端绑定的端口
DEBUG_STATUS = False  # 是否输出debug信息
# =================================================

os.environ['FLASK_ENV'] = 'production'
warnings.filterwarnings("ignore", message=".*development server.*")

def debug_print(message):
    """根据DEBUG_STATUS决定是否输出debug信息"""
    if DEBUG_STATUS:
        print(f"[DEBUG] {message}")

class QwenSimpleClient:
    """
    用于与 chat.qwen.ai API 交互的简化客户端。
    每次交互都创建新会话，处理完后自动删除。
    """
    def __init__(self, auth_token: str, base_url: str = "https://chat.qwen.ai"):
        self.auth_token = auth_token
        self.base_url = base_url.rstrip('/') # 确保 base_url 末尾没有斜杠
        self.session = requests.Session()
        # 初始化时设置基本请求头
        self.session.headers.update({
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/json",
            "source": "web",
            "authorization": f"Bearer {self.auth_token}"
        })
        self.models_info = {}
        self._fetch_models()

    def _fetch_models(self):
        """获取可用模型列表"""
        try:
            models_res = self.session.get(f"{self.base_url}/api/models")
            models_res.raise_for_status()
            self.models_info = {model['id']: model for model in models_res.json()['data']}
            debug_print(f"获取到 {len(self.models_info)} 个模型")
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            # 即使失败也继续，使用默认模型

    def _get_qwen_model_id(self, openai_model: str) -> str:
        """简化模型选择：检查模型是否存在，否则使用默认模型"""
        if openai_model in self.models_info:
            return openai_model
        else:
            default_model = "qwen3-235b-a22b"
            print(f"模型 '{openai_model}' 未找到，使用默认模型 '{default_model}'")
            return default_model

    def create_chat(self, model_id: str, title: str = "API临时对话") -> str:
        """创建一个新的对话"""
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
        """删除一个对话"""
        url = f"{self.base_url}/api/v2/chats/{chat_id}"
        try:
            # 使用不同的 session 或不携带特定 headers 来避免潜在问题
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
            # 删除失败通常不是致命错误，仅记录
            debug_print(f"删除对话失败 {chat_id} (可能已自动删除): {e}")
        except json.JSONDecodeError:
            debug_print(f"删除对话时无法解析 JSON 响应 {chat_id}")

    def chat_completions(self, openai_request: dict):
        """
        执行聊天补全，模拟 OpenAI API。
        返回流式生成器或非流式 JSON 响应。
        """
        # 解析 OpenAI 请求
        model = openai_request.get("model", "qwen3")
        messages = openai_request.get("messages", [])
        stream = openai_request.get("stream", False)
        
        # 映射模型
        qwen_model_id = self._get_qwen_model_id(model)
        debug_print(f"处理请求: 模型={qwen_model_id}, 消息数={len(messages)}, 流式={stream}")

        # 拼接所有消息作为输入
        formatted_history = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        if messages and messages[0]['role'] != "system":
            formatted_history = "system:\n\n" + formatted_history
        user_input = formatted_history

        # 创建新会话
        chat_id = self.create_chat(qwen_model_id, title=f"API_对话_{int(time.time())}")
        debug_print(f"为请求创建新会话: {chat_id}")

        try:
            # 准备请求负载
            timestamp_ms = int(time.time() * 1000)
            payload = {
                "stream": True, # 始终使用流式以获取实时数据
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
                    "files": [],
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

            headers = {
                "x-accel-buffering": "no" # 对于流式响应很重要
            }

            url = f"{self.base_url}/api/v2/chat/completions?chat_id={chat_id}"
            
            if stream:
                # 流式请求
                def generate():
                    try:
                        with self.session.post(url, json=payload, headers=headers, stream=True) as r:
                            r.raise_for_status()
                            finish_reason = "stop"
                            assistant_content = ""  # 用于累积assistant回复内容

                            for line in r.iter_lines(decode_unicode=True):
                                if line.startswith("data: "):
                                    data_str = line[6:]  # 移除 'data: '
                                    if data_str.strip() == "[DONE]":
                                        # 发送最终的 done 消息块，包含 finish_reason
                                        final_chunk = {
                                            "id": f"chatcmpl-{chat_id[:10]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(time.time()),
                                            "model": model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {}, 
                                                "finish_reason": finish_reason
                                            }]
                                        }
                                        yield f"data: {json.dumps(final_chunk)}\n\n"
                                        yield "data: [DONE]\n\n"
                                        break
                                    try:
                                        data = json.loads(data_str)
                                        
                                        # 处理 choices 数据
                                        if "choices" in data and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            delta = choice.get("delta", {})
                                            content = delta.get("content", "")

                                            if content:
                                                assistant_content += content
                                                openai_chunk = {
                                                    "id": f"chatcmpl-{chat_id[:10]}",
                                                    "object": "chat.completion.chunk",
                                                    "created": int(time.time()),
                                                    "model": model,
                                                    "choices": [{
                                                        "index": 0,
                                                        "delta": {"content": content},
                                                        "finish_reason": None
                                                    }]
                                                }
                                                yield f"data: {json.dumps(openai_chunk)}\n\n"

                                            # 检查结束信号
                                            if delta.get("status") == "finished":
                                                finish_reason = delta.get("finish_reason", "stop")

                                    except json.JSONDecodeError:
                                        continue
                    except requests.exceptions.RequestException as e:
                        debug_print(f"流式请求失败: {e}")
                        error_chunk = {
                            "id": f"chatcmpl-error",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": f"Error during streaming: {str(e)}"},
                                "finish_reason": "error"
                            }]
                        }
                        yield f"data: {json.dumps(error_chunk)}\n\n"
                    finally:
                        # 请求结束后自动删除会话
                        debug_print(f"流式请求结束，准备删除会话: {chat_id}")
                        self.delete_chat(chat_id)

                return generate()

            else:
                # 非流式请求: 聚合流式响应
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
                                        
                                        # 收集 usage 信息
                                        if "usage" in data:
                                            qwen_usage = data["usage"]
                                            usage_data = {
                                                "prompt_tokens": qwen_usage.get("input_tokens", 0),
                                                "completion_tokens": qwen_usage.get("output_tokens", 0),
                                                "total_tokens": qwen_usage.get("total_tokens", 0),
                                            }
                                    
                                    # 检查结束信号
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if delta.get("status") == "finished":
                                            finish_reason = delta.get("finish_reason", "stop")
                                        
                                except json.JSONDecodeError:
                                    continue
                    
                    # 构造非流式的 OpenAI 响应
                    openai_response = {
                        "id": f"chatcmpl-{chat_id[:10]}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "finish_reason": finish_reason
                        }],
                        "usage": usage_data
                    }
                    return jsonify(openai_response)
                finally:
                     # 请求结束后自动删除会话
                    debug_print(f"非流式请求结束，准备删除会话: {chat_id}")
                    self.delete_chat(chat_id)

        except requests.exceptions.RequestException as e:
            debug_print(f"聊天补全失败: {e}")
            # 确保即使出错也尝试删除会话
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

# 初始化客户端
qwen_client = QwenSimpleClient(auth_token=QWEN_AUTH_TOKEN)

@app.route('/v1/models', methods=['GET'])
def list_models():
    """列出可用模型 (模拟 OpenAI API)"""
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
            "error": {
                "message": f"获取模型列表失败: {e}",
                "type": "server_error",
                "param": None,
                "code": None
            }
        }), 500

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """处理 OpenAI 兼容的聊天补全请求"""
    openai_request = request.get_json()
    if not openai_request:
        return jsonify({
            "error": {
                "message": "请求体中 JSON 无效",
                "type": "invalid_request_error",
                "param": None,
                "code": None
            }
        }), 400

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
            "error": {
                "message": f"内部服务器错误: {str(e)}",
                "type": "server_error",
                "param": None,
                "code": None
            }
        }), 500

# 保留删除端点，但逻辑简化
@app.route('/v1/chats/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    """删除指定的对话"""
    try:
        # 直接调用客户端的删除方法
        qwen_client.delete_chat(chat_id)
        # 由于会话会自动删除，这里总是返回成功
        return jsonify({"message": f"尝试删除会话 {chat_id}", "success": True})
    except Exception as e:
        debug_print(f"删除会话时发生错误: {e}")
        return jsonify({
            "error": {
                "message": f"删除会话失败: {str(e)}",
                "type": "server_error",
                "param": None,
                "code": None
            }
        }), 500

@app.route('/', methods=['GET'])
def index():
    """根路径，返回 API 信息"""
    return jsonify({
        "message": "千问 (Qwen) OpenAI API 代理正在运行。",
        "docs": "https://platform.openai.com/docs/api-reference/chat"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    print(f"正在启动服务器于端口 {PORT}...")
    print(f"Debug模式: {'开启' if DEBUG_STATUS else '关闭'}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
