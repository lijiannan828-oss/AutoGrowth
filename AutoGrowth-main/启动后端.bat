@echo off
echo ========================================
echo 启动后端服务器 (Backend Server)
echo ========================================
echo.

cd /d "%~dp0backend"

echo 检查 Python 环境...
python --version
echo.

echo 启动 Uvicorn 服务器...
echo 后端地址: http://localhost:8001
echo API 文档: http://localhost:8001/docs
echo.

python -m uvicorn app.main:app --reload --port 8001

pause

