#!/bin/bash
# Monitor deployment status for Eventarc event format fix

set -e

echo "=" | cat
echo "📊 Eventarc 事件格式修复部署监控"
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
echo "2. 触发一个新的传输任务"
echo ""
echo "3. 检查 Relay Service 日志中的完整 payload:"
echo "   gcloud logging read \\"
echo "     \"resource.type=cloud_run_revision \\"
echo "      AND resource.labels.service_name=drama-processor-relay-service \\"
echo "      AND textPayload=~\\\"📋 Full payload\\\"\" \\"
echo "     --limit=10 \\"
echo "     --format=json"
echo ""
echo "4. 验证事件是否能正确解析:"
echo "   - 检查 payload 中是否包含正确的 bucket 和 name"
echo "   - 检查事件是否被正确识别为 _PROCESS_NOW.txt"
echo "   - 检查压制任务是否被创建"
echo ""
echo "=" | cat
echo "✅ 部署完成后，Eventarc 事件格式解析将自动生效"
echo "=" | cat


