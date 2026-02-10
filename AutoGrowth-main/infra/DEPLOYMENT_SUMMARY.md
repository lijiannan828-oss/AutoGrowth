# Cloud Run 部署配置总结

## ✅ 已完成的配置

### 1. 项目信息
- **GCP 项目 ID**: `autogrowth-477909`
- **区域**: `us-central1`
- **Artifact Registry 仓库**: `autogrowth-docker`
- **Cloud Run 服务**: `autogrowth-backend`
- **Cloud SQL 连接**: `fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`

### 2. 已创建的文件

#### 配置文件
- ✅ `backend/Dockerfile` - 优化的多阶段构建 Dockerfile
- ✅ `infra/cloudbuild.yaml` - Cloud Build 配置
- ✅ `.github/workflows/backend-deploy.yaml` - GitHub Actions 工作流
- ✅ `.gitignore` - Git 忽略文件配置

#### 文档
- ✅ `infra/DEPLOYMENT_SETUP.md` - 部署设置指南
- ✅ `infra/SETUP_CHECKLIST.md` - 设置检查清单
- ✅ `infra/GITHUB_SETUP.md` - GitHub 仓库设置指南

### 3. 配置特性

#### Dockerfile
- 多阶段构建优化镜像大小
- 健康检查配置
- 安全优化（非 root 用户运行）

#### GitHub Actions Workflow
- 自动构建 Docker 镜像
- 自动创建 Artifact Registry 仓库（如果不存在）
- 自动创建/更新 Secret Manager secrets
- 自动部署到 Cloud Run
- 自动健康检查

#### Cloud Run 配置
- 内存: 512Mi
- CPU: 1
- 最小实例: 0（按需启动）
- 最大实例: 10
- 超时: 300 秒
- 并发: 80
- **运行时服务账号**: `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`

## 📋 下一步操作

### 1. 设置 GitHub Secrets

在 GitHub 仓库中添加以下 Secrets：

1. **`FIREBASE_AUTOGROWTH_PROJECT_ID`**: `autogrowth-477909`
2. **`GCP_SA_KEY`**: GCP 服务账号 JSON 密钥（完整内容）
3. **`CLOUD_SQL_CONN_NAME`**: `fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`
4. **`POSTGRES_PASSWORD`**: 数据库密码
5. **`GOOGLE_SHEETS_ID`**: Google Sheets ID（可选）

### 2. 初始化 Git 仓库并推送

```bash
cd /Users/mac/AutoGrowth

# 初始化 Git（如果还没有）
git init

# 添加远程仓库
git remote add origin https://github.com/lijiannan828/AutoGrowth.git

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: AutoGrowth project with Cloud Run deployment"

# 推送到 main 分支
git branch -M main
git push -u origin main
```

### 3. 验证部署

推送代码后：
1. 访问 GitHub 仓库 → Actions 标签
2. 查看 "Backend Deploy to Cloud Run" workflow 执行情况
3. 等待部署完成（约 5-10 分钟）
4. 获取 Cloud Run 服务 URL 并测试健康检查

## 🔧 服务账号权限要求

### 部署服务账号（GCP_SA_KEY）
用于 GitHub Actions 认证和部署操作，需要以下 IAM 角色：

- `roles/run.admin` - Cloud Run Admin
- `roles/artifactregistry.writer` - Artifact Registry Writer
- `roles/secretmanager.secretAccessor` - Secret Manager Secret Accessor
- `roles/secretmanager.admin` - Secret Manager Admin（用于创建 secrets）
- `roles/cloudsql.client` - Cloud SQL Client
- `roles/iam.serviceAccountUser` - Service Account User

### 运行时服务账号（sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com）
用于 Cloud Run 服务运行时，需要以下 IAM 角色：

- `roles/cloudsql.client` - Cloud SQL Client
- `roles/secretmanager.secretAccessor` - Secret Manager Secret Accessor

**注意**: 运行时服务账号已在配置文件中指定，无需在 GitHub Secrets 中额外配置。

## 📝 环境变量配置

### Cloud Run 环境变量（通过 `--set-env-vars`）
- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `DATABASE_NAME=auto_growth`
- `DATABASE_USER=appdev`
- `USE_IAM_AUTH=false`
- `CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`
- `GOOGLE_SHEETS_ID` (从 GitHub Secrets 读取)

### Secret Manager Secrets（通过 `--set-secrets`）
- `DATABASE_PASSWORD` - 从 `postgres-password` secret 读取
- `GOOGLE_APPLICATION_CREDENTIALS` - 从 `gcp-sa-key` secret 读取

## 🚀 部署流程

1. **代码推送** → GitHub 检测到 `backend/` 或 `infra/` 目录变更
2. **GitHub Actions 触发** → 开始构建和部署流程
3. **Docker 构建** → 在 GitHub Actions runner 上构建镜像
4. **推送到 Artifact Registry** → 镜像推送到 `us-central1-docker.pkg.dev/autogrowth-477909/autogrowth-docker/autogrowth-backend`
5. **创建/更新 Secrets** → 在 Secret Manager 中创建或更新 secrets
6. **部署到 Cloud Run** → 使用新镜像部署服务
7. **健康检查** → 验证服务是否正常运行

## 📊 监控和日志

### 查看日志
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=autogrowth-backend" \
  --limit 50 \
  --project=autogrowth-477909
```

### 查看服务状态
```bash
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909
```

### 获取服务 URL
```bash
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)'
```

## ⚠️ 注意事项

1. **首次部署**：
   - Artifact Registry 仓库会自动创建
   - Secret Manager secrets 会自动创建
   - 如果创建失败，请检查服务账号权限

2. **数据库连接**：
   - 确保 Cloud SQL 实例允许 Cloud Run 连接
   - 检查数据库用户和密码是否正确

3. **服务账号密钥**：
   - `GCP_SA_KEY` secret 应该是完整的 JSON 文件内容
   - 确保服务账号有足够权限

4. **环境变量**：
   - 敏感信息（密码、密钥）通过 Secret Manager 管理
   - 非敏感信息通过环境变量传递

## 📚 相关文档

- `infra/DEPLOYMENT_SETUP.md` - 详细部署设置指南
- `infra/GITHUB_SETUP.md` - GitHub 仓库设置指南
- `infra/SETUP_CHECKLIST.md` - 设置检查清单

