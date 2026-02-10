# 设置环境变量
$env:GOOGLE_APPLICATION_CREDENTIALS="d:\workspace\AutoGrowth\backend\fleet-blend-469520-n7-23b7c649292b.json"

# 启动后端
Write-Host "正在启动后端服务..." -ForegroundColor Green
Write-Host "GCS 认证文件: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Cyan
Write-Host ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

