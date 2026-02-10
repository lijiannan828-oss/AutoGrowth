#!/bin/bash

# 修复压制字幕功能权限脚本
# 用于授予必要的权限并检查配置

set -e

PROJECT_ID="autogrowth-477909"
SERVICE_ACCOUNT="sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"
REGION="us-central1"

echo "=========================================="
echo "修复压制字幕功能权限"
echo "=========================================="
echo ""
echo "项目 ID: ${PROJECT_ID}"
echo "服务账号: ${SERVICE_ACCOUNT}"
echo "区域: ${REGION}"
echo ""

# 检查是否已登录 gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ 错误: 未登录 gcloud，请先运行 'gcloud auth login'"
    exit 1
fi

echo "✅ gcloud 已登录"
echo ""

# 1. 授予 Cloud Run Invoker 权限
echo "1. 授予 Cloud Run Invoker 权限..."
if gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" \
    --condition=None > /dev/null 2>&1; then
    echo "   ✅ 已授予 roles/run.invoker"
else
    echo "   ⚠️  授予 roles/run.invoker 失败（可能已存在）"
fi
echo ""

# 2. 授予 Datastore User 权限（Firestore 写入）
echo "2. 授予 Datastore User 权限..."
if gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/datastore.user" \
    --condition=None > /dev/null 2>&1; then
    echo "   ✅ 已授予 roles/datastore.user"
else
    echo "   ⚠️  授予 roles/datastore.user 失败（可能已存在）"
fi
echo ""

# 3. 检查 Cloud Run Job 是否存在
echo "3. 检查 Cloud Run Job..."
JOB_NAME="process-worker"
if gcloud run jobs describe ${JOB_NAME} --region ${REGION} --project ${PROJECT_ID} > /dev/null 2>&1; then
    echo "   ✅ Job '${JOB_NAME}' 存在"
    FULL_JOB_NAME=$(gcloud run jobs describe ${JOB_NAME} --region ${REGION} --project ${PROJECT_ID} --format="value(name)")
    echo "   完整名称: ${FULL_JOB_NAME}"
    echo ""
    echo "   ⚠️  请确保 Cloud Run 服务配置了以下环境变量:"
    echo "   PROCESS_JOB_NAME=${FULL_JOB_NAME}"
else
    echo "   ❌ Job '${JOB_NAME}' 不存在"
    echo "   需要先创建 Cloud Run Job"
    echo ""
    echo "   创建 Job 的命令示例:"
    echo "   gcloud run jobs create ${JOB_NAME} \\"
    echo "     --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/autogrowth-docker/process-worker:latest \\"
    echo "     --region=${REGION} \\"
    echo "     --service-account=${SERVICE_ACCOUNT} \\"
    echo "     --project=${PROJECT_ID}"
fi
echo ""

# 4. 检查 Cloud Run 服务环境变量
echo "4. 检查 Cloud Run 服务环境变量..."
SERVICE_NAME="autogrowth-backend"
ENV_VARS=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format="value(spec.template.spec.containers[0].env)" 2>/dev/null || echo "")

if echo "${ENV_VARS}" | grep -q "PROCESS_JOB_NAME"; then
    echo "   ✅ PROCESS_JOB_NAME 已配置"
    PROCESS_JOB_VALUE=$(gcloud run services describe ${SERVICE_NAME} \
      --region ${REGION} \
      --project ${PROJECT_ID} \
      --format="value(spec.template.spec.containers[0].env[?(@.name=='PROCESS_JOB_NAME')].value)" 2>/dev/null || echo "")
    if [ -n "${PROCESS_JOB_VALUE}" ]; then
        echo "   值: ${PROCESS_JOB_VALUE}"
    fi
else
    echo "   ❌ PROCESS_JOB_NAME 未配置"
    echo ""
    echo "   需要在部署时添加此环境变量"
    echo "   更新 infra/github/workflows/backend-deploy.yaml 或 infra/cloudbuild.yaml"
fi
echo ""

# 5. 等待 IAM 策略传播
echo "5. 等待 IAM 策略传播..."
sleep 5
echo "   ✅ 等待完成"
echo ""

# 6. 验证权限
echo "6. 验证权限..."
echo ""

REQUIRED_ROLES=(
    "roles/run.invoker"
    "roles/datastore.user"
)

MISSING_ROLES=()

for role in "${REQUIRED_ROLES[@]}"; do
    if gcloud projects get-iam-policy ${PROJECT_ID} \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT} AND bindings.role:${role}" \
        --format="value(bindings.role)" | grep -q "${role}"; then
        echo "   ✅ ${role}"
    else
        echo "   ❌ ${role} - 缺失"
        MISSING_ROLES+=("${role}")
    fi
done

echo ""

if [ ${#MISSING_ROLES[@]} -eq 0 ]; then
    echo "✅ 所有必需的权限都已配置"
    echo ""
    echo "下一步:"
    echo "1. 确保 PROCESS_JOB_NAME 环境变量已配置"
    echo "2. 确保 Cloud Run Job 已创建"
    echo "3. 重新部署 Cloud Run 服务"
else
    echo "❌ 发现缺失的权限，请重新运行此脚本"
    exit 1
fi

