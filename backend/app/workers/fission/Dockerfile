FROM python:3.11-slim

# 设置非交互式安装，避免debconf错误
ENV DEBIAN_FRONTEND=noninteractive

# 安装FFmpeg和Whisper依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# 先安装 PyTorch CPU 版本（减小镜像大小）
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 复制requirements并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建模块结构: app/workers/fission/
RUN mkdir -p app/workers/fission
COPY main.py app/workers/fission/
RUN touch app/__init__.py app/workers/__init__.py app/workers/fission/__init__.py

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV GCP_PROJECT_ID=fleet-blend-469520-n7
ENV FIRESTORE_PROJECT_ID=fleet-blend-469520-n7
ENV PYTHONPATH=/workspace

# 使用 python 作为入口，参数由 Cloud Run Job 传递
ENTRYPOINT ["python"]

