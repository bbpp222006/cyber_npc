# 使用官方的 Python 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录的所有文件到容器中的 /app 目录
COPY . /app

# 安装必要的 Python 库
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 公开端口
EXPOSE 8000

# 启动 FastAPI 应用，使用 Uvicorn 作为服务器
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
