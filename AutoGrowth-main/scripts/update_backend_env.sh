#!/bin/bash
# ============================================
# 更新 Backend API 环境变量脚本
# ============================================
# 用途：更新 Cloud Run Backend API 服务的环境变量
# 使用方法：
#   1. 修改下面的 FOLDER_ID 变量为实际的 Google Drive Folder ID
#   2. 运行：bash scripts/update_backend_env.sh
# ============================================

set -e

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
SERVICE_NAME="backend"  # 修改为你的实际服务名称

# ============================================
# 🔧 配置区域：请修改为实际的 Google Drive Folder ID
# ============================================
KR_FOLDER_ID="YOUR_KR_PROGRAMS_FOLDER_ID"
JP_FOLDER_ID="YOUR_JP_PROGRAMS_FOLDER_ID"
US_FOLDER_ID="YOUR_US_PROGRAMS_FOLDER_ID"

# ============================================
# 检查配置
# ============================================
if [[ "$KR_FOLDER_ID" == "YOUR_KR_PROGRAMS_FOLDER_ID" ]]; then
    echo "❌ 错误：请先修改脚本中的 Folder ID 配置"
    echo "   请编辑 scripts/update_backend_env.sh 文件"
    echo "   将 YOUR_*_FOLDER_ID 替换为实际的 Google Drive Folder ID"
    exit 1
fi

echo "=========================================="
echo "  更新 Backend API 环境变量"
echo "=========================================="
echo ""
echo "项目 ID: $PROJECT_ID"
echo "区域: $REGION"
echo "服务名称: $SERVICE_NAME"
echo ""
echo "Google Drive 映射配置："
echo "  KR Programs: $KR_FOLDER_ID"
echo "  JP Programs: $JP_FOLDER_ID"
echo "  US Programs: $US_FOLDER_ID"
echo ""

# 构建 PIPELINE_GDRIVE_ROOTS 环境变量
GDRIVE_ROOTS="KR Programs:${KR_FOLDER_ID},JP Programs:${JP_FOLDER_ID},US Programs:${US_FOLDER_ID}"

echo "📋 步骤 1: 检查服务是否存在..."
if gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "✅ 服务存在"
else
    echo "❌ 服务不存在！"
    echo "   请检查服务名称是否正确"
    echo "   可用的服务列表："
    gcloud run services list --region=$REGION --project=$PROJECT_ID
    exit 1
fi
echo ""

echo "📋 步骤 2: 更新环境变量..."
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --set-env-vars="PIPELINE_GDRIVE_ROOTS=${GDRIVE_ROOTS}" \
  --set-env-vars="PIPELINE_GCS_SOURCE_BUCKET=vigloo_source" \
  --set-env-vars="PIPELINE_GCS_PROCESSED_BUCKET=vigloo_processed" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="GCP_REGION=${REGION}" \
  --set-env-vars="FIRESTORE_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="FIRESTORE_DATABASE=(default)" \
  --set-env-vars="APP_ENV=production"

if [ $? -eq 0 ]; then
    echo "✅ 环境变量更新成功！"
else
    echo "❌ 环境变量更新失败"
    exit 1
fi
echo ""

echo "📋 步骤 3: 验证配置..."
echo "当前环境变量："
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
echo ""

echo "=========================================="
echo "  配置完成！"
echo "=========================================="
echo ""
echo "🔗 快速访问链接："
echo "   https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}?project=${PROJECT_ID}"
echo ""
echo "💡 下一步："
echo "   1. 访问前端 Transfer Planner 界面"
echo "   2. 验证是否能看到 KR/JP/US Programs 目录"
echo "   3. 测试创建传输任务"
echo ""

