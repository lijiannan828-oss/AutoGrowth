# 启动后端服务器
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动 AutoGrowth 后端服务器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量
$env:GOOGLE_APPLICATION_CREDENTIALS = "d:\AutoGrowth-main (1)\AutoGrowth-main\backend\fleet-blend-469520-n7-23b7c649292b.json"

Write-Host "✓ 环境变量已设置" -ForegroundColor Green
Write-Host "  GOOGLE_APPLICATION_CREDENTIALS = $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Gray
Write-Host ""

# 检查端口占用
Write-Host "检查端口 8000..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "⚠ 端口 8000 已被占用，尝试关闭..." -ForegroundColor Yellow
    $processId = $port8000.OwningProcess
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "✓ 已关闭占用端口的进程" -ForegroundColor Green
} else {
    Write-Host "✓ 端口 8000 可用" -ForegroundColor Green
}
Write-Host ""

# 启动服务器
Write-Host "启动 Uvicorn 服务器..." -ForegroundColor Yellow
Write-Host "访问地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 启动服务器
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

