# ============================================
# 更新 process-worker 环境变量脚本
# ============================================
# 用途：更新 Cloud Run Jobs process-worker 的环境变量
# 使用方法：
#   1. 确保已登录 gcloud: gcloud auth login
#   2. 运行：.\scripts\update_process_worker_env.ps1
# ============================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$JOB_NAME = "drama-processor-job"  # 实际的 Job 名称

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  更新 process-worker 环境变量" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目 ID: $PROJECT_ID" -ForegroundColor White
Write-Host "区域: $REGION" -ForegroundColor White
Write-Host "Job 名称: $JOB_NAME" -ForegroundColor White
Write-Host ""

# 步骤 1: 检查 gcloud 认证
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

# 步骤 2: 检查 Job 是否存在
Write-Host "📋 步骤 2: 检查 Job 是否存在..." -ForegroundColor Yellow
try {
    $jobInfo = gcloud run jobs describe $JOB_NAME `
        --region=$REGION `
        --project=$PROJECT_ID `
        --format=json 2>$null | ConvertFrom-Json
    
    if ($jobInfo) {
        Write-Host "✅ Job 存在" -ForegroundColor Green
        Write-Host "   镜像: $($jobInfo.spec.template.spec.template.spec.containers[0].image)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Job 不存在！" -ForegroundColor Red
        Write-Host "   请先部署 process-worker" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ 无法获取 Job 信息" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤 3: 更新环境变量
Write-Host "📋 步骤 3: 更新环境变量..." -ForegroundColor Yellow
Write-Host ""

$updateCommand = @"
gcloud run jobs update $JOB_NAME `
  --region=$REGION `
  --project=$PROJECT_ID `
  --set-env-vars="PIPELINE_GCS_SOURCE_BUCKET=vigloo_source" `
  --set-env-vars="PIPELINE_GCS_PROCESSED_BUCKET=vigloo_processed" `
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID" `
  --set-env-vars="FIRESTORE_PROJECT_ID=$PROJECT_ID" `
  --set-env-vars="APP_ENV=production"
"@

Write-Host "执行命令:" -ForegroundColor Cyan
Write-Host $updateCommand -ForegroundColor Gray
Write-Host ""

try {
    Invoke-Expression $updateCommand
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 环境变量更新成功！" -ForegroundColor Green
    } else {
        Write-Host "❌ 环境变量更新失败" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ 更新过程出错: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤 4: 验证配置
Write-Host "📋 步骤 4: 验证配置..." -ForegroundColor Yellow
Write-Host "当前环境变量:" -ForegroundColor Cyan
gcloud run jobs describe $JOB_NAME `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(spec.template.spec.template.spec.containers[0].env)"
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  配置完成！" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔗 快速访问链接:" -ForegroundColor Yellow
Write-Host "   https://console.cloud.google.com/run/jobs/details/$REGION/$JOB_NAME`?project=$PROJECT_ID" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 下一步:" -ForegroundColor Yellow
Write-Host "   1. 提交一个压制任务测试" -ForegroundColor White
Write-Host "   2. 查看 Cloud Run Jobs 日志确认环境变量生效" -ForegroundColor White
Write-Host "   3. 验证任务是否正常执行" -ForegroundColor White
Write-Host ""

