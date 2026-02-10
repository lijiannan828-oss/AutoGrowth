#!/bin/bash

# 修复 Artifact Registry 权限脚本

PROJECT_ID="autogrowth-477909"
SERVICE_ACCOUNT="sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"

echo "🔧 修复 Artifact Registry 权限"
echo "================================"
echo ""
echo "项目 ID: ${PROJECT_ID}"
echo "服务账号: ${SERVICE_ACCOUNT}"
echo ""

# 检查当前权限
echo "📋 检查当前权限..."
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}" \
  --format="table(bindings.role)" 2>/dev/null | grep -i artifact || echo "未找到 Artifact Registry 相关权限"

echo ""
echo "🔑 授予 Artifact Registry 权限..."

# 授予 Artifact Registry Writer 权限（用于推送镜像）
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.writer" \
  --condition=None

# 授予 Artifact Registry Admin 权限（用于创建仓库）
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.admin" \
  --condition=None

echo ""
echo "✅ 权限已授予"
echo ""
echo "📋 验证权限..."
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}" \
  --format="table(bindings.role)" | grep -i artifact

echo ""
echo "✅ 完成！"






