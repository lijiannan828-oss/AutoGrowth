# ============================================================================
# 交互式配置 Google Drive 文件夹
# ============================================================================
# 用途：引导用户输入正确的 Google Drive 文件夹 ID 并更新配置
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "交互式配置 Google Drive 文件夹" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 配置说明：" -ForegroundColor Yellow
Write-Host ""
Write-Host "你需要提供 4 个 Google Drive 文件夹的 ID。" -ForegroundColor White
Write-Host ""
Write-Host "如何获取文件夹 ID：" -ForegroundColor Yellow
Write-Host "  1. 在 Google Drive 中打开文件夹" -ForegroundColor White
Write-Host "  2. 查看浏览器地址栏：" -ForegroundColor White
Write-Host "     https://drive.google.com/drive/folders/[这里就是文件夹ID]" -ForegroundColor Gray
Write-Host "  3. 复制文件夹 ID（最后一段）" -ForegroundColor White
Write-Host ""
Write-Host "示例：" -ForegroundColor Yellow
Write-Host "  地址：https://drive.google.com/drive/folders/1ABC123xyz" -ForegroundColor Gray
Write-Host "  ID：1ABC123xyz" -ForegroundColor Green
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Gray
Write-Host ""

# 收集文件夹 ID
Write-Host "请输入各个文件夹的 ID：" -ForegroundColor Yellow
Write-Host ""

$CN_FOLDER_ID = Read-Host "CN Programs 文件夹 ID"
$JP_FOLDER_ID = Read-Host "JP Programs 文件夹 ID"
$KR_FOLDER_ID = Read-Host "KR Programs 文件夹 ID"
$US_FOLDER_ID = Read-Host "US Programs 文件夹 ID"

Write-Host ""

# 验证输入
if ([string]::IsNullOrWhiteSpace($CN_FOLDER_ID) -or 
    [string]::IsNullOrWhiteSpace($JP_FOLDER_ID) -or 
    [string]::IsNullOrWhiteSpace($KR_FOLDER_ID) -or 
    [string]::IsNullOrWhiteSpace($US_FOLDER_ID)) {
    Write-Host "❌ 错误：所有文件夹 ID 都必须填写" -ForegroundColor Red
    exit 1
}

# 生成配置
$GDRIVE_ROOTS = "CN Programs:$CN_FOLDER_ID,JP Programs:$JP_FOLDER_ID,KR Programs:$KR_FOLDER_ID,US Programs:$US_FOLDER_ID"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "配置预览" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CN Programs: $CN_FOLDER_ID" -ForegroundColor White
Write-Host "JP Programs: $JP_FOLDER_ID" -ForegroundColor White
Write-Host "KR Programs: $KR_FOLDER_ID" -ForegroundColor White
Write-Host "US Programs: $US_FOLDER_ID" -ForegroundColor White
Write-Host ""
Write-Host "完整配置值：" -ForegroundColor Yellow
Write-Host "$GDRIVE_ROOTS" -ForegroundColor Cyan
Write-Host ""

# 确认
$confirm = Read-Host "确认要更新配置吗？(y/n)"

if ($confirm -ne "y") {
    Write-Host "❌ 已取消" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "开始更新配置" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 更新后端服务
Write-Host "🚀 正在更新 $BACKEND_SERVICE 环境变量..." -ForegroundColor Yellow

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

# 验证配置
Write-Host "🔍 验证配置..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$verifyResult = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" | Select-String "PIPELINE_GDRIVE_ROOTS"

if ($verifyResult) {
    Write-Host "✅ 配置验证成功！" -ForegroundColor Green
    Write-Host "当前配置：$verifyResult" -ForegroundColor Gray
} else {
    Write-Host "⚠️  无法验证配置" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "✅ 配置完成！" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 后续步骤：" -ForegroundColor Yellow
Write-Host "  1. 等待 2-3 分钟让服务重新部署" -ForegroundColor White
Write-Host "  2. 运行：.\scripts\restart_backend.ps1（强制重启）" -ForegroundColor White
Write-Host "  3. 清除浏览器缓存（Ctrl + Shift + Delete）" -ForegroundColor White
Write-Host "  4. 硬刷新页面（Ctrl + F5）" -ForegroundColor White
Write-Host "  5. 检查前端是否能看到数据" -ForegroundColor White
Write-Host ""

