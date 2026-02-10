# Cloud Run 部署配置指南

## 前置要求

### 1. GCP 项目配置
- 确保已启用以下 API：
  - Cloud Run API
  - Artifact Registry API
  - Cloud Build API
  - Cloud SQL Admin API
  - Secret Manager API

### 2. GitHub Secrets 配置
已在 GitHub Actions 中配置以下 secrets：
- `FIREBASE_AUTOGROWTH_PROJECT_ID`: GCP 项目 ID
- `GCP_SA_KEY`: GCP 服务账号 JSON 密钥
- `CLOUD_SQL_CONN_NAME`: Cloud SQL 连接名称（格式：`project:region:instance`）
- `POSTGRES_HOST`: PostgreSQL 主机地址
- `POSTGRES_PASSWORD`: 数据库密码
- `GOOGLE_SHEETS_ID`: Google Sheets ID（可选，如果未设置则从环境变量读取）

### 3. GCP Secret Manager 配置
需要在 Secret Manager 中创建以下 secrets：

```bash
# 设置项目 ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# 创建 Cloud SQL 连接名称 secret
echo -n "your-project:region:instance" | gcloud secrets create cloud-sql-conn-name \
  --data-file=- \
  --project=${PROJECT_ID}

# 创建数据库密码 secret
echo -n "your-database-password" | gcloud secrets create postgres-password \
  --data-file=- \
  --project=${PROJECT_ID}

# 创建 GCP 服务账号密钥 secret
gcloud secrets create gcp-sa-key \
  --data-file=path/to/service-account.json \
  --project=${PROJECT_ID}
```

### 4. 服务账号权限
确保用于部署的服务账号具有以下权限：
- Cloud Run Admin
- Artifact Registry Writer
- Secret Manager Secret Accessor
- Cloud SQL Client
- Service Account User

## 部署步骤

### 方式 1: 使用 GitHub Actions（推荐）

1. 推送代码到 GitHub
2. GitHub Actions 会自动触发部署
3. 查看部署状态：GitHub Actions → Backend Deploy to Cloud Run

### 方式 2: 使用 Cloud Build

```bash
# 设置变量
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export ARTIFACT_REGISTRY_REPO="autogrowth-docker"
export SERVICE_NAME="autogrowth-backend"
export CLOUD_SQL_CONN_NAME="your-project:region:instance"

# 提交构建
gcloud builds submit \
  --config=infra/cloudbuild.yaml \
  --substitutions=_REGION=${REGION},_ARTIFACT_REGISTRY_REPO=${ARTIFACT_REGISTRY_REPO},_SERVICE_NAME=${SERVICE_NAME},_CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONN_NAME} \
  --project=${PROJECT_ID}
```

### 方式 3: 本地构建和部署

```bash
# 1. 构建 Docker 镜像
cd backend
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${SERVICE_NAME}:latest .

# 2. 配置 Docker 认证
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 3. 推送镜像
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${SERVICE_NAME}:latest

# 4. 部署到 Cloud Run
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REGISTRY_REPO}/${SERVICE_NAME}:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --concurrency 80 \
  --set-env-vars "APP_ENV=production,LOG_LEVEL=INFO,DATABASE_NAME=auto_growth,DATABASE_USER=appdev,USE_IAM_AUTH=false" \
  --set-secrets "CLOUD_SQL_CONNECTION_NAME=cloud-sql-conn-name:latest,DATABASE_PASSWORD=postgres-password:latest,GOOGLE_APPLICATION_CREDENTIALS=gcp-sa-key:latest" \
  --add-cloudsql-instances ${CLOUD_SQL_CONN_NAME} \
  --project ${PROJECT_ID}
```

## 环境变量配置

### Cloud Run 环境变量
以下环境变量通过 `--set-env-vars` 设置：
- `APP_ENV`: 应用环境（production/staging/development）
- `LOG_LEVEL`: 日志级别（INFO/DEBUG/WARNING/ERROR）
- `DATABASE_NAME`: 数据库名称
- `DATABASE_USER`: 数据库用户名
- `USE_IAM_AUTH`: 是否使用 IAM 认证（false 表示使用密码认证）
- `GOOGLE_SHEETS_ID`: Google Sheets ID（可选）

### Secret Manager Secrets
以下敏感信息通过 `--set-secrets` 从 Secret Manager 读取：
- `CLOUD_SQL_CONNECTION_NAME`: Cloud SQL 连接名称
- `DATABASE_PASSWORD`: 数据库密码
- `GOOGLE_APPLICATION_CREDENTIALS`: GCP 服务账号密钥（JSON 格式）

## 健康检查

服务部署后，可以通过以下端点进行健康检查：
```
GET https://your-service-url/health
```

预期响应：
```json
{"status": "ok"}
```

## 监控和日志

### 查看日志
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
  --limit 50 \
  --project=${PROJECT_ID}
```

### 查看服务状态
```bash
gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project=${PROJECT_ID}
```

## 故障排查

### 1. 部署失败
- 检查服务账号权限
- 检查 Secret Manager secrets 是否存在
- 检查 Cloud SQL 连接名称格式是否正确

### 2. 服务无法启动
- 查看 Cloud Run 日志
- 检查环境变量和 secrets 是否正确
- 检查数据库连接配置

### 3. 健康检查失败
- 检查服务是否正常运行
- 检查端口配置（应该是 8000）
- 检查 `/health` 端点是否可访问

## 更新部署

### 更新代码
1. 推送代码到 GitHub
2. GitHub Actions 会自动重新构建和部署

### 更新环境变量
```bash
gcloud run services update ${SERVICE_NAME} \
  --update-env-vars "KEY=VALUE" \
  --region ${REGION} \
  --project=${PROJECT_ID}
```

### 更新 Secrets
```bash
# 更新 Secret Manager 中的 secret
echo -n "new-value" | gcloud secrets versions add secret-name \
  --data-file=- \
  --project=${PROJECT_ID}

# 重新部署服务以使用新版本
gcloud run services update ${SERVICE_NAME} \
  --update-secrets "SECRET_NAME=secret-name:latest" \
  --region ${REGION} \
  --project=${PROJECT_ID}
```

