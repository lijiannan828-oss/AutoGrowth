# GitHub 仓库设置指南

## 前置要求

### 1. 创建 GitHub 仓库

1. 登录 GitHub (https://github.com)
2. 点击右上角 "+" → "New repository"
3. 仓库名称：`AutoGrowth` (或你喜欢的名称)
4. 设置为 Private 或 Public（根据需求）
5. **不要**初始化 README、.gitignore 或 license（因为本地已有代码）

### 2. 配置 GitHub Secrets

在仓库设置中添加以下 Secrets：

**Settings → Secrets and variables → Actions → New repository secret**

#### 必需的 Secrets：

1. **`FIREBASE_AUTOGROWTH_PROJECT_ID`**
   - 值：`autogrowth-477909`
   - 说明：GCP 项目 ID

2. **`GCP_SA_KEY`**
   - 值：GCP 服务账号的完整 JSON 密钥内容
   - 说明：用于认证和部署的服务账号密钥
   - 获取方式：
     ```bash
     # 在 GCP Console 中创建服务账号并下载密钥
     # 或使用 gcloud 命令
     gcloud iam service-accounts keys create key.json \
       --iam-account=your-service-account@autogrowth-477909.iam.gserviceaccount.com
     ```

3. **`CLOUD_SQL_CONN_NAME`**
   - 值：`fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`
   - 说明：Cloud SQL 连接名称

4. **`POSTGRES_PASSWORD`**
   - 值：数据库密码
   - 说明：PostgreSQL 数据库密码

5. **`POSTGRES_HOST`** (可选，如果使用)
   - 值：数据库主机地址
   - 说明：PostgreSQL 主机地址

6. **`GOOGLE_SHEETS_ID`** (可选)
   - 值：Google Sheets ID
   - 说明：如果已配置，可以添加此 secret

### 3. 服务账号权限

确保用于部署的 GCP 服务账号具有以下 IAM 角色：

- `roles/run.admin` - Cloud Run Admin
- `roles/artifactregistry.writer` - Artifact Registry Writer
- `roles/secretmanager.secretAccessor` - Secret Manager Secret Accessor
- `roles/cloudsql.client` - Cloud SQL Client
- `roles/iam.serviceAccountUser` - Service Account User

## 初始化 Git 仓库

### 1. 检查 .gitignore

确保 `.gitignore` 文件包含以下内容：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# Node
node_modules/
.next/
out/
dist/

# Environment variables
.env
.env.local
.env*.local

# Service account keys
service-account.json
*.json
!package.json
!package-lock.json
!tsconfig.json

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# Temporary files
tmp/
temp/
```

### 2. 初始化并推送代码

```bash
# 在项目根目录执行
cd /Users/mac/AutoGrowth

# 初始化 Git 仓库（如果还没有）
git init

# 添加远程仓库（替换为你的 GitHub 仓库 URL）
git remote add origin https://github.com/lijiannan828/AutoGrowth.git

# 或者使用 SSH
# git remote add origin git@github.com:lijiannan828/AutoGrowth.git

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: AutoGrowth project with Cloud Run deployment"

# 推送到 main 分支
git branch -M main
git push -u origin main
```

## 验证部署

### 1. 检查 GitHub Actions

1. 推送代码后，访问 GitHub 仓库
2. 点击 "Actions" 标签
3. 查看 "Backend Deploy to Cloud Run" workflow
4. 确认所有步骤都成功执行

### 2. 检查 Cloud Run 服务

```bash
# 查看服务状态
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909

# 获取服务 URL
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)'
```

### 3. 测试健康检查

```bash
# 获取服务 URL
SERVICE_URL=$(gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)')

# 测试健康检查端点
curl ${SERVICE_URL}/health
```

预期响应：
```json
{"status": "ok"}
```

## 故障排查

### 1. GitHub Actions 失败

**问题**: 认证失败
- 检查 `GCP_SA_KEY` secret 是否正确
- 检查服务账号是否有足够权限

**问题**: Artifact Registry 创建失败
- 检查服务账号是否有 `roles/artifactregistry.admin` 权限
- 或手动创建仓库：
  ```bash
  gcloud artifacts repositories create autogrowth-docker \
    --repository-format=docker \
    --location=us-central1 \
    --project=autogrowth-477909
  ```

**问题**: Secret Manager 创建失败
- 检查服务账号是否有 `roles/secretmanager.admin` 权限
- 或手动创建 secrets（参考 `DEPLOYMENT_SETUP.md`）

### 2. Cloud Run 部署失败

**问题**: 镜像拉取失败
- 检查 Artifact Registry 仓库是否存在
- 检查镜像是否成功推送

**问题**: 服务启动失败
- 查看 Cloud Run 日志：
  ```bash
  gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=autogrowth-backend" \
    --limit 50 \
    --project=autogrowth-477909
  ```

### 3. 数据库连接失败

**问题**: 无法连接到 Cloud SQL
- 检查 Cloud SQL 实例是否允许 Cloud Run 连接
- 检查 `CLOUD_SQL_CONN_NAME` 格式是否正确
- 检查数据库用户和密码是否正确

## 后续步骤

1. ✅ 代码已推送到 GitHub
2. ✅ GitHub Actions 自动部署成功
3. ✅ Cloud Run 服务正常运行
4. ⏳ 配置自定义域名（可选）
5. ⏳ 设置监控和告警（可选）
6. ⏳ 配置 CI/CD 流程优化（可选）

