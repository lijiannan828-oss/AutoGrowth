@echo off
chcp 65001 >nul
echo ========================================
echo 正在启动后端服务器...
echo ========================================
echo.

cd /d "d:\AutoGrowth-main (1)\AutoGrowth-main\backend"

echo [1/3] 检查 Python 环境
python --version
if errorlevel 1 (
    echo 错误: Python 未安装或未添加到 PATH
    pause
    exit /b 1
)
echo.

echo [2/3] 检查环境变量配置
if not exist ".env" (
    echo 警告: .env 文件不存在
    pause
)
echo.

echo [3/3] 启动 Uvicorn 服务器
echo 后端地址: http://localhost:8001
echo API 文档: http://localhost:8001/docs
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0

pause

