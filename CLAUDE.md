# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言规范

- **永远使用中文**进行所有交流和文档编写
- 每个文件不要超过 1000 行

## 常用命令

### Frontend (frontend/)

```bash
cd frontend
npm install              # 安装依赖
npm run dev              # 启动开发服务器 (端口 3001, 绑定 0.0.0.0)
npm run build            # 生产构建 (standalone 模式)
npm run start            # 启动生产服务器
npm run lint             # ESLint 检查
```

### Backend (backend/)

```bash
cd backend
pip install -r requirements.txt          # 安装依赖
uvicorn app.main:app --reload --port 8000  # 启动开发服务器
```

### 数据库迁移 (Alembic)

```bash
cd backend
alembic revision --autogenerate -m "描述"  # 生成迁移
alembic upgrade head                       # 执行迁移
```

### 部署

- GitHub Actions 自动部署到 Google Cloud Run
- `main` 分支 → 生产环境
- `staging` 分支 → 预发布环境
- 后端也可通过 `backend/cloudbuild.yaml` 用 Cloud Build 部署

## 架构概览

全栈应用，前后端分离，部署在 Google Cloud Platform 上。

### Frontend — Next.js 16 (App Router) + TypeScript

- UI 框架: Ant Design 5 + Tailwind CSS 4
- 状态管理: TanStack React Query（服务端状态）+ React Context（认证状态）
- 表单: React Hook Form + Zod 校验
- 认证: Firebase Auth，token 存储在 localStorage，通过 axios 拦截器自动附加
- API 通信: axios 客户端 ([api-client.ts](frontend/src/lib/api-client.ts))，基础 URL 由 `NEXT_PUBLIC_API_URL` 控制
- Next.js rewrites 将 `/api/v1/*` 代理到后端

### Backend — FastAPI + Python 3.11

- 入口: [main.py](backend/app/main.py) — lifespan 管理数据库、Firestore、调度器的初始化和关闭
- API 路由全部挂载在 `/api/v1` 前缀下 ([router.py](backend/app/api/v1/router.py))
- 配置: Pydantic Settings，通过 `validation_alias` 映射环境变量 ([config.py](backend/app/core/config.py))
- 数据库: PostgreSQL (Cloud SQL)，通过 SQLAlchemy 2.0 async + asyncpg，支持 Cloud SQL Connector 和直连两种模式
- ORM 模型在 `backend/app/models/`，Pydantic schema 在 `backend/app/schemas/`
- 认证: Firebase token 验证，开发环境支持 `dev-token-123` 跳过验证 ([deps.py](backend/app/api/deps.py))
- 邮箱域名白名单控制访问权限 (`ALLOWED_EMAIL_DOMAINS`)

### 分层结构 (Backend)

```
api/v1/     → 路由层 (HTTP 入口，参数校验)
schemas/    → Pydantic 请求/响应模型
services/   → 业务逻辑层
repositories/ → 数据访问层
models/     → SQLAlchemy ORM 模型
core/       → 基础设施 (数据库、Firestore、配置、安全、调度器)
workers/    → 独立部署的后台任务进程
```

### Workers — 独立 Cloud Run Jobs

`backend/app/workers/` 下有 5 个独立 worker，各自有 `main.py` 入口，作为单独的 Cloud Run Job 部署:

- `fission/` — 视频裂变处理 (贴纸叠加、GIF 动画、Whisper 字幕生成)
- `ai_video/` — AI 视频生成
- `transfer/` — Google Drive → GCS 文件传输
- `process/` — 通用视频处理
- `zip_compress/` — 视频压缩打包

Workers 通过 Firestore 跟踪任务状态，使用 GCS 存储输入/输出文件。

### 外部服务集成

- Google Cloud Storage — 多个 bucket 用于不同功能 (fission、subtitle、tts、pipeline)
- Google Firestore — 任务状态跟踪、实时数据
- Google Sheets — 作为数据源 (通过 gspread)
- Google Drive — 文件发现和传输 (pipeline 功能)
- Google OAuth — 用户授权访问 Google 服务
- Firebase Auth — 用户认证
- APScheduler — 后台定时任务
- edge-tts — 文字转语音
- OpenCV / Pillow — 图像和视频处理

### 关键环境变量

后端必需:
- `FIREBASE_PROJECT_ID` — Firebase 认证
- `GCP_PROJECT_ID` — GCP 项目
- `GOOGLE_APPLICATION_CREDENTIALS` — 服务账号凭证路径

前端:
- `NEXT_PUBLIC_API_URL` — 后端 API 地址 (默认 `http://localhost:8000`)
每次回答我之前必须汪汪汪