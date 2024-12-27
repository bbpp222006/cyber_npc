# app.py
from enum import Enum
from typing import List
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi_standalone_docs import StandaloneDocs

from pydantic import BaseModel

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

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 定义一个类来管理 WebSocket 连接
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"发送消息失败: {e}")

manager = ConnectionManager()

model_name = "丘丘人"

model_path = os.path.join("static", "models", model_name)
expression_path = os.path.join(model_path, "expressions")
expression_names  = [f.split(".")[0] for f in os.listdir(expression_path) if f.endswith(".exp3.json")]

# 动态生成 Enum 类
ExpressionEnum = Enum('ExpressionEnum', {name: name for name in expression_names})

class ExpressionNameModel(BaseModel):
    expression_name: ExpressionEnum

@app.post("/trigger_expression")
async def trigger_expression(expression: ExpressionNameModel):
    expression_name = expression.expression_name.value  # 获取枚举的值

    # 检查表情名称是否存在
    if expression_name not in expression_names:
        raise HTTPException(status_code=400, detail="无效的表情名称。")

    # 向所有 WebSocket 客户端广播，携带表情名称
    await manager.broadcast(f"set_expression:{expression_name}")
    return JSONResponse(content={"message": f"表情 {expression_name} 已触发。"})

@app.post("/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    # 检查文件类型是否为音频
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="仅支持音频文件上传。")

    # 生成唯一的文件名以避免冲突
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"tmp{file_extension}"
    file_path = os.path.join("static/uploads", unique_filename)

    # 保存文件
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 获取文件的 URL
    file_url = f"/static/uploads/{unique_filename}"

    # 向所有 WebSocket 客户端广播，携带音频文件的 URL
    await manager.broadcast(f"play_audio:{file_url}")
    return JSONResponse(content={"message": "音频文件已上传并触发播放。", "file_url": file_url})


@app.get("/list_expression")
async def list_expression():

    return JSONResponse(content={"expressions": expression_names})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 查询目录下结尾为 .model.json 或 .model3.json 的文件
    for file_name in os.listdir(model_path):
        if file_name.endswith(".model.json") or file_name.endswith(".model3.json"):
            model_url = f"/static/models/{model_name}/{file_name}"
            break
    return templates.TemplateResponse("index.html", {"request": request, "model_url": model_url})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 这里可以处理来自客户端的消息（如果需要）
            print(f"收到来自客户端的消息: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

    
    



