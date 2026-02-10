FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-noto-cjk \
        fonts-nanum \
        fonts-noto-core \
        fonts-noto-unhinted \
        fonts-noto-extra \
        fonts-noto-ui-core \
        fonts-noto-ui-extra \
        fontconfig \
        wget \
    && fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements.txt from backend root
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend app directory
COPY app /app/app

CMD ["python", "-m", "app.workers.process.main"]



