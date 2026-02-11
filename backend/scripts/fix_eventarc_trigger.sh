#!/bin/bash
# Fix Eventarc trigger configuration

set -euo pipefail

PROJECT_ID="fleet-blend-469520-n7"
REGION="asia-northeast3"  # Trigger region
TARGET_REGION="us-central1"  # Target service region
TRIGGER_NAME="drama-processor-trigger"
RELAY_SERVICE_NAME="drama-processor-relay-service"
SERVICE_ACCOUNT="sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"
BUCKET="vigloo_source"

echo "🔧 修复 Eventarc 触发器配置"
echo "   Trigger: ${TRIGGER_NAME}"
echo "   Region: ${REGION}"
echo "   Target: ${RELAY_SERVICE_NAME} (${TARGET_REGION})"
echo ""

echo "📋 当前配置："
gcloud eventarc triggers describe "${TRIGGER_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="yaml(destination.cloudRun.path,eventFilters)" || true

echo ""
echo "⚠️  发现的问题："
echo "   1. 路径配置为 '/'，应该是 '/api/relay/event'"
echo "   2. 缺少路径过滤器来匹配 '_PROCESS_NOW.txt'"
echo ""

echo "🔄 更新触发器配置..."
echo "   注意：Eventarc 触发器不支持直接更新路径和过滤器"
echo "   需要删除并重新创建"
echo ""

read -p "是否继续删除并重新创建触发器？(y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ 取消操作"
    exit 1
fi

echo ""
echo "🗑️  删除现有触发器..."
gcloud eventarc triggers delete "${TRIGGER_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet || echo "⚠️  触发器可能不存在或已删除"

echo ""
echo "🚀 创建新触发器（正确配置）..."
gcloud eventarc triggers create "${TRIGGER_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --destination-run-service="${RELAY_SERVICE_NAME}" \
  --destination-run-region="${TARGET_REGION}" \
  --destination-run-path="/api/relay/event" \
  --service-account="${SERVICE_ACCOUNT}" \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=${BUCKET}" \
  --event-filters-path-pattern="subject=objects/**/_PROCESS_NOW.txt" \
  --transport-topic="projects/${PROJECT_ID}/topics/${TRIGGER_NAME}-topic" \
  --labels="autogrowth=eventarc,worker=drama-processor"

echo ""
echo "✅ 触发器配置完成"
echo ""
echo "📋 验证配置："
gcloud eventarc triggers describe "${TRIGGER_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="yaml(destination.cloudRun.path,eventFilters)"

echo ""
echo "✅ 修复完成！"
echo ""
echo "📝 下一步："
echo "   1. 等待几秒钟让触发器生效"
echo "   2. 可以手动创建一个测试信号文件来验证"
echo "   3. 或者等待下一个传输任务完成"

