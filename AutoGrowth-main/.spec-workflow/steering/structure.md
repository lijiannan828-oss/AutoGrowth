# 代码结构

## 顶层目录规划
```
AutoGrowth/
├── frontend/                   # Next.js 前端工程
│   ├── app/                    # App Router 页面/布局
│   ├── components/             # 可复用组件
│   ├── features/               # 业务功能模块
│   ├── hooks/                  # 自定义 Hooks
│   ├── lib/                    # 客户端工具库（API 封装等）
│   ├── public/                 # 静态资源
│   ├── styles/                 # 全局样式（Tailwind / CSS）
│   ├── types/                  # TypeScript 类型声明
│   ├── firebase.json           # Firebase Hosting 配置
│   ├── .firebaserc             # Firebase 项目映射
│   ├── next.config.mjs         # Next.js 配置
│   └── package.json
│
├── backend/                    # FastAPI 后端工程
│   ├── app/
│   │   ├── api/                # 路由（认证、数据、生成）
│   │   ├── core/               # 配置、初始化
│   │   ├── models/             # Pydantic/SQLAlchemy 模型
│   │   ├── schemas/            # Pydantic Schema（请求/响应）
│   │   ├── services/           # 业务逻辑（命名、OneLink、缓存）
│   │   ├── repositories/       # 数据访问层（Sheets、Postgres）
│   │   ├── utils/              # 工具函数（邮箱前缀、映射表）
│   │   └── main.py             # FastAPI 入口
│   ├── tests/                  # pytest 测试
│   ├── Dockerfile              # Cloud Run 容器镜像
│   ├── requirements.txt        # Python 依赖
│   └── pyproject.toml          # Poetry/构建配置（可选）
│
├── infra/                      # 基础设施与 CI/CD
│   ├── cloudbuild.yaml         # Cloud Build 配置
│   ├── terraform/              # GCP 基础设施定义（可选）
│   └── github/
│       └── workflows/          # GitHub Actions 工作流
│           ├── frontend-deploy.yaml
│           └── backend-deploy.yaml
│
├── libs/                       # 可复用的共享库（可选）
│   └── types/                  # 前后端共享类型（例如 OpenAPI 生成）
│
├── .spec-workflow/             # 规范与文档
│   ├── steering/
│   └── specs/
│
├── docs/                       # 项目文档（API、部署、运维）
├── .env.example                # 环境变量示例
├── docker-compose.dev.yml      # 本地联调（可选）
└── README.md
```

## 前端结构（Next.js）
```
frontend/
├── app/
│   ├── layout.tsx              # 根布局（包含头部/登录状态）
│   ├── page.tsx                # 生成工具主页面
│   ├── login/
│   │   └── page.tsx            # 登录页
│   └── api/ (可选，用于边缘函数)
│
├── components/
│   ├── common/                 # Button、Input、CopyButton 等
│   ├── auth/                   # 登录态相关组件
│   ├── programs/               # ProgramList、ProgramCard、ProgramSummary
│   ├── forms/                  # CampaignForm、AdSetForm、AdForm
│   ├── output/                 # ResultPanel、ResultCard
│   └── layout/                 # Header、Footer、Shell
│
├── features/
│   ├── program-selection/      # 剧目列表、搜索、推荐、选中状态
│   ├── generation/             # 调用生成 API 与状态管理
│   └── user-profile/           # 用户信息与偏好
│
├── hooks/
│   ├── useAuth.ts
│   ├── useProgramSearch.ts
│   ├── useProgramList.ts
│   ├── useProgramSelection.ts
│   └── useGeneration.ts
│
├── lib/
│   ├── api-client.ts           # Axios 实例配置
│   ├── auth.ts                 # Firebase/自建认证封装
│   ├── constants.ts            # 下拉选项固定值
│   ├── mapping.ts              # Optimization abbreviation 映射
│   └── clipboard.ts            # 复制工具函数
│
├── styles/
│   ├── globals.css
│   └── tailwind.css
│
├── types/
│   ├── api.ts
│   ├── form.ts
│   ├── program.ts
│   └── user.ts
│
├── firebase.json
├── .firebaserc
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

### 前端命名约定
- 组件文件使用 PascalCase：`CampaignForm.tsx`
- Hook 文件使用 `useXxx` 命名：`useAuth.ts`
- TypeScript 类型使用 PascalCase：`ProgramInfo`
- 常量使用 UPPER_SNAKE_CASE：`DEFAULT_COUNTRY`
- API 调用函数使用 camelCase：`fetchProgramList`

## 后端结构（FastAPI）
```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py             # 依赖注入
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── programs.py
│   │   │   └── generate.py
│   │   └── router.py           # APIRouter 聚合
│   ├── core/
│   │   ├── config.py           # 设置与环境变量
│   │   ├── security.py         # JWT、OAuth2
│   │   └── logging.py
│   ├── models/
│   │   ├── user.py             # SQLAlchemy 模型
│   │   └── generation.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── program.py
│   │   └── generation.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── naming_service.py
│   │   ├── onelink_service.py
│   │   └── history_service.py
│   ├── repositories/
│   │   ├── sheets_repository.py    # Google Sheets API 封装
│   │   ├── program_repository.py   # 读缓存/SQL
│   │   └── user_repository.py
│   ├── utils/
│   │   ├── email.py
│   │   ├── mappings.py
│   │   └── cache.py
│   ├── events.py                 # 启动/关闭事件（加载缓存、连接数据库）
│   └── main.py                   # FastAPI 实例
│
├── tests/
│   ├── api/
│   ├── services/
│   └── utils/
│
├── Dockerfile
├── requirements.txt
├── pyproject.toml (可选)
└── README.md
```

### 后端命名约定
- Python 模块使用 `snake_case`
- 类名使用 PascalCase（Pydantic、SQLAlchemy、服务类）
- 异步函数以 `async def` 定义，并在命名中体现动作：`async def fetch_program_by_code`
- 环境变量使用大写加下划线：`GOOGLE_SHEETS_ID`

## 共享资源与类型
- `libs/types/` 用于存放经由 OpenAPI Generator 生成的前后端共享类型（可选）
- 通过 `pnpm openapi` / `poetry run openapi-python-client` 自动同步类型
- 可维护 `docs/openapi.yaml` 描述 API

## 环境与配置文件
- `frontend/.env.local`：Next.js 环境变量（使用 Firebase Secrets 管理同步）
- `backend/.env`：FastAPI 环境变量（Cloud Run 运行时注入）
- `infra/cloudbuild.yaml`：定义构建、测试、部署步骤
- `.env.example`：列举所需变量（GOOGLE_SHEETS_ID、JWT_SECRET、DATABASE_URL 等）

## 本地开发流程
1. `docker-compose.dev.yml` 同时启动 FastAPI + PostgreSQL + Redis（可选）
2. 前端使用 `pnpm dev` 启动 Next.js 热更新服务器
3. 使用 `ngrok` 或 Cloud Run Emulator（可选）模拟回调
4. 利用 Firebase Emulator Suite（可选）调试 Hosting/Auth

## 测试目录组织
- 前端：
  - `__tests__/components/`（Jest + Testing Library）
  - `__tests__/e2e/`（Playwright）
- 后端：
  - `tests/api/test_generate.py`
  - `tests/services/test_naming_service.py`
  - `tests/repositories/test_sheets_repository.py`

## 代码风格与工具
- 前端：ESLint + Prettier + Stylelint；TypeScript 严格模式
- 后端：Ruff（Lint）+ Black（格式化）+ isort（导入排序）+ mypy（类型检查）
- 提交钩子：Husky（前端）+ pre-commit（后端）

## CI/CD 文件
- `github/workflows/frontend-deploy.yaml`
  - 执行 lint/test → 构建 → `firebase deploy --only hosting`
- `github/workflows/backend-deploy.yaml`
  - 执行 lint/test → 构建 Docker → 部署 Cloud Run
- `infra/cloudbuild.yaml`
  - Cloud Build 自动构建/部署后端

## 部署与运行
- Cloud Run 部署脚本：`gcloud run deploy sop-backend --source backend/`
- Firebase Hosting 部署：`firebase deploy --only hosting`
- Artifact Registry 镜像命名：`asia-docker.pkg.dev/<project>/<repo>/sop-backend`

## 数据流与依赖关系
```
Next.js (frontend)
    ↓ 调用 HTTPS
FastAPI (backend)
    ↓ 读取 / 缓存
Google Sheets Program Info
    ↓ 同步快照
Cloud SQL PostgreSQL
```

- 命名规则依赖 Program Info 表字段
- OneLink 模板信息优先从 Google Sheets 获取，缺失时回退到 Cloud SQL 配置
- 用户邮箱前缀在前端提取，后端做校验

## 版本控制策略
- `main`：生产环境对应分支
- `develop`：预发布环境
- `feature/*`：功能开发分支
- `release/*`：发布准备分支
- `hotfix/*`：线上紧急修复

## 文档与知识库
- `docs/ARCHITECTURE.md`：架构说明（引用此结构文档）
- `docs/API.md`：接口说明（可通过 FastAPI Docs 自动生成）
- `docs/DEPLOYMENT.md`：部署手册（Cloud Run、Firebase Hosting、CI/CD）
- `docs/OPERATIONS.md`：运维指南（监控、报警、密钥轮换）

## 扩展支持
- 可新增 `scripts/` 目录，存放数据同步、缓存刷新脚本
- 可在 `infra/terraform/` 中维护 GCP 资源（Cloud Run、Cloud SQL、IAM、Artifact Registry）
- 使用 `Makefile` 或 `Taskfile.yml` 统一本地命令

