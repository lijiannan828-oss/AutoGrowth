# ============================================
# process-worker 存在性检查脚本
# ============================================

$PROJECT_ID = "fleet-blend-469520-n7"
$JOB_NAME = "process-worker"
$REGIONS = @("us-central1", "asia-east1", "asia-northeast1", "us-west1")

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  process-worker 存在性检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目 ID: $PROJECT_ID" -ForegroundColor White
Write-Host "Job 名称: $JOB_NAME" -ForegroundColor White
Write-Host ""

# 检查 gcloud 是否已安装
Write-Host "📋 步骤 1: 检查 gcloud 工具..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud version --format="value(version)" 2>$null
    if ($gcloudVersion) {
        Write-Host "✅ gcloud 已安装 (版本: $gcloudVersion)" -ForegroundColor Green
    } else {
        Write-Host "❌ gcloud 未安装或未配置" -ForegroundColor Red
        Write-Host "   请访问: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ 无法执行 gcloud 命令" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 检查是否已登录
Write-Host "📋 步骤 2: 检查 gcloud 认证状态..." -ForegroundColor Yellow
try {
    $account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if ($account) {
        Write-Host "✅ 已登录账号: $account" -ForegroundColor Green
    } else {
        Write-Host "❌ 未登录！请运行: gcloud auth login" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ 认证检查失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 在多个区域中查找 process-worker
Write-Host "📋 步骤 3: 在多个区域中查找 process-worker..." -ForegroundColor Yellow
Write-Host ""

$foundRegion = $null
$jobInfo = $null

foreach ($region in $REGIONS) {
    Write-Host "   🔍 检查区域: $region" -ForegroundColor Cyan
    
    try {
        $result = gcloud run jobs describe $JOB_NAME `
            --region=$region `
            --project=$PROJECT_ID `
            --format=json 2>$null
        
        if ($result) {
            $jobInfo = $result | ConvertFrom-Json
            $foundRegion = $region
            Write-Host "   ✅ 找到了！" -ForegroundColor Green
            break
        } else {
            Write-Host "   ❌ 未找到" -ForegroundColor Gray
        }
    } catch {
        Write-Host "   ❌ 未找到" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  检查结果" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($foundRegion) {
    Write-Host "✅ process-worker 存在！" -ForegroundColor Green
    Write-Host ""
    Write-Host "📍 部署区域: $foundRegion" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 详细信息:" -ForegroundColor Yellow
    Write-Host "   镜像: $($jobInfo.spec.template.spec.template.spec.containers[0].image)" -ForegroundColor White
    
    $memory = $jobInfo.spec.template.spec.template.spec.containers[0].resources.limits.memory
    $cpu = $jobInfo.spec.template.spec.template.spec.containers[0].resources.limits.cpu
    Write-Host "   内存: $memory" -ForegroundColor White
    Write-Host "   CPU: $cpu" -ForegroundColor White
    
    $parallelism = $jobInfo.spec.template.spec.parallelism
    Write-Host "   并行任务数: $parallelism" -ForegroundColor White
    
    Write-Host ""
    Write-Host "📋 最近执行记录:" -ForegroundColor Yellow
    try {
        $executions = gcloud run jobs executions list `
            --job=$JOB_NAME `
            --region=$foundRegion `
            --project=$PROJECT_ID `
            --limit=5 `
            --format=json 2>$null | ConvertFrom-Json
        
        if ($executions -and $executions.Count -gt 0) {
            Write-Host "   找到 $($executions.Count) 次执行记录" -ForegroundColor Green
            Write-Host ""
            foreach ($exec in $executions) {
                $execName = $exec.metadata.name
                $status = $exec.status.conditions[0].type
                $completionTime = $exec.status.completionTime
                $succeededCount = $exec.status.succeededCount
                $failedCount = $exec.status.failedCount
                
                Write-Host "   📌 $execName" -ForegroundColor Cyan
                Write-Host "      状态: $status" -ForegroundColor White
                Write-Host "      成功: $succeededCount | 失败: $failedCount" -ForegroundColor White
                Write-Host "      完成时间: $completionTime" -ForegroundColor Gray
                Write-Host ""
            }
        } else {
            Write-Host "   ⚠️  无执行记录（Job 从未运行过）" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "   ⚠️  无法获取执行记录" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🔗 快速访问链接:" -ForegroundColor Yellow
    Write-Host "   https://console.cloud.google.com/run/jobs/details/$foundRegion/$JOB_NAME`?project=$PROJECT_ID" -ForegroundColor Cyan
    
} else {
    Write-Host "❌ process-worker 不存在！" -ForegroundColor Red
    Write-Host ""
    Write-Host "📝 可能的原因:" -ForegroundColor Yellow
    Write-Host "   1. Worker 从未部署过" -ForegroundColor White
    Write-Host "   2. Worker 已被删除" -ForegroundColor White
    Write-Host "   3. 部署在其他项目中" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 解决方案:" -ForegroundColor Yellow
    Write-Host "   需要部署 process-worker" -ForegroundColor White
    Write-Host "   运行部署脚本: .\scripts\deploy_process_worker.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🔗 手动检查链接:" -ForegroundColor Yellow
    Write-Host "   https://console.cloud.google.com/run/jobs?project=$PROJECT_ID" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  检查完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

