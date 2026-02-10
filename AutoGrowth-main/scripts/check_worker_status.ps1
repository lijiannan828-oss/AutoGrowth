# 压制工具状态检查脚本（PowerShell 版本）
# 用法: .\scripts\check_worker_status.ps1

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"  # 如果实际区域不同，请修改
$JOB_NAME = "process-worker"

Write-Host "🔍 开始检查压制工具状态..." -ForegroundColor Cyan
Write-Host "项目: $PROJECT_ID"
Write-Host "区域: $REGION"
Write-Host "Job 名称: $JOB_NAME"
Write-Host ""

# 1. 检查 gcloud 是否已登录
Write-Host "📋 1. 检查 gcloud 认证状态..." -ForegroundColor Yellow
try {
    $account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if ($account) {
        Write-Host "✅ 已登录: $account" -ForegroundColor Green
    } else {
        Write-Host "❌ 未登录！请运行: gcloud auth login" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ gcloud 命令不可用！请先安装 Google Cloud SDK" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. 检查 Cloud Run Job 是否存在
Write-Host "📋 2. 检查 Cloud Run Job 是否存在..." -ForegroundColor Yellow
try {
    $jobInfo = gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID --format=json 2>$null | ConvertFrom-Json
    if ($jobInfo) {
        Write-Host "✅ Cloud Run Job 存在" -ForegroundColor Green
        Write-Host "   镜像: $($jobInfo.spec.template.spec.template.spec.containers[0].image)"
        Write-Host "   内存: $($jobInfo.spec.template.spec.template.spec.containers[0].resources.limits.memory)"
        Write-Host "   CPU: $($jobInfo.spec.template.spec.template.spec.containers[0].resources.limits.cpu)"
    } else {
        Write-Host "❌ Cloud Run Job 不存在！" -ForegroundColor Red
        Write-Host "   请先部署 Worker" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ 无法获取 Cloud Run Job 信息" -ForegroundColor Red
    Write-Host "   可能原因：区域错误、权限不足、Job 未部署" -ForegroundColor Yellow
    Write-Host "   请尝试其他区域：asia-east1, asia-northeast1" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 3. 检查最近的执行记录
Write-Host "📊 3. 检查最近 5 次执行记录..." -ForegroundColor Yellow
try {
    $executions = gcloud run jobs executions list --job=$JOB_NAME --region=$REGION --project=$PROJECT_ID --limit=5 --format=json 2>$null | ConvertFrom-Json
    if ($executions -and $executions.Count -gt 0) {
        Write-Host "✅ 找到 $($executions.Count) 次执行记录" -ForegroundColor Green
        foreach ($exec in $executions) {
            $name = $exec.metadata.name
            $status = $exec.status.conditions[0].type
            $completionTime = $exec.status.completionTime
            $succeededCount = $exec.status.succeededCount
            $failedCount = $exec.status.failedCount
            Write-Host "   - $name | 状态: $status | 成功: $succeededCount | 失败: $failedCount | 完成时间: $completionTime"
        }
    } else {
        Write-Host "⚠️  无执行记录（Job 从未运行过）" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  无法获取执行记录" -ForegroundColor Yellow
}
Write-Host ""

# 4. 检查最近的错误日志
Write-Host "🔴 4. 检查最近 10 条错误日志..." -ForegroundColor Yellow
try {
    $errorLogs = gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME AND severity>=ERROR" --limit=10 --project=$PROJECT_ID --format=json --freshness=24h 2>$null | ConvertFrom-Json
    if ($errorLogs -and $errorLogs.Count -gt 0) {
        Write-Host "❌ 找到 $($errorLogs.Count) 条错误日志" -ForegroundColor Red
        foreach ($log in $errorLogs) {
            $timestamp = $log.timestamp
            $message = $log.textPayload
            Write-Host "   [$timestamp] $message" -ForegroundColor Red
        }
    } else {
        Write-Host "✅ 无错误日志（最近 24 小时）" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  无法获取错误日志" -ForegroundColor Yellow
}
Write-Host ""

# 5. 检查最近的 Worker 日志
Write-Host "📝 5. 检查最近 20 条 Worker 日志..." -ForegroundColor Yellow
try {
    $workerLogs = gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME AND textPayload=~'\[process-worker\]'" --limit=20 --project=$PROJECT_ID --format=json --freshness=1h 2>$null | ConvertFrom-Json
    if ($workerLogs -and $workerLogs.Count -gt 0) {
        Write-Host "✅ 找到 $($workerLogs.Count) 条 Worker 日志" -ForegroundColor Green
        foreach ($log in $workerLogs[-5..-1]) {  # 只显示最后 5 条
            $timestamp = $log.timestamp
            $message = $log.textPayload
            Write-Host "   [$timestamp] $message"
        }
    } else {
        Write-Host "⚠️  无 Worker 日志（最近 1 小时）" -ForegroundColor Yellow
        Write-Host "   可能原因：Worker 未运行、日志延迟、时间范围太短" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  无法获取 Worker 日志" -ForegroundColor Yellow
}
Write-Host ""

# 6. 提供快速链接
Write-Host "🔗 6. 快速访问链接..." -ForegroundColor Yellow
Write-Host "   Cloud Run Jobs: https://console.cloud.google.com/run/jobs?project=$PROJECT_ID"
Write-Host "   Firestore 任务: https://console.cloud.google.com/firestore/data/pipeline_jobs?project=$PROJECT_ID"
Write-Host "   Firestore 并发: https://console.cloud.google.com/firestore/data/concurrency_control?project=$PROJECT_ID"
Write-Host "   Cloud Logging: https://console.cloud.google.com/logs/query?project=$PROJECT_ID"
Write-Host ""

# 7. 下一步建议
Write-Host "💡 下一步操作建议：" -ForegroundColor Cyan
Write-Host "   1. 如果 Job 不存在 → 运行部署脚本"
Write-Host "   2. 如果有错误日志 → 查看详细错误信息"
Write-Host "   3. 如果无执行记录 → 检查 Firestore 任务状态和并发控制"
Write-Host "   4. 如果任务卡住 → 查看 Firestore tasks 子集合的 current_file"
Write-Host ""

Write-Host "✅ 检查完成！" -ForegroundColor Green

