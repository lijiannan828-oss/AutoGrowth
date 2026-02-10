# ============================================
# 生产环境配置脚本
# ============================================
# 用途：一键配置 autogrowth-backend 和 process-worker 的环境变量
# 使用方法：
#   1. 修改下面的 FOLDER_ID 变量为实际的 Google Drive Folder ID
#   2. 确保已登录 gcloud: gcloud auth login
#   3. 运行：.\scripts\configure_production_env.ps1
# ============================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"
$WORKER_JOB = "process-worker"

# ============================================
# 🔧 配置区域：请修改为实际的 Google Drive Folder ID
# ============================================
$KR_FOLDER_ID = "YOUR_KR_PROGRAMS_FOLDER_ID"
$JP_FOLDER_ID = "YOUR_JP_PROGRAMS_FOLDER_ID"
$US_FOLDER_ID = "YOUR_US_PROGRAMS_FOLDER_ID"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  生产环境配置脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目 ID: $PROJECT_ID" -ForegroundColor White
Write-Host "区域: $REGION" -ForegroundColor White
Write-Host "Backend 服务: $BACKEND_SERVICE" -ForegroundColor White
Write-Host "Worker 作业: $WORKER_JOB" -ForegroundColor White
Write-Host ""

# ============================================
# 检查配置
# ============================================
if ($KR_FOLDER_ID -eq "YOUR_KR_PROGRAMS_FOLDER_ID") {
    Write-Host "❌ 错误：请先修改脚本中的 Folder ID 配置" -ForegroundColor Red
    Write-Host ""
    Write-Host "📝 配置步骤：" -ForegroundColor Yellow
    Write-Host "   1. 打开 Google Drive，进入对应文件夹" -ForegroundColor White
    Write-Host "   2. 查看浏览器地址栏：" -ForegroundColor White
    Write-Host "      https://drive.google.com/drive/folders/[这里就是Folder ID]" -ForegroundColor Gray
    Write-Host "   3. 复制 Folder ID" -ForegroundColor White
    Write-Host "   4. 编辑此脚本，替换 YOUR_*_FOLDER_ID" -ForegroundColor White
    Write-Host ""
    exit 1
}

# 构建 PIPELINE_GDRIVE_ROOTS 环境变量
$GDRIVE_ROOTS = "KR Programs:${KR_FOLDER_ID},JP Programs:${JP_FOLDER_ID},US Programs:${US_FOLDER_ID}"

Write-Host "Google Drive 映射配置：" -ForegroundColor Yellow
Write-Host "  KR Programs: $KR_FOLDER_ID" -ForegroundColor Gray
Write-Host "  JP Programs: $JP_FOLDER_ID" -ForegroundColor Gray
Write-Host "  US Programs: $US_FOLDER_ID" -ForegroundColor Gray
Write-Host ""

# ============================================
# 步骤 1: 检查 gcloud 认证
# ============================================
Write-Host "📋 步骤 1: 检查 gcloud 认证..." -ForegroundColor Yellow
try {
    $account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if ($account) {
        Write-Host "✅ 已登录: $account" -ForegroundColor Green
    } else {
        Write-Host "❌ 未登录！请运行: gcloud auth login" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ gcloud 未安装或配置错误" -ForegroundColor Red
    exit 1
}
Write-Host ""

# ============================================
# 步骤 2: 配置 autogrowth-backend
# ============================================
Write-Host "📋 步骤 2: 配置 autogrowth-backend 服务..." -ForegroundColor Yellow
Write-Host ""

# 检查服务是否存在
Write-Host "   检查服务是否存在..." -ForegroundColor Cyan
if (gcloud run services describe $BACKEND_SERVICE --region=$REGION --project=$PROJECT_ID 2>$null) {
    Write-Host "   ✅ 服务存在" -ForegroundColor Green
} else {
    Write-Host "   ❌ 服务不存在！" -ForegroundColor Red
    Write-Host "   请检查服务名称是否正确" -ForegroundColor Yellow
    exit 1
}

Write-Host "   更新环境变量..." -ForegroundColor Cyan
gcloud run services update $BACKEND_SERVICE `
  --region=$REGION `
  --project=$PROJECT_ID `
  --set-env-vars="PIPELINE_GDRIVE_ROOTS=${GDRIVE_ROOTS}" `
  --set-env-vars="PIPELINE_GCS_SOURCE_BUCKET=vigloo_source" `
  --set-env-vars="PIPELINE_GCS_PROCESSED_BUCKET=vigloo_processed" `
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" `
  --set-env-vars="FIRESTORE_PROJECT_ID=${PROJECT_ID}" `
  --set-env-vars="APP_ENV=production"

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Backend 服务配置成功！" -ForegroundColor Green
} else {
    Write-Host "   ❌ Backend 服务配置失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# ============================================
# 步骤 3: 配置 process-worker
# ============================================
Write-Host "📋 步骤 3: 配置 process-worker 作业..." -ForegroundColor Yellow
Write-Host ""

# 检查作业是否存在
Write-Host "   检查作业是否存在..." -ForegroundColor Cyan
if (gcloud run jobs describe $WORKER_JOB --region=$REGION --project=$PROJECT_ID 2>$null) {
    Write-Host "   ✅ 作业存在" -ForegroundColor Green
} else {
    Write-Host "   ❌ 作业不存在！" -ForegroundColor Red
    Write-Host "   请检查作业名称是否正确" -ForegroundColor Yellow
    exit 1
}

Write-Host "   更新环境变量..." -ForegroundColor Cyan
gcloud run jobs update $WORKER_JOB `
  --region=$REGION `
  --project=$PROJECT_ID `
  --set-env-vars="PIPELINE_GCS_SOURCE_BUCKET=vigloo_source" `
  --set-env-vars="PIPELINE_GCS_PROCESSED_BUCKET=vigloo_processed" `
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" `
  --set-env-vars="FIRESTORE_PROJECT_ID=${PROJECT_ID}" `
  --set-env-vars="APP_ENV=production"

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Worker 作业配置成功！" -ForegroundColor Green
} else {
    Write-Host "   ❌ Worker 作业配置失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

