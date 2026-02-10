#!/bin/bash
# Monitor deployment of the blocked job fix

set -e

echo "🚀 监控部署状态"
echo "=============="
echo ""

# Check GitHub Actions
echo "📋 GitHub Actions 状态:"
echo "   https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo ""

# Check recent deployments
echo "📦 最近的部署:"
gcloud run services list \
  --filter="metadata.name~'drama-processor-relay-service' OR metadata.name~'drama-processor-job'" \
  --format="table(metadata.name,status.url,status.latestReadyRevisionName,status.latestCreatedRevisionName)" \
  --project=fleet-blend-469520-n7 \
  --region=us-central1 2>/dev/null || echo "   ⚠️  无法获取部署状态"

echo ""
echo "🔍 验证修复:"
echo "   1. 并发控制清理逻辑: backend/app/services/concurrency_service.py"
echo "   2. 字幕文件识别逻辑: backend/app/services/pipeline_discovery_service.py"
echo ""
echo "📄 详细文档:"
echo "   - backend/scripts/DEPLOYMENT_COMPLETION_EXPLANATION.md"
echo "   - backend/scripts/BLOCKED_JOB_FINAL_REPORT.md"
echo "   - backend/scripts/FILE_PAIRING_ISSUE_REPORT.md"
echo ""
echo "✅ 部署完成后，运行以下命令验证:"
echo "   python backend/scripts/diagnose_blocked_job.py"


