# ============================================
# process-worker 部署脚本
# ============================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$JOB_NAME = "process-worker"
$SERVICE_ACCOUNT = "sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"
$IMAGE_NAME = "$REGION-docker.pkg.dev/$PROJECT_ID/autogrowth-docker/$JOB_NAME"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  部署 process-worker 到 Cloud Run Jobs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目 ID: $PROJECT_ID" -ForegroundColor White
Write-Host "区域: $REGION" -ForegroundColor White
Write-Host "Job 名称: $JOB_NAME" -ForegroundColor White
Write-Host "镜像名称: $IMAGE_NAME" -ForegroundColor White
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

# 步骤 2: 设置默认项目
Write-Host "📋 步骤 2: 设置默认项目..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
Write-Host "✅ 项目已设置" -ForegroundColor Green
Write-Host ""

# 步骤 3: 构建 Docker 镜像
Write-Host "📋 步骤 3: 构建 Docker 镜像..." -ForegroundColor Yellow
Write-Host "   这可能需要 5-10 分钟，请耐心等待..." -ForegroundColor Gray
Write-Host ""

$buildCommand = @"
gcloud builds submit backend/app/workers/process `
  --tag=$IMAGE_NAME`:latest `
  --project=$PROJECT_ID `
  --timeout=20m
"@

Write-Host "执行命令:" -ForegroundColor Cyan
Write-Host $buildCommand -ForegroundColor Gray
Write-Host ""

try {
    Invoke-Expression $buildCommand
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 镜像构建成功" -ForegroundColor Green
    } else {
        Write-Host "❌ 镜像构建失败" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ 构建过程出错: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤 4: 部署到 Cloud Run Jobs
Write-Host "📋 步骤 4: 部署到 Cloud Run Jobs..." -ForegroundColor Yellow
Write-Host ""

$deployCommand = @"
gcloud run jobs create $JOB_NAME `
  --image=$IMAGE_NAME`:latest `
  --region=$REGION `
  --project=$PROJECT_ID `
  --service-account=$SERVICE_ACCOUNT `
  --memory=4Gi `
  --cpu=2 `
  --max-retries=0 `
  --parallelism=3 `
  --task-timeout=3600s `
  --set-secrets=GOOGLE_APPLICATION_CREDENTIALS=gcp-sa-key:latest
"@

Write-Host "执行命令:" -ForegroundColor Cyan
Write-Host $deployCommand -ForegroundColor Gray
Write-Host ""

try {
    Invoke-Expression $deployCommand
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 部署成功！" -ForegroundColor Green
    } else {
        Write-Host "⚠️  部署失败，可能 Job 已存在，尝试更新..." -ForegroundColor Yellow
        
        # 如果创建失败，尝试更新
        $updateCommand = @"
gcloud run jobs update $JOB_NAME `
  --image=$IMAGE_NAME`:latest `
  --region=$REGION `
  --project=$PROJECT_ID
"@
        Invoke-Expression $updateCommand
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 更新成功！" -ForegroundColor Green
        } else {
            Write-Host "❌ 更新失败" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "❌ 部署过程出错: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤 5: 验证部署
Write-Host "📋 步骤 5: 验证部署..." -ForegroundColor Yellow
gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  部署完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔗 快速访问链接:" -ForegroundColor Yellow
Write-Host "   https://console.cloud.google.com/run/jobs/details/$REGION/$JOB_NAME`?project=$PROJECT_ID" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 下一步:" -ForegroundColor Yellow
Write-Host "   1. 在前端提交一个压制任务测试" -ForegroundColor White
Write-Host "   2. 查看 Firestore pipeline_jobs 集合确认任务状态" -ForegroundColor White
Write-Host "   3. 查看 Cloud Run Jobs 日志确认执行情况" -ForegroundColor White

