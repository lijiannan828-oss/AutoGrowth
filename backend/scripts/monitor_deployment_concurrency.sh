#!/bin/bash
# Monitor deployment status for concurrency control feature

set -e

echo "🔍 检查部署状态..."
echo ""

# Check GitHub Actions
echo "📋 GitHub Actions 状态:"
echo "   访问: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo ""

# Check Cloud Run Service
echo "📋 Cloud Run Service 状态:"
gcloud run services describe drama-processor-relay-service \
  --region=asia-northeast3 \
  --format="table(
    metadata.name,
    status.url,
    status.latestReadyRevisionName,
    status.conditions[0].status
  )" 2>/dev/null || echo "   ⚠️  无法获取服务状态"
echo ""

# Check environment variables
echo "📋 环境变量检查:"
ENV_VARS=$(gcloud run services describe drama-processor-relay-service \
  --region=asia-northeast3 \
  --format="value(spec.template.spec.containers[0].env)" 2>/dev/null || echo "")

if echo "$ENV_VARS" | grep -q "MAX_CONCURRENT_JOBS"; then
    echo "   ✅ MAX_CONCURRENT_JOBS 已配置"
    echo "$ENV_VARS" | grep "MAX_CONCURRENT_JOBS"
else
    echo "   ⚠️  MAX_CONCURRENT_JOBS 未找到（可能需要手动配置）"
fi
echo ""

# Check Firestore concurrency control document
echo "📋 Firestore 并发控制文档:"
python backend/scripts/check_concurrency_control.py 2>/dev/null || echo "   ⚠️  无法检查 Firestore 文档"
echo ""

echo "✅ 检查完成"
echo ""
echo "📄 详细验证指南: backend/scripts/DEPLOYMENT_VERIFICATION_CONCURRENCY.md"


