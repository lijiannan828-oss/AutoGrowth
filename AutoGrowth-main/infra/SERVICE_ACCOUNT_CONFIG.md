# 服务账号配置说明

## 服务账号信息

### 生产环境服务账号
- **服务账号邮箱**: `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`
- **用途**: Cloud Run 服务运行时使用的服务账号
- **配置位置**: 
  - GitHub Actions workflow: `.github/workflows/backend-deploy.yaml`
  - Cloud Build 配置: `infra/cloudbuild.yaml`

## 配置说明

### 1. GitHub Actions 中的使用

在 `.github/workflows/backend-deploy.yaml` 中：

```yaml
env:
  SERVICE_ACCOUNT: sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com
```

部署 Cloud Run 时使用：
```bash
gcloud run deploy ... --service-account ${SERVICE_ACCOUNT}
```

### 2. Cloud Build 中的使用

在 `infra/cloudbuild.yaml` 中：

```yaml
substitutions:
  _SERVICE_ACCOUNT: 'sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com'
```

### 3. 服务账号权限要求

`sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 需要以下 IAM 角色：

#### Cloud Run 运行时权限
- `roles/cloudsql.client` - 连接 Cloud SQL
- `roles/secretmanager.secretAccessor` - 读取 Secret Manager secrets
- `roles/storage.objectViewer` - 如果需要访问 Cloud Storage（可选）

#### 部署权限（用于 GitHub Actions 中的 GCP_SA_KEY）
用于部署的服务账号（`GCP_SA_KEY` 中的服务账号）需要：
- `roles/run.admin` - 部署和管理 Cloud Run 服务
- `roles/artifactregistry.writer` - 推送 Docker 镜像
- `roles/secretmanager.admin` - 创建和管理 secrets
- `roles/iam.serviceAccountUser` - 使用服务账号运行服务

## 重要说明

### 1. 两个不同的服务账号

**部署服务账号**（`GCP_SA_KEY`）:
- 用于 GitHub Actions 认证和部署操作
- 需要部署和管理权限

**运行时服务账号**（`sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`）:
- 用于 Cloud Run 服务运行时
- 只需要运行时权限（连接数据库、读取 secrets 等）
- 通过 `--service-account` 参数指定

### 2. 为什么需要指定运行时服务账号？

- **最小权限原则**: 运行时服务账号只需要运行时的最小权限
- **安全隔离**: 部署权限和运行时权限分离
- **审计追踪**: 可以清楚地区分部署操作和运行时操作

### 3. Secret Manager 访问

确保 `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 对以下 secrets 有访问权限：

```bash
# 授予访问权限
gcloud secrets add-iam-policy-binding postgres-password \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=autogrowth-477909

gcloud secrets add-iam-policy-binding gcp-sa-key \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=autogrowth-477909
```

### 4. Cloud SQL 连接

确保 `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 可以连接 Cloud SQL：

```bash
# 如果使用 IAM 认证，需要创建 IAM 数据库用户
# 如果使用密码认证（当前配置），确保服务账号有 Cloud SQL Client 角色即可
```

## 验证配置

### 检查服务账号权限

```bash
# 查看服务账号的 IAM 角色
gcloud projects get-iam-policy autogrowth-477909 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

### 检查 Cloud Run 服务配置

```bash
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="value(spec.template.spec.serviceAccountName)"
```

应该返回：`sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`

## 故障排查

### 问题：服务启动失败，提示权限不足

**解决方案**:
1. 检查服务账号是否有 `roles/cloudsql.client` 角色
2. 检查服务账号是否有 `roles/secretmanager.secretAccessor` 角色
3. 检查 Secret Manager secrets 的 IAM 策略

### 问题：无法连接 Cloud SQL

**解决方案**:
1. 检查 Cloud SQL 实例是否允许 Cloud Run 连接
2. 检查服务账号是否有 `roles/cloudsql.client` 角色
3. 如果使用 IAM 认证，确保已创建 IAM 数据库用户

### 问题：无法读取 Secret Manager secrets

**解决方案**:
1. 检查服务账号是否有 `roles/secretmanager.secretAccessor` 角色
2. 检查 secrets 的 IAM 策略是否包含该服务账号
3. 验证 secret 名称是否正确

