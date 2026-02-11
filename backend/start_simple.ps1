# 简化的后端启动脚本
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AutoGrowth 后端服务启动" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python版本
Write-Host "检查Python版本..." -ForegroundColor Yellow
python --version

Write-Host ""
Write-Host "启动后端服务 (端口: 8000)..." -ForegroundColor Green
Write-Host "访问 API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "健康检查: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动uvicorn
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

