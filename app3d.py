# server.py

import asyncio
import json
import logging
import os
from typing import List

import openai
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi_standalone_docs import StandaloneDocs
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
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
        self.lock = asyncio.Lock()  # 用于线程安全地管理连接

    async def connect(self, websocket: WebSocket):
        """
        建立连接
        """
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
        print(f"新连接建立: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        """
        断开连接
        """
        async with self.lock:
            self.active_connections.remove(websocket)
        print(f"连接断开: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        发送个人消息
        """
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """
        广播消息给所有连接的客户端
        """
        async with self.lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"发送消息失败给 {connection.client}: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点，处理客户端连接和消息
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"接收到来自 {websocket.client} 的消息: {data}")
            # 这里可以根据需要处理接收到的消息
            # 例如，可以回显消息或进行其他逻辑处理
            # 例如，回显消息给客户端：
            # await manager.send_personal_message(f"你说: {data}", websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        await manager.disconnect(websocket)
        print(f"连接异常: {e}")

# 定义消息模型
class Message(BaseModel):
    type: str
    content: str

@app.post("/send_message/")
async def send_message(message: Message):
    """
    HTTP POST端点，主动发送消息给所有连接的WebSocket客户端
    """
    if not message.content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    # 构造消息，例如添加前缀
    await manager.broadcast(json.dumps(message.dict()))
    return {"message": "消息已发送给所有客户端"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=38024)