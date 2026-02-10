#!/usr/bin/env bash

# Eventarc trigger setup script for AutoGrowth pipeline.
# Usage:
#   chmod +x infra/eventarc_setup.sh
#   PROJECT_ID=fleet-blend-469520-n7 REGION=us-central1 \
#   SERVICE_ACCOUNT=sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com \
#   ./infra/eventarc_setup.sh
#
# Required gcloud permissions:
#   - roles/eventarc.admin
#   - roles/run.admin
#   - roles/iam.serviceAccountUser
#   - roles/pubsub.admin (for implicit topics)

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-fleet-blend-469520-n7}"
REGION="${REGION:-us-central1}"
PIPELINE_GCS_SOURCE_BUCKET="${PIPELINE_GCS_SOURCE_BUCKET:-vigloo_source}"
TRIGGER_NAME="${TRIGGER_NAME:-drama-processor-trigger}"
RELAY_SERVICE_NAME="${RELAY_SERVICE_NAME:-drama-processor-relay-service}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-sa-run-prod@${PROJECT_ID}.iam.gserviceaccount.com}"

echo "🔧 使用的配置："
echo "  PROJECT_ID                = ${PROJECT_ID}"
echo "  REGION                    = ${REGION}"
echo "  PIPELINE_GCS_SOURCE_BUCKET= ${PIPELINE_GCS_SOURCE_BUCKET}"
echo "  TRIGGER_NAME              = ${TRIGGER_NAME}"
echo "  RELAY_SERVICE_NAME        = ${RELAY_SERVICE_NAME}"
echo "  SERVICE_ACCOUNT           = ${SERVICE_ACCOUNT}"
echo ""

echo "✅ 确保所需 API 已启用..."
gcloud services enable \
  eventarc.googleapis.com \
  run.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  --project="${PROJECT_ID}"

echo ""
echo "🔍 检查触发器是否已存在..."
if gcloud beta eventarc triggers describe "${TRIGGER_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "ℹ️  触发器 ${TRIGGER_NAME} 已存在。请确认其 destination 及过滤条件是否正确："
  gcloud beta eventarc triggers describe "${TRIGGER_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}"
  exit 0
fi

echo ""
echo "🚀 创建新的 Eventarc 触发器 ${TRIGGER_NAME}..."
echo "⚠️  注意：触发器将发送 HTTP 请求到 relay 服务，而不是直接触发 Job"
gcloud beta eventarc triggers create "${TRIGGER_NAME}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --destination-run-service="${RELAY_SERVICE_NAME}" \
  --destination-run-region="${REGION}" \
  --destination-run-path="/api/relay/event" \
  --service-account="${SERVICE_ACCOUNT}" \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=${PIPELINE_GCS_SOURCE_BUCKET}" \
  --event-filters-path-pattern="subject=objects/**/_PROCESS_NOW.txt" \
  --transport-topic="projects/${PROJECT_ID}/topics/${TRIGGER_NAME}-topic" \
  --labels="autogrowth=eventarc,worker=drama-processor"

echo ""
echo "✅ Eventarc 触发器创建完成。"
echo "📋 触发器配置："
echo "   - Destination: ${RELAY_SERVICE_NAME} (Cloud Run Service)"
echo "   - Path: /api/relay/event"
echo "   - Event: GCS object finalized (_PROCESS_NOW.txt)"
echo ""
echo "🔍 验证步骤："
echo "   1. 确认 relay 服务已部署：gcloud run services describe ${RELAY_SERVICE_NAME} --region=${REGION}"
echo "   2. 测试传输完成后，检查 relay 服务日志：gcloud run services logs read ${RELAY_SERVICE_NAME} --region=${REGION}"
echo "   3. 确认 process job 被正确触发并包含 JOB_ID 环境变量"

