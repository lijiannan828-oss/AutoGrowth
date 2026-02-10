# ============================================================================
# 更新为普通文件夹 ID
# ============================================================================
# 用途：将 PIPELINE_GDRIVE_ROOTS 更新为普通文件夹 ID
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "更新为普通文件夹 ID" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 新的文件夹 ID（普通文件夹）
$KR_FOLDER_ID = "17tuD6faa0S_HIo0auCIHCydsKCfkvUMD"
$JP_FOLDER_ID = "1Pqaev9bqBbZXniTWM__wvw_0inDyMBWs"
$US_FOLDER_ID = "1htT5nJdtoVV5pA812s2fwOPvqVAWkrYC"

# 注意：你没有提供 CN Programs 的 ID，这里保留原来的
$CN_FOLDER_ID = "0AOmMvGake5oOUk9PVA"

$GDRIVE_ROOTS = "CN Programs:$CN_FOLDER_ID,JP Programs:$JP_FOLDER_ID,KR Programs:$KR_FOLDER_ID,US Programs:$US_FOLDER_ID"

Write-Host "📋 新的配置：" -ForegroundColor Yellow
Write-Host "  CN Programs: $CN_FOLDER_ID (保留原配置)" -ForegroundColor White
Write-Host "  JP Programs: $JP_FOLDER_ID (普通文件夹)" -ForegroundColor Green
Write-Host "  KR Programs: $KR_FOLDER_ID (普通文件夹)" -ForegroundColor Green
Write-Host "  US Programs: $US_FOLDER_ID (普通文件夹)" -ForegroundColor Green
Write-Host ""
Write-Host "完整配置值：" -ForegroundColor Yellow
Write-Host "  $GDRIVE_ROOTS" -ForegroundColor Cyan
Write-Host ""

# 确认
Write-Host "⚠️  注意：这将更新后端配置为普通文件夹 ID" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "确认要更新吗？(y/n)"

if ($confirm -ne "y") {
    Write-Host "❌ 已取消" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🚀 正在更新环境变量..." -ForegroundColor Yellow

$updateResult = gcloud run services update $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --update-env-vars="PIPELINE_GDRIVE_ROOTS=$GDRIVE_ROOTS" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 更新成功！" -ForegroundColor Green
} else {
    Write-Host "❌ 更新失败！" -ForegroundColor Red
    Write-Host $updateResult -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "✅ 配置更新完成！" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 后续步骤：" -ForegroundColor Yellow
Write-Host "  1. 等待 2-3 分钟让服务重新部署" -ForegroundColor White
Write-Host "  2. 运行：.\scripts\restart_backend.ps1（强制重启）" -ForegroundColor White
Write-Host "  3. 清除浏览器缓存（Ctrl + Shift + Delete）" -ForegroundColor White
Write-Host "  4. 硬刷新页面（Ctrl + F5）" -ForegroundColor White
Write-Host ""

