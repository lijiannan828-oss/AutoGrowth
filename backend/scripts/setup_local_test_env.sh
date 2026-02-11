#!/bin/bash
# 设置本地测试环境

set -e

echo "设置本地测试环境..."
echo "=" * 60

# 1. 检查虚拟环境
if [ ! -d "backend/venv" ]; then
    echo "创建虚拟环境..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# 2. 激活虚拟环境
echo "激活虚拟环境..."
source backend/venv/bin/activate

# 3. 安装依赖
echo "安装依赖..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt
pip install google-cloud-run  # 确保安装了 google-cloud-run
cd ..

# 4. 检查 GCP 认证
echo ""
echo "检查 GCP 认证..."
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠️  GOOGLE_APPLICATION_CREDENTIALS 未设置"
    echo ""
    echo "请选择以下方式之一设置认证:"
    echo ""
    echo "方式 1: 使用服务账号密钥文件"
    echo "  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json"
    echo ""
    echo "方式 2: 使用 gcloud 默认认证"
    echo "  gcloud auth application-default login"
    echo ""
    echo "方式 3: 使用项目中的服务账号密钥（如果存在）"
    if [ -f "backend/secrets/sa-run-prod-key.json" ]; then
        echo "  发现密钥文件: backend/secrets/sa-run-prod-key.json"
        echo "  export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/backend/secrets/sa-run-prod-key.json"
    fi
else
    echo "✅ GOOGLE_APPLICATION_CREDENTIALS 已设置: $GOOGLE_APPLICATION_CREDENTIALS"
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo "✅ 密钥文件存在"
    else
        echo "⚠️  密钥文件不存在: $GOOGLE_APPLICATION_CREDENTIALS"
    fi
fi

echo ""
echo "✅ 环境设置完成"
echo ""
echo "运行测试:"
echo "  python -m backend.scripts.test_concurrency_service_local [job_id]"
