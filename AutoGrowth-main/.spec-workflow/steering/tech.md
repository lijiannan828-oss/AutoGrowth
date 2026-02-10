# 技术架构

## 技术栈概述

### 前端技术栈
- **框架**: Next.js 14（基于 React 18，支持 SSR/SSG，生态成熟）
- **语言**: TypeScript 5+
- **UI 组件库**: Ant Design（丰富的表单组件）+ Tailwind CSS（快速定制样式）
- **表单与验证**: React Hook Form + Zod
- **状态管理**: React Context + React Query（用于服务器状态管理）
- **HTTP 客户端**: Axios（封装 API 调用，支持拦截器）
- **部署**: Firebase Hosting（提供 HTTPS、CDN 与轻量 CI/CD）

### 后端技术栈
- **运行时**: Python 3.11（团队熟悉）
- **框架**: FastAPI（高性能、异步、自动文档）
- **数据访问**: 
  - Google Sheets API（实时读取 Program Info 表）
  - SQLAlchemy + asyncpg + Cloud SQL Python Connector（连接 Cloud SQL for PostgreSQL）
- **认证**: JWT（FastAPI + PyJWT），支持 Firebase Authentication 校验（可选）
- **任务调度**: APScheduler（定时缓存刷新，可选）
- **部署**: Google Cloud Run（自动伸缩、无服务器、HTTPS）

## 本地/生产环境隔离与数据库连接

本项目采用“前后端本地开发 + 生产 CI 部署”的隔离方式；两环境共享同一 Cloud SQL 数据库保证数据一致，但 API 严格区分：

- 前端
  - 本地: 使用 `frontend/.env.development.local`
    - `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api`
    - Next.js 开发模式自动加载；已在 `.gitignore` 忽略
  - 生产: CI 在构建前写入 `.env.production`
    - 值来自 GitHub Secrets `BACKEND_API_URL`（必须以 `/api` 结尾，`api-client.ts` 会自动标准化）
  - 冗余清理: 保留 `/.env.development.local`；删除/避免 `/.env.local`，避免出现“双重加载”的提示并引起混淆

- 后端
  - 本地: 使用 `backend/.env`（pydantic-settings 默认读取该文件）
    - 推荐内容:
      - `APP_ENV=development`
      - `LOG_LEVEL=DEBUG`
      - `FRONTEND_ORIGINS=http://localhost:3001`
      - `CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`
      - `DATABASE_NAME=auto_growth`
      - `DATABASE_USER=appdev`
      - `DATABASE_PASSWORD=<本地密码>`（例如 `930828Krisrita*`）
      - `USE_IAM_AUTH=false`
      - `GOOGLE_APPLICATION_CREDENTIALS=/Users/mac/AutoGrowth/backend/service-account.json`
    - 启动: `cd backend && source venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
  - 生产: Cloud Run 通过环境变量注入
    - 不注入 `GOOGLE_APPLICATION_CREDENTIALS` 内容（依赖运行时 SA 的 ADC）
    - 注入 `FRONTEND_ORIGINS` 为生产域名列表
    - 数据库连接使用 Cloud SQL Connector；可用密码认证（简单稳定）或启用 IAM DB Auth 后再开启 `USE_IAM_AUTH=true`

- 数据库连接建议
  - 本地优先使用“密码认证”（`USE_IAM_AUTH=false` + `DATABASE_PASSWORD`）
  - 如需 IAM：确保 Cloud SQL 开启 IAM 数据库认证，并创建 `sa-name@project-id.iam` 的数据库用户

- 一键自检
  - `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`
  - `curl 'http://127.0.0.1:8000/api/data/programs?page=1&page_size=5'` → 200 JSON
  - 前端 `npm run dev` 后访问 `http://localhost:3001`，接口命中本地后端

### 数据存储
- **主数据源**: Google Sheets `Program Info`（统一维护所有剧目信息、Shortener、SeasonID、OneLink 模板字段）
- **关系型数据库**: Cloud SQL for PostgreSQL（存储用户信息、生成历史、缓存快照）
- **配置与密钥**: Google Secret Manager（存储服务账号凭证、JWT 秘钥等）
- **缓存层（可选）**: Cloud Memorystore for Redis（加速热门剧目查询）

### 部署与运维
- **CI/CD**: GitHub Actions + Google Cloud Build Trigger
  - Commit → GitHub Actions 运行测试 → 构建 Docker 镜像 → 推送 Artifact Registry → Cloud Run 部署
  - 前端构建并部署到 Firebase Hosting（`firebase deploy`）
- **容器镜像**: Artifact Registry（GCP 镜像仓库）
- **监控日志**: Cloud Monitoring + Cloud Logging
- **环境管理**: 多环境（dev/staging/prod）参数化配置
- **IaC（可选）**: Terraform or Google Cloud Deployment Manager

## 系统架构

### 整体架构模式
采用 Next.js + FastAPI 的前后端分离架构，通过 HTTPS 通信。

```
┌─────────────────────────┐
│       用户浏览器         │
└─────────────▲──────────┘
              │ HTTPS
┌─────────────┴──────────┐
│     Firebase Hosting    │  (前端应用托管)
└─────────────▲──────────┘
              │ HTTPS
┌─────────────┴──────────┐        ┌──────────────────────┐
│     Cloud Run (API)     │◀──────▶│ Cloud SQL for Postgre│
│  FastAPI + Uvicorn/Gunicorn │    │ (用户/缓存数据)       │
└──────▲─────────┬───────┘        └──────────────────────┘
       │         │
       │         └─────────────┐
       │ HTTPS (Service Account)│
       ▼                       ▼
┌───────────────┐        ┌────────────────┐
│ Google Sheets │        │ Secret Manager  │
│ Program Info  │        │ (凭证、密钥)    │
└───────────────┘        └────────────────┘
```

### 核心模块划分

#### 前端模块（Next.js）
1. **认证模块**
   - 使用 Firebase Authentication（Google Provider）实现白名单登录
   - 获取用户邮箱，提取邮箱前缀
   - 将 Token/Session 存储在 HttpOnly Cookie

2. **剧目浏览模块**
   - 使用 React Query 拉取分页剧目列表
   - 提供搜索、排序、推荐标记展示
   - ProgramList + ProgramSearch 组合，支持移动端自适应

3. **表单模块**
   - Campaign/Ad Set/Ad 表单组合
   - 基于 React Hook Form + Zod 的强类型验证
   - 条件字段自动显示/隐藏

4. **生成模块**
   - 调用 `/api/generate/all`
   - 显示生成结果与复制功能

5. **UI/体验模块**
   - 三步流程 UI（选择剧目 → 填写策略 → 复制结果）
   - Ant Design 组件 + Tailwind CSS 主题
   - 支持暗色模式（可选）

#### 后端模块（FastAPI）
1. **认证服务**
   - `/auth/login`：验证 Firebase ID Token → 校验白名单 → 生成 Session
   - `/auth/refresh`：刷新 Token（可选）
   - `/auth/logout`：失效 Token（可选）

2. **数据服务**
   - `GoogleSheetsClient`：封装 Google Sheets API
   - `ProgramRepository`：读取 Program Info，支持倒序排序、分页、关键字过滤、推荐标记
   - `OneLinkTemplateResolver`：解析模板字段

3. **生成服务**
   - `NamingService`：实现 SOP 命名规则
   - `OneLinkService`：组合 OneLink URL
   - `ValidationService`：验证输入

4. **存储服务**
   - `UserService`：管理用户信息（Cloud SQL）
   - `HistoryService`：保存生成历史记录
   - `CacheService`：写入/读取 Redis（可选）

5. **API 层**
   - `/api/data/programs`：获取剧目列表（分页/搜索/排序）
   - `/api/data/programs/:code`：查询单个剧目（可选）
   - `/api/generate/all`：一次性生成全部结果
   - `/api/meta/options`：获取下拉选项（国家、媒体来源等）

## 数据模型

### Program Info 表（Google Sheets）
单表包含所有命名与列表需要字段：
```typescript
interface ProgramInfoRow {
  programCode: string;      // KR000P05S01
  title: string;            // Romantic Island
  programId: string;        // P05
  seasonId: string;         // S01
  programShortner: string;  // romantic_island
  titleENShortener: string; // RomanticIsland
  baseOneLinkUrl: string;   // https://vigloo.onelink.me/SrIM
  fixedParams: string;      // JSON 字符串或键值对
  releasedAt: string;       // 上架时间（用于倒序排序）
  status?: string;          // 状态（上线中、待上线等）
  isRecommended?: boolean;  // 推荐/热门标记
  coverImageUrl?: string;   // 剧目封面（可选）
  lastUpdatedAt: string;    // 更新时间戳
}
```

### PostgreSQL 表（Cloud SQL）
```sql
-- 用户表
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  email_prefix TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

-- 生成历史表
CREATE TABLE generation_history (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  program_code TEXT,
  campaign_name TEXT,
  adset_name TEXT,
  ad_name TEXT,
  onelink_url TEXT,
  payload JSONB,
  created_at TIMESTAMP DEFAULT now()
);

-- 缓存快照表（可选）
CREATE TABLE program_cache (
  program_code TEXT PRIMARY KEY,
  payload JSONB,
  refreshed_at TIMESTAMP
);
```

## 核心算法与业务逻辑

### 命名规则服务（NamingService）
- 输入：`GenerationRequest` + `ProgramInfoRow` + `userEmailPrefix`
- 流程：
  1. 验证必填字段
  2. 计算 Optimization abbreviation（映射表配置在 Cloud SQL 或 YAML）
  3. 拼接 Campaign Name（自动附加邮箱前缀）
  4. 拼接 Ad Set Name
  5. 拼接 Ad Name（智能跳过空字段）
  6. 返回结构化结果

### OneLink 生成服务（OneLinkService）
- 解析 `fixedParams`（可存为 JSON）
- 组合 QueryString：`pid`、`s`、`c`、`af_adset`、`af_ad` 等
- 使用 `urllib.parse.urlencode` 进行参数编码
- 返回完整 URL

#### 标题字段优先级（重要）
- 所有涉及“标题（title）”的命名位置采用如下优先级：
  - `program_shortner` > `title_en_shortener` > `title`
- 具体实现：
  - Campaign 名：若 `program_shortner` 为空，则优先使用 `title_en_shortener`，再回退到 `title`；最终会做 normalize（空白转下划线、小写）
  - Ad 名：直接使用 `title_en_shortener`（调用处传入该字段）

### 邮箱前缀提取工具
```python
def extract_email_prefix(email: str) -> str:
    if '@' not in email:
        raise ValueError('invalid email')
    return email.split('@', 1)[0]
```

## API 设计

### 认证 API
```http
POST /api/auth/login
Request: { "email": "user@company.com", "password": "***" }
Response: { "token": "jwt", "user": { "email": "...", "emailPrefix": "..." } }

POST /api/auth/logout
Request: Authorization Bearer Token
Response: { "success": true }
```

### 数据 API
```http
GET /api/data/programs?q=romantic
Response: {
  "results": [
    {
      "programCode": "KR000P05S01",
      "title": "Romantic Island",
      "programShortner": "romantic_island",
      "titleENShortener": "RomanticIsland",
      "programId": "P05",
      "seasonId": "S01"
    }
  ]
}
```

### 生成 API
```http
POST /api/generate/all
Request: {
  "programCode": "KR000P05S01",
  "campaign": { ... },
  "adset": { ... },
  "ad": { ... }
}
Response: {
  "campaignName": "...",
  "adSetName": "...",
  "adName": "...",
  "oneLinkUrl": "..."
}
```

## 数据访问策略
1. **Google Sheets API**
   - 使用服务账号 + OAuth2
   - `gspread` 或 Google 官方客户端读取
   - 采用 ETag/更新时间字段做缓存
   - 读取后写入 Redis/Cloud SQL 缓存，设定 TTL（例如 5 分钟）

2. **Cloud SQL 缓存回落**
   - 缓存命中：直接返回
  - 缓存失效：重新调用 Google Sheets → 更新缓存 → 返回

3. **错误处理**
   - Sheets API 限流 → 回退到缓存数据
   - 数据缺失 → 返回结构化错误提示

## Cloud SQL 数据库连接配置

### 连接方式
使用 **Cloud SQL Python Connector**（推荐），而非 Cloud SQL Auth Proxy：
- ✅ 不需要单独运行代理进程
- ✅ 自动处理连接管理和重连
- ✅ 更好的错误处理和异步支持
- ✅ 与 SQLAlchemy 无缝集成
- ✅ 支持传统密码认证和 IAM 认证

### 环境变量配置
```bash
# 必需配置
CLOUD_SQL_CONNECTION_NAME=fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod
DATABASE_NAME=auto_growth
DATABASE_USER=appdev  # 或 appprod
DATABASE_PASSWORD=your_password_here
USE_IAM_AUTH=false  # 使用传统密码认证

# 服务账号（用于 Cloud SQL Connector 认证）
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

### 代码实现要点
1. **Event Loop 处理**：
   - SQLAlchemy 的 greenlet 机制与 Cloud SQL Connector 的 event loop 要求存在冲突
   - 必须在 `get_asyncpg_connection` 中为每个连接创建新的 Connector 实例
   - 使用 `asyncio.get_event_loop()` 确保 Connector 绑定到正确的 event loop

2. **连接参数**：
   ```python
   # 传统密码认证（推荐）
   await connector.connect_async(
       connection_name,
       "asyncpg",
       user=database_user,
       db=database_name,
       password=database_password,  # 如果提供密码
       enable_iam_auth=False
   )
   
   # IAM 认证（如果密码未启用）
   await connector.connect_async(
       connection_name,
       "asyncpg",
       user=iam_database_user,  # 格式: sa-name@project-id.iam
       db=database_name,
       enable_iam_auth=True
   )
   ```

3. **IAM 数据库用户**（如果使用 IAM 认证）：
   - 需要在 Cloud SQL 中创建 IAM 数据库用户
   - 用户名格式：`sa-name@project-id.iam`（不带 `.gserviceaccount.com` 后缀）
   - 创建命令：`gcloud sql users create "sa-name@project-id.iam" --instance=INSTANCE_NAME --type=CLOUD_IAM_SERVICE_ACCOUNT`
   - 需要授予数据库权限（GRANT 语句）

### 常见问题与解决方案

1. **Event Loop 错误**：
   - 错误：`ConnectorLoopError: Running event loop does not match 'connector._loop'`
   - 解决：在 `get_asyncpg_connection` 中为每个连接创建新的 Connector 实例，并传入当前 event loop

2. **密码认证失败**：
   - 检查 `DATABASE_PASSWORD` 环境变量是否正确设置
   - 确认 `USE_IAM_AUTH=false`（如果使用密码认证）
   - 验证数据库用户是否存在且有正确权限

3. **IAM 认证失败**：
   - 确认 IAM 数据库用户已在 Cloud SQL 中创建
   - 检查用户名格式（去掉 `.gserviceaccount.com` 后缀）
   - 验证服务账号有 `roles/cloudsql.client` 权限
   - 确认 Cloud SQL 实例已启用 IAM 认证（`cloudsql.iam_authentication: on`）
   - 需要为 IAM 数据库用户授予数据库权限

4. **连接池配置**：
   - 使用 `NullPool`（Cloud SQL Connector 自己处理连接池）
   - 设置 `prepared_statement_cache_size=0`（避免兼容性问题）

### 依赖包
```txt
cloud-sql-python-connector[asyncpg]>=1.18.0
sqlalchemy==2.0.36
asyncpg==0.30.0
```

### 测试连接
使用 `test_database_connection.py` 脚本验证连接配置：
```bash
python test_database_connection.py
```

## 安全与权限
- 所有 API 通过 HTTPS
- JWT 验证中间件拦截未授权请求
- 服务账号密钥存储在 Secret Manager，通过运行时注入
- Cloud SQL 通过 Cloud SQL Python Connector 访问（使用服务账号认证）
- Google Sheets 访问范围限制为只读
- 实现请求速率限制（FastAPI `slowapi` 或自实现）
- **数据库密码存储在环境变量中，不要提交到代码仓库**

## 性能优化
- Next.js 自动代码拆分 + 图片优化（如有）
- React Query 缓存最近查询结果
- FastAPI 异步 IO，高并发性能
- Cloud Run 自动扩缩容（最小实例数配置保证冷启动）
- 利用 Redis/Cloud SQL 缓存减少 Sheets API 调用
- Cloud CDN（Firebase Hosting 内置）加速静态资源

## 测试策略
- **单元测试**: pytest（后端），Jest/Testing Library（前端）
- **集成测试**: 使用 `httpx.AsyncClient` 调 FastAPI；msw 模拟前端 API
- **端到端测试**: Playwright（模拟登录 → 选择剧目 → 生成 → 复制）
- **CI 检查**: Lint（ESLint、Ruff）、Type Check（tsc、mypy）

## 容器化与部署流程
1. **Dockerfile（后端）**
   - 基于 `python:3.11-slim`
   - 安装依赖、复制代码、运行 `uvicorn`/`gunicorn`
2. **Cloud Build**
   - Trigger：推送 `main` 分支或 tag
   - 步骤：`gcloud builds submit` → `gcloud run deploy`
3. **Firebase Hosting**
   - 使用 GitHub Actions `firebase-action` 进行部署
   - 不同环境使用不同的 Firebase 项目/Channel
4. **环境变量**
   - Cloud Run：通过 `gcloud run services update --set-env-vars` 或 Secret Manager
   - Next.js：`.env.local`（使用 Firebase Secrets 管理器）
   - **数据库连接配置**：
     ```bash
     CLOUD_SQL_CONNECTION_NAME=project:region:instance
     DATABASE_NAME=database_name
     DATABASE_USER=username
     DATABASE_PASSWORD=password  # 存储在 Secret Manager
     USE_IAM_AUTH=false
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
     ```
   - **安全提示**：数据库密码等敏感信息应存储在 Google Secret Manager，通过环境变量注入

## 部署问题排查与清单（Cloud Run + Firebase Hosting）

> 本节总结本项目在正式部署时遇到的所有典型卡点（API 启用、服务账号权限、工具链兼容性等），并给出标准排查清单。适用于：
> - 后端：Cloud Run（项目：`fleet-blend-469520-n7`）
> - 前端：Firebase Hosting（项目：`autogrowth-477909`）

### 一、后端（Cloud Run，项目 fleet-blend-469520-n7）

- 必需启用的 API
  - artifactregistry.googleapis.com
  - run.googleapis.com
  - secretmanager.googleapis.com
  - serviceusage.googleapis.com
  - iam.googleapis.com
  - sqladmin.googleapis.com（如使用 Cloud SQL 管理操作校验）

- GitHub 部署服务账号（github-actions-deployer@fleet-blend-469520-n7.iam.gserviceaccount.com）
  - 项目级角色：
    - roles/run.admin
    - roles/artifactregistry.admin
    - roles/secretmanager.admin
    - roles/iam.serviceAccountTokenCreator（用于生成短期访问令牌，部分场景）
  - 对运行时服务账号（Cloud Run --service-account 指定）如需设置/代签：
    - roles/iam.serviceAccountUser（授予在目标 SA 上）

- 运行时服务账号（sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com）
  - 项目级角色：
    - roles/artifactregistry.reader（拉取镜像）
    - roles/secretmanager.secretAccessor（读取密钥）
    - roles/cloudsql.client（访问 Cloud SQL）

- Artifact Registry 仓库
  - 区域：us-central1
  - 仓库：autogrowth-docker
  - 常见问题：
    - 无法创建仓库（PERMISSION_DENIED: artifactregistry.repositories.create）：给部署 SA 授予 roles/artifactregistry.admin，或先手工创建仓库后再推镜像
    - gcloud 命令错误：describe 不支持 `--repository-format` 参数（应仅在 create 时使用）

- Secret Manager
  - 项目需启用：secretmanager.googleapis.com
  - 部署 SA 需具备 secrets 创建/版本管理权限（roles/secretmanager.admin）
  - 运行时 SA 需具备 secrets 读取权限（roles/secretmanager.secretAccessor）
  - 建议的密钥命名与用途：
    - postgres-password（DATABASE_PASSWORD）
    - gcp-sa-key（GOOGLE_APPLICATION_CREDENTIALS，如使用文件式凭据）
  - 工作流逻辑：若存在则跳过创建，避免覆盖

- Cloud Run 部署参数要点
  - 必填：`--service-account`、`--image`、`--region`
  - 数据库相关：
    - `--add-cloudsql-instances $CLOUD_SQL_CONN_NAME`
    - `--set-env-vars "USE_IAM_AUTH=false, DATABASE_NAME=..., DATABASE_USER=..., CLOUD_SQL_CONNECTION_NAME=..." `
    - `--set-secrets "DATABASE_PASSWORD=postgres-password:latest,GOOGLE_APPLICATION_CREDENTIALS=gcp-sa-key:latest"`
  - 常见错误与解决：
    - iam.serviceaccounts.actAs denied：尽量避免跨项目运行时 SA；必要时在运行时 SA 所在项目给 Cloud Run 服务代理与部署 SA 授予 roles/iam.serviceAccountUser
    - Secret Manager API 未启用：在 CI 中增加 `gcloud services enable secretmanager.googleapis.com`
    - 运行后取不到密钥：检查运行时 SA 是否有 secretAccessor，且密钥名匹配

### 二、前端（Firebase Hosting SSR，项目 autogrowth-477909）

- 必需启用的 API
  - firebase.googleapis.com
  - firebasehosting.googleapis.com
  - firebaseextensions.googleapis.com
  - cloudfunctions.googleapis.com（Functions Gen2）
  - cloudbuild.googleapis.com
  - artifactregistry.googleapis.com（Functions 镜像仓库）
  - run.googleapis.com / eventarc.googleapis.com / pubsub.googleapis.com（Gen2 依赖）
  - compute.googleapis.com（框架部署流程会做项目信息读取）
  - iam.googleapis.com / serviceusage.googleapis.com
  - cloudbilling.googleapis.com（需已绑定结算账号）

- GitHub 部署服务账号（github-actions-deployer@fleet-blend-469520-n7.iam.gserviceaccount.com）在前端项目上的角色
  - roles/firebase.admin
  - roles/firebasehosting.admin
  - roles/cloudfunctions.admin
  - roles/compute.viewer（避免 compute.projects.get 403）
  - roles/serviceusage.serviceUsageAdmin（允许在 CI 自动启用所需 API）
  - roles/iam.serviceAccountUser（作用于默认 Compute SA：`934473654771-compute@developer.gserviceaccount.com` 或 App Engine SA：`autogrowth-477909@appspot.gserviceaccount.com`）

- CI 身份认证（非交互）
  - 使用 `google-github-actions/auth@v2`，`credentials_json: ${{ secrets.GCP_SA_KEY }}`，`token_format: access_token`
  - 以 `FIREBASE_TOKEN=${{ steps.gcp-auth.outputs.access_token }}` 运行 `firebase-tools`
  - 在部署账号所在项目启用 `iamcredentials.googleapis.com` 并授予部署 SA：roles/iam.serviceAccountTokenCreator（解决 getAccessToken 403）

- Next.js 与 Firebase Hosting 配置（Frameworks/SSR）
  - Next.js 16 移除了 `next export`；选用 Firebase Hosting Web Frameworks（SSR）模式
  - `frontend/firebase.json`：
    - 推荐使用：`{ "hosting": { "source": ".", "frameworksBackend": {} } }`
    - GitHub Action 中设置 `entryPoint: frontend`
  - 常见错误与解决：
    - “firebase.json not found”：action 增加 `entryPoint: frontend`
    - “Must supply a public/source/rewrites”：在 `hosting` 下提供 `"source": "."` 或 rewrites
    - “Functions successfully deployed but could not set up cleanup policy ...”：在 CI 部署命令中添加 `--force`，或手动执行 `firebase functions:artifacts:setpolicy`
    - “The caller does not have permission（extensions API）”：启用 `firebaseextensions.googleapis.com` 并授予 `roles/firebase.admin`

- 环境变量与后端 URL
  - 在 GitHub Secrets 中添加：`BACKEND_API_URL=https://<cloud-run-url>/api`
  - CI 中写入 `frontend/.env.production`：`NEXT_PUBLIC_API_URL=$BACKEND_API_URL`
  - 建议将 Cloud Run 绑定自定义域名，以稳定前端配置

### 三、跨项目部署注意事项

- 强烈建议后端运行时服务账号与 Cloud Run 服务在同一项目，避免 `iam.serviceaccounts.actAs` 复杂授权与不可预期拒绝
- 如必须跨项目：
  - 在运行时 SA 所在项目，为 Cloud Run 服务代理（`service-<PROJECT_NUMBER>@serverless-robot-prod.iam.gserviceaccount.com`）与部署 SA 授权：
    - roles/iam.serviceAccountUser（必要）
    - roles/iam.serviceAccountTokenCreator（部分环境要求更严格时）
  - 在镜像所在项目为运行时 SA 授权：roles/artifactregistry.reader

### 四、标准化部署前检查清单

- APIs（后端项目）
  - [ ] Artifact Registry / Cloud Run / Secret Manager / Service Usage / IAM / Cloud SQL Admin
- APIs（前端项目）
  - [ ] Firebase / Firebase Hosting / Firebase Extensions / Cloud Functions / Cloud Build
  - [ ] Artifact Registry / Run / Eventarc / Pub/Sub / Compute / IAM / Service Usage / Cloud Billing
- 角色与主体
  - [ ] 部署 SA（后端项目）：run.admin / artifactregistry.admin / secretmanager.admin / iam.serviceAccountTokenCreator
  - [ ] 部署 SA（前端项目）：firebase.admin / firebasehosting.admin / cloudfunctions.admin / compute.viewer / serviceusage.serviceUsageAdmin / iam.serviceAccountUser（绑定到默认 Compute SA）
  - [ ] 运行时 SA（后端项目）：artifactregistry.reader / secretmanager.secretAccessor / cloudsql.client
- 资源与配置
  - [ ] Artifact Registry 仓库存在（us-central1/autogrowth-docker）
  - [ ] Secret Manager 存在：postgres-password / gcp-sa-key（存在则不覆盖）
  - [ ] Cloud Run 部署参数包含：--service-account / --add-cloudsql-instances / --set-secrets / --set-env-vars
  - [ ] 前端 CI：FIREBASE_TOKEN 注入（使用 GCP Access Token），部署命令附 `--force`
  - [ ] 前端 `.env.production` 注入 `NEXT_PUBLIC_API_URL`

以上清单已在本仓库 CI 工作流中逐步自动化：后端 `.github/workflows/backend-deploy.yaml` 与前端 `.github/workflows/frontend-deploy.yaml` 已包含 API 启用、Secrets 校验、IAM 赋权与重试策略。遇到失败可先对照本节定位缺少的 API/角色，再查看对应工作流的输出日志进行修复。 

### 五、经验教训与最佳实践

- Cloud Run 凭据（ADC）
  - 不要把服务账号 JSON 内容通过 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量注入到容器（Cloud Run 会把其当“文件路径”解析，从而报 DefaultCredentialsError）。
  - 使用 Cloud Run 运行时服务账号的默认凭据（Workload Identity），并确保该 SA 具备所需角色（`cloudsql.client`、`secretmanager.secretAccessor`、`artifactregistry.reader`）。

- CORS 与 withCredentials
  - 浏览器携带凭据时（axios `withCredentials=true`），后端必须返回具体的 `Access-Control-Allow-Origin`，不能为 `*`，同时返回 `Access-Control-Allow-Credentials: true`。
  - 实践：通过 `FRONTEND_ORIGINS`（逗号分隔）精确列出前端域名；若列表为 `*`，自动关闭 `allow_credentials` 以避免浏览器拦截。

- gcloud --set-env-vars 逗号转义
  - `--set-env-vars` 使用逗号分隔键值对；当值内包含逗号时，需转义（或使用 env 文件）。多层解析（YAML→Shell→gcloud）可能需要双重转义。
  - 简化策略：前期只配置单一 CORS 源，或改用 `--env-vars-file`。

- Next.js 前端 API Base URL
  - 保证 `NEXT_PUBLIC_API_URL` 以 `/api` 结尾；若用户误填，容易出现 `/data/programs` 404。
  - 实践：在前端 `api-client` 中标准化 baseURL（去除误粘贴的 `@` 前缀、裁剪尾部斜杠、不以 `/api` 结尾则自动补上）。

- Firebase Hosting（Frameworks/SSR）
  - Next.js 16 移除 `next export`；需使用 Hosting Frameworks（SSR）。
  - 常见问题：
    - `firebase.json not found`：在 Action 中设置 `entryPoint: frontend`。
    - “Must supply public/source/rewrites”：在 `hosting` 配置 `"source": "."`。
    - Functions 清理策略报错：部署命令使用 `--force` 或手动执行 `firebase functions:artifacts:setpolicy`。
  - 非交互式认证：用 `google-github-actions/auth@v2` 获取 access token，作为 `FIREBASE_TOKEN` 给 `firebase-tools` 使用；前提是启用 `iamcredentials.googleapis.com` 并授予部署 SA `roles/iam.serviceAccountTokenCreator`。

- 跨项目部署
  - 避免跨项目运行时 SA；如需跨项目，必须为运行时 SA 所在项目的 SA 绑定 `roles/iam.serviceAccountUser` 给 Cloud Run 服务代理与部署 SA，且为镜像项目授予 `roles/artifactregistry.reader`。
  - 简化策略：后端 Cloud Run、镜像仓库、运行时 SA 收敛在同一项目。

- 可观测性
  - 后端出现 500 时优先查看 Cloud Run 日志；若是数据库/ADC/CORS 相关报错，可快速定位配置问题。
  - 前端 200 但浏览器显示 CORS 错误，是浏览器层拦截（非后端 4xx/5xx）；检查响应头是否带 `Access-Control-Allow-Origin`（具体源）与 `Access-Control-Allow-Credentials:true`。

## 运维与监控
- Cloud Logging 收集 API/应用日志
- Cloud Monitoring 设置 QPS、错误率、响应时间告警
- Firebase Analytics（可选）收集前端事件
- Sentry（可选）捕获前后端异常

## 技术选型理由
- **Next.js + Firebase Hosting**: 企业级生态、SSR 能力、静态资源全球加速、CI 流程成熟
- **FastAPI + Python**: 团队熟悉、性能优异、与数据科学生态兼容
- **Google Sheets API**: 保持与现有运营流程一致，实时获取最新数据
- **Cloud SQL (PostgreSQL)**: 托管式数据库，可靠性高，支持复杂查询
  - 使用 Cloud SQL Python Connector 进行连接（无需 Cloud SQL Auth Proxy）
  - 支持传统密码认证和 IAM 认证
  - 自动处理连接管理和重连
- **Cloud Run**: 无服务器，自动伸缩，维护成本低，易于集成 GCP 生态
- **Artifact Registry + GitHub Actions**: 标准化容器构建和部署流程

## 扩展性规划
1. 新增批量生成任务，使用 Cloud Tasks + Cloud Run 处理
2. 将 Program Info Sheet 同步到 Cloud SQL，支持脱机访问
3. 引入 gRPC/GraphQL 接口，供其他内部系统复用
4. 支持多语言界面与多区域配置
5. 引入角色权限（管理员可管理 Program Info 元数据）
6. 通过 Looker Studio 构建自动化报表（基于 Cloud SQL）

