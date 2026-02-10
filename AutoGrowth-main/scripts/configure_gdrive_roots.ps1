# ============================================================================
# Google Drive Roots 配置脚本
# ============================================================================
# 用途：自动配置 autogrowth-backend 和 process-worker 的 PIPELINE_GDRIVE_ROOTS
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

# 配置参数
$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"
$WORKER_JOB = "process-worker"

# Google Drive Folder ID 配置
$CN_FOLDER_ID = "0AOmMvGake5oOUk9PVA"
$JP_FOLDER_ID = "0APzazx6u_NjmUk9PVA"
$KR_FOLDER_ID = "0ALGBuL6lJ76mUk9PVA"
$US_FOLDER_ID = "0AB-Io4pA_rcdUk9PVA"

# 生成完整的环境变量值
$GDRIVE_ROOTS = "CN Programs:$CN_FOLDER_ID,JP Programs:$JP_FOLDER_ID,KR Programs:$KR_FOLDER_ID,US Programs:$US_FOLDER_ID"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Google Drive Roots 配置脚本" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 显示配置信息
Write-Host "📋 配置信息：" -ForegroundColor Yellow
Write-Host "  项目 ID：$PROJECT_ID" -ForegroundColor White
Write-Host "  区域：$REGION" -ForegroundColor White
Write-Host "  Backend 服务：$BACKEND_SERVICE" -ForegroundColor White
Write-Host "  Worker 任务：$WORKER_JOB" -ForegroundColor White
Write-Host ""
Write-Host "📁 Google Drive Folder ID：" -ForegroundColor Yellow
Write-Host "  CN Programs: $CN_FOLDER_ID" -ForegroundColor White
Write-Host "  JP Programs: $JP_FOLDER_ID" -ForegroundColor White
Write-Host "  KR Programs: $KR_FOLDER_ID" -ForegroundColor White
Write-Host "  US Programs: $US_FOLDER_ID" -ForegroundColor White
Write-Host ""
Write-Host "🔧 完整配置值：" -ForegroundColor Yellow
Write-Host "  $GDRIVE_ROOTS" -ForegroundColor Green
Write-Host ""

# 检查 gcloud 是否已认证
Write-Host "🔍 检查 gcloud 认证状态..." -ForegroundColor Yellow
$authCheck = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($authCheck)) {
    Write-Host "❌ 错误：gcloud 未认证" -ForegroundColor Red
    Write-Host "请运行：gcloud auth login" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ 已认证账号：$authCheck" -ForegroundColor Green
Write-Host ""

# 配置 autogrowth-backend 服务
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "步骤 1/2：配置 $BACKEND_SERVICE 服务" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 正在更新 $BACKEND_SERVICE 环境变量..." -ForegroundColor Yellow
$backendResult = gcloud run services update $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --update-env-vars="PIPELINE_GDRIVE_ROOTS=$GDRIVE_ROOTS" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $BACKEND_SERVICE 配置成功！" -ForegroundColor Green
} else {
    Write-Host "❌ $BACKEND_SERVICE 配置失败！" -ForegroundColor Red
    Write-Host $backendResult -ForegroundColor Red
    exit 1
}
Write-Host ""

# 配置 process-worker 任务
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "步骤 2/2：配置 $WORKER_JOB 任务" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🚀 正在更新 $WORKER_JOB 环境变量..." -ForegroundColor Yellow
$workerResult = gcloud run jobs update $WORKER_JOB `
    --region=$REGION `
    --project=$PROJECT_ID `
    --update-env-vars="PIPELINE_GDRIVE_ROOTS=$GDRIVE_ROOTS" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ $WORKER_JOB 配置成功！" -ForegroundColor Green
} else {
    Write-Host "⚠️  $WORKER_JOB 配置失败（可能不存在）" -ForegroundColor Yellow
    Write-Host $workerResult -ForegroundColor Yellow
}
Write-Host ""

# 验证配置
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "验证配置" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🔍 验证 $BACKEND_SERVICE 配置..." -ForegroundColor Yellow
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

# 完成
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "✅ 配置完成！" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 后续步骤：" -ForegroundColor Yellow
Write-Host "  1. 访问 GCP Console 查看服务状态" -ForegroundColor White
Write-Host "  2. 测试 API 端点是否正常工作" -ForegroundColor White
Write-Host "  3. 检查日志确认配置已生效" -ForegroundColor White
Write-Host ""

