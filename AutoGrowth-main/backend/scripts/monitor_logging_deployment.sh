#!/bin/bash
# Monitor deployment status for logging enhancement

set -e

echo "=" | cat
echo "📊 日志增强部署监控"
echo "=" | cat
echo ""

# Get latest commit
COMMIT_SHA=$(git rev-parse HEAD)
echo "📝 最新提交: $COMMIT_SHA"
echo ""

# Check GitHub Actions status
echo "🔍 检查 GitHub Actions 状态..."
echo ""

# Get workflow runs
WORKFLOW_RUNS=$(gh run list --workflow=backend-deploy.yaml --limit=1 --json status,conclusion,createdAt,headSha 2>/dev/null || echo "[]")

if [ "$WORKFLOW_RUNS" != "[]" ]; then
    echo "$WORKFLOW_RUNS" | jq -r '.[] | "状态: \(.status) | 结论: \(.conclusion // "N/A") | 创建时间: \(.createdAt) | SHA: \(.headSha)"'
else
    echo "⚠️  无法获取 GitHub Actions 状态（需要安装 gh CLI 或手动检查）"
    echo "   链接: https://github.com/lijiannan828-oss/AutoGrowth/actions"
fi

echo ""
echo "=" | cat
echo "📋 部署验证步骤"
echo "=" | cat
echo ""
echo "1. 等待 CI/CD 部署完成（约 5-10 分钟）"
echo ""
echo "2. 检查 Relay Service 日志:"
echo "   gcloud logging read \\"
echo "     \"resource.type=cloud_run_revision \\"
echo "      AND resource.labels.service_name=drama-processor-relay-service \\"
echo "      AND textPayload=~\\\"RELAY-\\\"\" \\"
echo "     --limit=50 \\"
echo "     --format=json"
echo ""
echo "3. 检查 ConcurrencyService 日志:"
echo "   gcloud logging read \\"
echo "     \"resource.type=cloud_run_revision \\"
echo "      AND resource.labels.service_name=drama-processor-relay-service \\"
echo "      AND textPayload=~\\\"CONCURRENCY\\\"\" \\"
echo "     --limit=50 \\"
echo "     --format=json"
echo ""
echo "4. 触发一个传输任务，验证日志输出:"
echo "   - 传输任务完成后，检查 Relay Service 是否收到 Eventarc 事件"
echo "   - 检查是否有详细的处理步骤日志"
echo "   - 检查是否有 request_id 追踪"
echo ""
echo "=" | cat
echo "✅ 部署完成后，日志增强功能将自动生效"
echo "=" | cat


