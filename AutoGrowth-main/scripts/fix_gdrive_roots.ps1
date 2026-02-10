# ============================================================================
# 修复 PIPELINE_GDRIVE_ROOTS 配置脚本
# ============================================================================
# 用途：正确配置所有环境变量，避免被覆盖
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "修复 PIPELINE_GDRIVE_ROOTS 配置" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 步骤 1：检查当前配置
Write-Host "📋 步骤 1：检查当前环境变量配置..." -ForegroundColor Yellow
Write-Host ""

$currentEnv = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="yaml(spec.template.spec.containers[0].env)" 2>&1

Write-Host "当前环境变量：" -ForegroundColor White
Write-Host $currentEnv -ForegroundColor Gray
Write-Host ""

# 步骤 2：获取现有环境变量
Write-Host "📋 步骤 2：获取现有环境变量..." -ForegroundColor Yellow
Write-Host ""

$envVars = @{}
$envOutput = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(spec.template.spec.containers[0].env)" 2>&1

if ($envOutput) {
    $envOutput -split ';' | ForEach-Object {
        if ($_ -match '(.+?)=(.+)') {
            $envVars[$matches[1]] = $matches[2]
            Write-Host "   找到: $($matches[1])" -ForegroundColor Gray
        }
    }
}
Write-Host ""

# 步骤 3：更新 PIPELINE_GDRIVE_ROOTS
Write-Host "📋 步骤 3：更新 PIPELINE_GDRIVE_ROOTS..." -ForegroundColor Yellow
Write-Host ""

$GDRIVE_ROOTS = "CN Programs:0AOmMvGake5oOUk9PVA,JP Programs:0APzazx6u_NjmUk9PVA,KR Programs:0ALGBuL6lJ76mUk9PVA,US Programs:0AB-Io4pA_rcdUk9PVA"

Write-Host "新的 PIPELINE_GDRIVE_ROOTS 值：" -ForegroundColor White
Write-Host "  $GDRIVE_ROOTS" -ForegroundColor Green
Write-Host ""

# 更新环境变量（只更新 PIPELINE_GDRIVE_ROOTS，保留其他变量）
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

# 步骤 4：验证配置
Write-Host "📋 步骤 4：验证配置..." -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 5  # 等待配置生效

$verifyResult = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" | Select-String "PIPELINE_GDRIVE_ROOTS"

if ($verifyResult) {
    Write-Host "✅ 配置验证成功！" -ForegroundColor Green
    Write-Host "当前配置：" -ForegroundColor White
    Write-Host $verifyResult -ForegroundColor Green
} else {
    Write-Host "⚠️  无法验证配置" -ForegroundColor Yellow
}
Write-Host ""

# 步骤 5：检查服务状态
Write-Host "📋 步骤 5：检查服务状态..." -ForegroundColor Yellow
Write-Host ""

$serviceUrl = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(status.url)"

Write-Host "服务 URL：" -ForegroundColor White
Write-Host "  $serviceUrl" -ForegroundColor Cyan
Write-Host ""

# 完成
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "✅ 配置修复完成！" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 后续步骤：" -ForegroundColor Yellow
Write-Host "  1. 清除浏览器缓存（Ctrl + Shift + Delete）" -ForegroundColor White
Write-Host "  2. 硬刷新页面（Ctrl + F5）" -ForegroundColor White
Write-Host "  3. 检查前端是否能看到 CN/JP/KR/US Programs" -ForegroundColor White
Write-Host "  4. 如果还是空的，运行诊断脚本：.\scripts\diagnose_empty_issue.ps1" -ForegroundColor White
Write-Host ""

