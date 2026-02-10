#!/bin/bash
set -e

echo "🚀 启动前后端服务进行本地测试"
echo ""

# 检查后端环境
if [ ! -d "backend/venv" ]; then
    echo "❌ 后端虚拟环境不存在，请先运行: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠️  前端依赖未安装，正在安装..."
    cd frontend && npm install && cd ..
fi

# 检查环境变量
if [ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
    echo "⚠️  未设置 GOOGLE_APPLICATION_CREDENTIALS，请确保已设置"
fi

echo "✅ 环境检查完成"
echo ""
echo "📝 启动说明："
echo "  1. 后端将在 http://localhost:8000 启动"
echo "  2. 前端将在 http://localhost:3001 启动"
echo "  3. 按 Ctrl+C 停止服务"
echo ""

# 启动后端（后台）
echo "🔧 启动后端服务..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"
echo "  日志文件: backend.log"

# 等待后端启动
sleep 3

# 启动前端（前台，方便查看日志）
echo "🎨 启动前端服务..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

echo ""
echo "✅ 服务已启动"
echo ""
echo "📋 进程管理："
echo "  停止后端: kill $BACKEND_PID"
echo "  停止前端: kill $FRONTEND_PID"
echo "  查看后端日志: tail -f backend.log"
echo ""

# 等待用户中断
wait $FRONTEND_PID
