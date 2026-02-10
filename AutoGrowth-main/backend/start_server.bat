@echo off
echo ========================================
echo 启动 AutoGrowth 后端服务器
echo ========================================
echo.

set GOOGLE_APPLICATION_CREDENTIALS=d:\AutoGrowth-main (1)\AutoGrowth-main\backend\fleet-blend-469520-n7-23b7c649292b.json

echo 环境变量已设置
echo GOOGLE_APPLICATION_CREDENTIALS = %GOOGLE_APPLICATION_CREDENTIALS%
echo.

echo 启动 Uvicorn 服务器...
echo 访问地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

cd /d "d:\AutoGrowth-main (1)\AutoGrowth-main\backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause

