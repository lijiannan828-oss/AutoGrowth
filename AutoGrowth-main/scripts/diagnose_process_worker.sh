#!/bin/bash
# 压制工具诊断脚本
# 用法: ./scripts/diagnose_process_worker.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID="${1:-fleet-blend-469520-n7}"
REGION="${2:-asia-east1}"
JOB_NAME="process-worker"

echo "🔍 开始诊断压制工具..."
echo "项目: $PROJECT_ID"
echo "区域: $REGION"
echo "Job 名称: $JOB_NAME"
echo ""

# 1. 检查 Cloud Run Job 是否存在
echo "📋 1. 检查 Cloud Run Job 状态..."
if gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Cloud Run Job 存在"
    gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID --format="table(
        metadata.name,
        status.conditions[0].type,
        status.conditions[0].status,
        spec.template.spec.template.spec.containers[0].image
    )"
else
    echo "❌ Cloud Run Job 不存在！请先部署 Worker"
    exit 1
fi
echo ""

# 2. 检查最近的执行记录
echo "📊 2. 最近 5 次执行记录..."
gcloud run jobs executions list \
    --job=$JOB_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --limit=5 \
    --format="table(
        metadata.name,
        status.completionTime,
        status.succeededCount,
        status.failedCount
    )" || echo "⚠️ 无执行记录"
echo ""

# 3. 检查最近的错误日志
echo "🔴 3. 最近 10 条错误日志..."
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME AND severity>=ERROR" \
    --limit=10 \
    --project=$PROJECT_ID \
    --format="table(timestamp,textPayload)" \
    --freshness=24h || echo "⚠️ 无错误日志"
echo ""

# 4. 检查最近的 Worker 日志
echo "📝 4. 最近 20 条 Worker 日志..."
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME AND textPayload=~'\[process-worker\]'" \
    --limit=20 \
    --project=$PROJECT_ID \
    --format="table(timestamp,textPayload)" \
    --freshness=1h || echo "⚠️ 无 Worker 日志"
echo ""

# 5. 检查 Firestore 中的任务状态
echo "🗄️ 5. Firestore 任务状态（需要手动检查）..."
echo "请访问: https://console.cloud.google.com/firestore/data/pipeline_jobs?project=$PROJECT_ID"
echo ""

# 6. 检查并发控制状态
echo "🔒 6. 并发控制状态（需要手动检查）..."
echo "请访问: https://console.cloud.google.com/firestore/data/concurrency_control?project=$PROJECT_ID"
echo ""

# 7. 检查 Service Account 权限
echo "🔑 7. Service Account 权限..."
SERVICE_ACCOUNT=$(gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID --format="value(spec.template.spec.template.spec.serviceAccountName)")
echo "Service Account: $SERVICE_ACCOUNT"
if [ -n "$SERVICE_ACCOUNT" ]; then
    gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SERVICE_ACCOUNT" \
        --format="table(bindings.role)" || echo "⚠️ 无法获取权限信息"
else
    echo "⚠️ 未配置 Service Account"
fi
echo ""

echo "✅ 诊断完成！"
echo ""
echo "💡 下一步操作建议："
echo "1. 如果 Cloud Run Job 不存在，运行: cd infra && ./deploy.sh"
echo "2. 如果有错误日志，查看详细信息: gcloud logging read '...' --format json"
echo "3. 如果任务卡在 QUEUED，检查并发控制: Firestore > concurrency_control"
echo "4. 如果任务卡在 PROCESSING，查看 tasks 子集合的 current_file 字段"

