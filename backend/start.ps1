# 后端服务启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动 AutoGrowth 后端服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量
$env:GOOGLE_APPLICATION_CREDENTIALS = "fleet-blend-469520-n7-23b7c649292b.json"

Write-Host "🚀 启动后端服务..." -ForegroundColor Green
Write-Host ""
Write-Host "服务地址: http://localhost:8000" -ForegroundColor Yellow
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Red
Write-Host ""

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

