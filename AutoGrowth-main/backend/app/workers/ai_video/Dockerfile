FROM python:3.11-slim

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装 FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# 复制 requirements 并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建模块结构: app/workers/ai_video/
RUN mkdir -p app/workers/ai_video
COPY main.py app/workers/ai_video/
RUN touch app/__init__.py app/workers/__init__.py app/workers/ai_video/__init__.py

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV GCP_PROJECT_ID=fleet-blend-469520-n7
ENV FIRESTORE_PROJECT_ID=fleet-blend-469520-n7
ENV PYTHONPATH=/workspace

# 使用 python 作为入口，参数由 Cloud Run Job 传递
ENTRYPOINT ["python"]

