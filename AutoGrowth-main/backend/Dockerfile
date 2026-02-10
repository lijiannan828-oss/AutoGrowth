# syntax=docker/dockerfile:1.4
# Multi-stage build for optimized image size
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by all workers (transfer/process/zip)
# Include all Noto fonts for multi-language subtitle rendering (Thai, Hindi, Arabic, Cyrillic, etc.)
# Note: fonts-noto-extra and fonts-noto-ui-extra contain complete font sets including full Thai and Hindi character coverage
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --no-install-recommends -y \
    ffmpeg \
    fonts-noto-cjk \
    fonts-nanum \
    fonts-noto-core \
    fonts-noto-unhinted \
    fonts-noto-extra \
    fonts-noto-ui-extra \
    fontconfig \
    rclone \
    ca-certificates \
    curl \
    wget \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app ./app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the application - use PORT env variable for Cloud Run compatibility
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
