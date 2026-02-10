#!/bin/bash

# 服务账号权限修复脚本
# 用于授予 sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com 所需的权限

set -e

PROJECT_ID="autogrowth-477909"
SERVICE_ACCOUNT="sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"

echo "=========================================="
echo "服务账号权限修复"
echo "=========================================="
echo ""
echo "项目 ID: ${PROJECT_ID}"
echo "服务账号: ${SERVICE_ACCOUNT}"
echo ""

# 检查是否已登录 gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ 错误: 未登录 gcloud，请先运行 'gcloud auth login'"
    exit 1
fi

# 1. 授予 Cloud SQL Client 角色
echo "1. 授予 Cloud SQL Client 角色..."
if gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client" \
    --condition=None > /dev/null 2>&1; then
    echo "   ✅ 已授予 roles/cloudsql.client"
else
    echo "   ⚠️  授予 roles/cloudsql.client 失败（可能已存在）"
fi
echo ""

# 2. 授予 Secret Manager Secret Accessor 角色
echo "2. 授予 Secret Manager Secret Accessor 角色..."
if gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None > /dev/null 2>&1; then
    echo "   ✅ 已授予 roles/secretmanager.secretAccessor"
else
    echo "   ⚠️  授予 roles/secretmanager.secretAccessor 失败（可能已存在）"
fi
echo ""

# 3. 等待 IAM 策略传播（通常需要几秒钟）
echo "3. 等待 IAM 策略传播..."
sleep 5
echo "   ✅ 等待完成"
echo ""

# 4. 验证权限
echo "4. 验证权限..."
echo ""

REQUIRED_ROLES=(
    "roles/cloudsql.client"
    "roles/secretmanager.secretAccessor"
)

ALL_GRANTED=true

for role in "${REQUIRED_ROLES[@]}"; do
    if gcloud projects get-iam-policy ${PROJECT_ID} \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT} AND bindings.role:${role}" \
        --format="value(bindings.role)" | grep -q "${role}"; then
        echo "   ✅ ${role}"
    else
        echo "   ❌ ${role} - 仍然缺失"
        ALL_GRANTED=false
    fi
done

echo ""
echo "=========================================="
echo "修复完成"
echo "=========================================="

if [ "$ALL_GRANTED" = true ]; then
    echo "✅ 所有权限已成功授予！"
    echo ""
    echo "可以继续进行部署。"
    exit 0
else
    echo "⚠️  部分权限可能未正确授予，请检查是否有足够的权限执行这些操作。"
    echo ""
    echo "如果权限授予失败，可能需要："
    echo "1. 确保当前用户有 'roles/resourcemanager.projectIamAdmin' 角色"
    echo "2. 或者联系项目管理员授予权限"
    exit 1
fi

