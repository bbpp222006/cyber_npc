# server.py

import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional

import httpx
import openai
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi_standalone_docs import StandaloneDocs
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp  # Use aiohttp for asynchronous HTTP requests
import uvicorn
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# 初始化 FastAPI 应用
app = FastAPI()

StandaloneDocs(app=app)
# 添加 CORS 中间件（根据需要调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 根据需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """
    管理WebSocket连接的类
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connections_lock = asyncio.Lock()  # 用于线程安全地管理连接
        self.send_lock = asyncio.Lock()  # 确保send_text_audio操作的互斥
        self.playback_complete_event = asyncio.Event()  # 等待播放完成的事件

    async def connect(self, websocket: WebSocket):
        """
        建立连接
        """
        await websocket.accept()
        async with self.connections_lock:
            self.active_connections.append(websocket)
        logger.info(f"新连接建立: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        """
        断开连接
        """
        async with self.connections_lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"连接断开: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        发送个人消息
        """
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """
        广播消息给所有连接的客户端
        """
        async with self.connections_lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"发送消息失败给 {connection.client}: {e}")

    async def wait_for_playback_complete(self, timeout: Optional[float] = None) -> bool:
        """
        等待播放完成事件被设置
        """
        try:
            await asyncio.wait_for(self.playback_complete_event.wait(), timeout)
            self.playback_complete_event.clear()
            return True
        except asyncio.TimeoutError:
            logger.error("等待播放完成超时")
            return False

    def playback_complete(self):
        """
        设置播放完成事件
        """
        self.playback_complete_event.set()



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点，处理客户端连接和消息
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"接收到来自 {websocket.client} 的消息: {message}")
            if message.get("type") == "playback_complete":
                # 设置播放完成事件
                manager.playback_complete()
            # 这里可以根据需要处理接收到的消息
            # 例如，可以回显消息或进行其他逻辑处理
            # 例如，回显消息给客户端：
            # await manager.send_personal_message(f"你说: {data}", websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        await manager.disconnect(websocket)
        logger.error(f"连接异常: {e}")


# Get TTS audio data asynchronously using httpx
async def get_tts_audio(text: str) -> Optional[Dict[str, bytes]]:
    """
    异步调用TTS服务以获取音频数据并返回为bytes
    """
    url = "http://127.0.0.1:7860/tts/"
    payload = {
        "text": text,
        "streaming": "false"
    }

    headers = {
        "Content-Type": "application/json"
    }
    logger.info(f"请求TTS: {payload}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload,timeout=30)
            if response.status_code == 200:
                audio_data = response.content
                logger.info("成功接收到TTS音频数据")
                return {
                    "audio_data": audio_data,
                    "text": text
                }
            else:
                logger.error(f"TTS请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"TTS请求异常: {e}")
            return None

# # Get TTS audio data asynchronously
# async def sentence2audio(text: str) -> List[Optional[bytes]]:
#    # 按句子单位切割回复内容并处理
#     sentences = re.split(r'([、,，。?？!！；;：:…]+)', text)
#     # 每两个拼接
#     sentences = [sentences[i] + sentences[i+1] for i in range(0, len(sentences)-1, 2)]

#     # 创建10个任务
#     tasks = [asyncio.create_task(get_tts_audio( sentence))  for sentence in sentences if sentence]
    
#     # 按任务提交的顺序等待每个任务完成，并将结果放入队列
#     for i, t in enumerate(tasks, start=1):
#         result = await t  # 等待第i个任务完成
#         await queue.put(result)  # 将结果放入队列
#         print(f"任务 {i} 的结果已放入队列")
#     await queue.put("Done")

async def audio2web():
    """
    b模块：按顺序等待并处理队列中的结果。
    """
    logger.info("开始处理队列")
    async with manager.send_lock:
        while True:
            result = await queue.get()  # 等待队列中的下一个结果
            if result == "Done":
                logger.info("队列处理完成")
                continue
            

            result = await result
            if result is None:
                logger.error("队列中存在None值")
                continue
            # 构造text_audio消息
            audio_base64 = base64.b64encode(result["audio_data"]).decode('utf-8')
            sentence = result["text"]
            logger.info(f"从队列中获取结果: {sentence}")
            emotion = get_emotion(sentence)
            
            message = {
                "type": "text_audio",
                "content": sentence,
                "data": audio_base64,
                "tag": emotion
            }
            # 广播消息
            await manager.broadcast(json.dumps(message))
            logger.info(f"text_audio消息已发送: {sentence}，等待播放完成")
            # 等待播放完成，设定一个超时时间（例如 30 秒）
            playback_completed = await manager.wait_for_playback_complete(timeout=30.0)
            if not playback_completed:
                raise HTTPException(status_code=500, detail="等待播放完成超时")

            logger.info(f"text_audio消息已发送: {sentence}，已完成播放")

# @app.post("/send_text_audio/")
# async def send_text_audio(request: str):
#     """
#     HTTP POST端点，主动发送text_audio消息给所有连接的WebSocket客户端
#     """
#     text = request.strip()
#     if not text:
#         raise HTTPException(status_code=400, detail="文本内容不能为空")

#     producer_task = asyncio.create_task(sentence2audio(text))

#     await producer_task

#     return {"message": "text_audio消息已发送给所有客户端"}


@app.post("/chat_openai/")
async def chat_openai(user_input: str="你好"):
    


    response = openai_client.chat.completions.create(model= "qwen2.5:32b",
                                                    stream=True,
                                                    messages=[
                                                        {"role": "system",
                                                        "content": "你是一个专业的虚拟主播，能够完美的模仿人类的语气和情感，并且能够熟练的对弹幕进行回应。"},
                                                         {"role": "user", "content": f"弹幕：{user_input}"}])
    current_sentence = ""
    for chunk in response:
        token=chunk.choices[0].delta.content
        logger.info(rf"当前token: {token}")

        
        current_sentence += token
        if current_sentence.endswith(("、", "，", "。", "?", "？", "!", "！", "；", ";", "：", ":", "…", "\n")):
            current_sentence = current_sentence.strip()
            if current_sentence:
                logger.info(f"当前句子: {current_sentence}")
                producer_task = asyncio.create_task(get_tts_audio(current_sentence))
                await queue.put(producer_task)
                current_sentence = ""
    await queue.put("Done")

    return {"message": "text_audio消息已发送给所有客户端"}


    # readonly Happy: "happy";
    # readonly Angry: "angry";
    # readonly Sad: "sad";
    # readonly Relaxed: "relaxed";
    # readonly LookUp: "lookUp";
    # readonly Surprised: "surprised";
    # readonly Neutral: "neutral";
def get_emotion(sentence):
    emotion_result = "neutral"
    logger.info(f"当前句子: {sentence}->>正在判断情感")
    emotion_result = "neutral"
    logger.info(f"当前句子: {sentence}->>{emotion_result}")
    return emotion_result


@app.on_event("startup")
async def startup_event():
    logger.info("应用启动，启动消费者任务")
    app.state.consumer_task = asyncio.create_task(audio2web())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用关闭，取消消费者任务")
    consumer_task = app.state.consumer_task
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("消费者任务已成功取消")

if __name__ == "__main__":
    
    manager = ConnectionManager()

    queue = asyncio.Queue(maxsize=1)

    """
    openai接口
    """
    openai_client = openai.OpenAI(
            api_key="aaa",
            base_url="http://192.10.50.139:11434/v1",
        )

    uvicorn.run(app, host="0.0.0.0", port=38024)
