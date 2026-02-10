#!/bin/bash

# 服务账号权限验证脚本
# 用于验证 sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com 的权限配置

set -e

PROJECT_ID="autogrowth-477909"
SERVICE_ACCOUNT="sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"
REGION="us-central1"
CLOUD_SQL_CONN_NAME="fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod"

echo "=========================================="
echo "服务账号权限验证"
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

# 1. 检查服务账号是否存在
echo "1. 检查服务账号是否存在..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT} --project=${PROJECT_ID} > /dev/null 2>&1; then
    echo "   ✅ 服务账号存在"
else
    echo "   ❌ 服务账号不存在"
    echo "   请创建服务账号或检查服务账号名称是否正确"
    exit 1
fi
echo ""

# 2. 检查 IAM 角色
echo "2. 检查服务账号的 IAM 角色..."
echo "   需要的角色:"
echo "   - roles/cloudsql.client"
echo "   - roles/secretmanager.secretAccessor"
echo ""

REQUIRED_ROLES=(
    "roles/cloudsql.client"
    "roles/secretmanager.secretAccessor"
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

if [ ${#MISSING_ROLES[@]} -gt 0 ]; then
    echo ""
    echo "   ⚠️  发现缺失的角色，请运行以下命令授予权限:"
    for role in "${MISSING_ROLES[@]}"; do
        echo "   gcloud projects add-iam-policy-binding ${PROJECT_ID} \\"
        echo "     --member=\"serviceAccount:${SERVICE_ACCOUNT}\" \\"
        echo "     --role=\"${role}\""
    done
else
    echo ""
    echo "   ✅ 所有必需的角色都已配置"
fi
echo ""

# 3. 检查 Secret Manager secrets 的 IAM 策略
echo "3. 检查 Secret Manager secrets 的 IAM 策略..."
echo "   需要的 secrets:"
echo "   - postgres-password"
echo "   - gcp-sa-key"
echo ""

REQUIRED_SECRETS=(
    "postgres-password"
    "gcp-sa-key"
)

MISSING_SECRET_ACCESS=()

for secret in "${REQUIRED_SECRETS[@]}"; do
    # 检查 secret 是否存在
    if gcloud secrets describe ${secret} --project=${PROJECT_ID} > /dev/null 2>&1; then
        echo "   ✅ Secret '${secret}' 存在"
        
        # 检查服务账号是否有访问权限
        if gcloud secrets get-iam-policy ${secret} --project=${PROJECT_ID} \
            --flatten="bindings[].members" \
            --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}" \
            --format="value(bindings.role)" | grep -q "roles/secretmanager.secretAccessor"; then
            echo "      ✅ 服务账号有访问权限"
        else
            echo "      ❌ 服务账号没有访问权限"
            MISSING_SECRET_ACCESS+=("${secret}")
        fi
    else
        echo "   ⚠️  Secret '${secret}' 不存在（将在首次部署时创建）"
    fi
done

if [ ${#MISSING_SECRET_ACCESS[@]} -gt 0 ]; then
    echo ""
    echo "   ⚠️  发现缺失的 secret 访问权限，请运行以下命令授予权限:"
    for secret in "${MISSING_SECRET_ACCESS[@]}"; do
        echo "   gcloud secrets add-iam-policy-binding ${secret} \\"
        echo "     --member=\"serviceAccount:${SERVICE_ACCOUNT}\" \\"
        echo "     --role=\"roles/secretmanager.secretAccessor\" \\"
        echo "     --project=${PROJECT_ID}"
    done
else
    echo ""
    echo "   ✅ 所有必需的 secret 访问权限都已配置"
fi
echo ""

# 4. 检查 Cloud SQL 实例
echo "4. 检查 Cloud SQL 实例..."
if gcloud sql instances describe yvideo-factory-db-prod --project=fleet-blend-469520-n7 > /dev/null 2>&1; then
    echo "   ✅ Cloud SQL 实例存在"
    
    # 检查是否启用了 Cloud SQL 连接
    echo "   ℹ️  确保 Cloud SQL 实例允许 Cloud Run 连接"
    echo "   ℹ️  如果使用私有 IP，需要配置 VPC 连接器"
else
    echo "   ⚠️  无法访问 Cloud SQL 实例（可能需要跨项目权限）"
    echo "   ℹ️  请确保服务账号有权限连接到 Cloud SQL"
fi
echo ""

# 5. 检查 Artifact Registry 仓库
echo "5. 检查 Artifact Registry 仓库..."
ARTIFACT_REGISTRY_REPO="autogrowth-docker"
if gcloud artifacts repositories describe ${ARTIFACT_REGISTRY_REPO} \
    --location=${REGION} \
    --project=${PROJECT_ID} > /dev/null 2>&1; then
    echo "   ✅ Artifact Registry 仓库存在"
else
    echo "   ℹ️  Artifact Registry 仓库不存在（将在首次部署时自动创建）"
fi
echo ""

# 总结
echo "=========================================="
echo "验证总结"
echo "=========================================="

if [ ${#MISSING_ROLES[@]} -eq 0 ] && [ ${#MISSING_SECRET_ACCESS[@]} -eq 0 ]; then
    echo "✅ 所有权限配置正确！"
    echo ""
    echo "可以继续进行部署。"
    exit 0
else
    echo "⚠️  发现权限配置问题，请先修复后再进行部署。"
    echo ""
    echo "修复命令已在上面的输出中提供。"
    exit 1
fi

