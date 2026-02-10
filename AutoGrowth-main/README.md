# AutoGrowth - 短剧投放命名与链接自动化生成器

## 项目简介

AutoGrowth 是一个用于自动化生成短剧投放命名和 OneLink 链接的工具，支持从 Google Sheets 读取剧目信息，并自动生成符合 SOP 规范的 Campaign、Ad Set 和 Ad 命名。

## 技术栈

### 前端
- Next.js 14 (React 18)
- TypeScript
- Ant Design + Tailwind CSS
- React Query

### 后端
- FastAPI (Python 3.11)
- SQLAlchemy + asyncpg
- Cloud SQL for PostgreSQL
- Google Sheets API
- APScheduler

### 部署
- Cloud Run (后端)
- Firebase Hosting (前端，待配置)
- GitHub Actions (CI/CD)
- Artifact Registry (Docker 镜像)

## 快速开始

### 本地开发

#### 后端
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 设置环境变量
export CLOUD_SQL_CONNECTION_NAME=your-connection-name
export DATABASE_NAME=auto_growth
export DATABASE_USER=appdev
export DATABASE_PASSWORD=your-password
export USE_IAM_AUTH=false
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
export GOOGLE_SHEETS_ID=your-sheets-id

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

## 部署

### 自动部署

项目配置了 GitHub Actions 自动部署流程：

1. 推送代码到 `main` 分支
2. GitHub Actions 自动触发
3. 构建 Docker 镜像
4. 推送到 Artifact Registry
5. 部署到 Cloud Run

### 手动部署

参考 `infra/DEPLOYMENT_SETUP.md` 了解详细部署步骤。

## 项目结构

```
AutoGrowth/
├── backend/              # 后端服务
│   ├── app/              # 应用代码
│   ├── scripts/          # 工具脚本
│   └── Dockerfile        # Docker 配置
├── frontend/             # 前端应用
│   └── src/              # 源代码
├── infra/                # 基础设施配置
│   ├── cloudbuild.yaml   # Cloud Build 配置
│   └── github/           # GitHub Actions workflows
└── .github/              # GitHub 配置
    └── workflows/        # CI/CD workflows
```

## 环境变量

### 后端环境变量

- `CLOUD_SQL_CONNECTION_NAME`: Cloud SQL 连接名称
- `DATABASE_NAME`: 数据库名称
- `DATABASE_USER`: 数据库用户名
- `DATABASE_PASSWORD`: 数据库密码
- `USE_IAM_AUTH`: 是否使用 IAM 认证
- `GOOGLE_APPLICATION_CREDENTIALS`: GCP 服务账号密钥路径
- `GOOGLE_SHEETS_ID`: Google Sheets ID

### 前端环境变量

- `NEXT_PUBLIC_API_URL`: 后端 API URL

## API 文档

部署后访问：
- Swagger UI: `https://your-service-url/docs`
- ReDoc: `https://your-service-url/redoc`

## 文档

- [部署指南](infra/DEPLOYMENT_SETUP.md)
- [GitHub 设置指南](infra/GITHUB_SETUP.md)
- [服务账号配置](infra/SERVICE_ACCOUNT_CONFIG.md)
- [Secret Manager 策略](infra/SECRET_MANAGER_POLICY.md)

## 许可证

内部项目

