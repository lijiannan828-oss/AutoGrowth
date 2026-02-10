# Secret Manager 管理策略

## 重要说明

### GitHub Secrets vs Secret Manager Secrets

**GitHub Secrets** (在 GitHub 仓库中配置):
- `GCP_SA_KEY` - GCP 服务账号密钥
- `POSTGRES_PASSWORD` - 数据库密码
- `CLOUD_SQL_CONN_NAME` - Cloud SQL 连接名称
- `FIREBASE_AUTOGROWTH_PROJECT_ID` - GCP 项目 ID
- `GOOGLE_SHEETS_ID` - Google Sheets ID (可选)

**Secret Manager Secrets** (在 GCP Secret Manager 中):
- `postgres-password` - 从 GitHub Secret `POSTGRES_PASSWORD` 创建
- `gcp-sa-key` - 从 GitHub Secret `GCP_SA_KEY` 创建

## 工作流程

### 首次部署
1. Workflow 从 GitHub Secrets 读取 `POSTGRES_PASSWORD` 和 `GCP_SA_KEY`
2. 检查 Secret Manager 中是否存在对应的 secrets
3. **如果不存在**，创建新的 secrets
4. **如果已存在**，跳过创建（不会覆盖）
5. 确保运行时服务账号有访问权限

### 后续部署
- **不会更新已存在的 secrets**
- 只确保运行时服务账号有访问权限

## 安全策略

### 不覆盖原则
- ✅ 如果 Secret Manager secret 已存在，**不会创建或更新**
- ✅ 只会在 secret 不存在时创建
- ✅ 不会添加新版本覆盖现有 secret

### 权限管理
- ✅ 自动授予运行时服务账号访问权限（idempotent 操作）
- ✅ 如果权限已存在，操作会安全跳过

## 手动更新 Secrets

如果需要更新 Secret Manager 中的 secrets，需要手动操作：

```bash
# 更新 postgres-password
echo -n "new-password" | gcloud secrets versions add postgres-password \
  --data-file=- \
  --project=autogrowth-477909

# 更新 gcp-sa-key
gcloud secrets versions add gcp-sa-key \
  --data-file=/path/to/new-service-account.json \
  --project=autogrowth-477909
```

## 验证 Secrets

```bash
# 列出所有 secrets
gcloud secrets list --project=autogrowth-477909

# 检查特定 secret 是否存在
gcloud secrets describe postgres-password --project=autogrowth-477909
gcloud secrets describe gcp-sa-key --project=autogrowth-477909

# 检查访问权限
gcloud secrets get-iam-policy postgres-password --project=autogrowth-477909
gcloud secrets get-iam-policy gcp-sa-key --project=autogrowth-477909
```

