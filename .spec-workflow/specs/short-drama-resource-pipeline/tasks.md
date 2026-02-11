# 实施任务清单

> 规范：`short-drama-resource-pipeline`  
> 说明：将设计文档拆解为可执行任务。开始每个任务前请先在本文件把对应条目的 `[ ]` 改为 `[-]`；完成后改为 `[x]`。

## 前端（Next.js）

- [x] FE-001 添加持久化侧边栏与导航（`app/layout.tsx`）
  - 文件：`frontend/src/app/layout.tsx`，必要时新增 `components/layout/Sidebar.tsx`
  - 输出：在根布局中加入侧边栏，含“命名工具”(`/`) 与“资源流水线”(`/pipeline`) 导航，高亮当前路由
  - _Prompt:
    - Role: Senior Next.js Engineer
    - Task: Implement the task for spec short-drama-resource-pipeline, first run spec-workflow-guide to get the workflow guide then implement the task: add a persistent sidebar to `app/layout.tsx` with links to `/` and `/pipeline`, highlight active route, keep existing styles and providers.
    - Restrictions: Do not break current naming tool pages; avoid inline styles; keep existing indentation and formatting.
    - _Leverage: `frontend/src/app/layout.tsx`, existing components in `frontend/src/components/layout/`.
    - _Requirements: US-001（导航与布局）
    - Success: Sidebar rendered on all pages; navigation works; no regressions on `/`.

- [x] FE-002 新建 `/pipeline` 指挥中心页面骨架
  - 文件：`frontend/src/app/pipeline/page.tsx`
  - 输出：基本布局、占位区块（剧集列表、详情/子文件夹、任务列表与进度、操作栏）
  - _Prompt:
    - Role: Senior React Engineer
    - Task: Implement `/pipeline/page.tsx` skeleton with sections and placeholders; no API calls yet.
    - Restrictions: No hard-coded data; keep styles minimal.
    - _Leverage: Tailwind/AntD if already in project.
    - _Requirements: US-001, US-005, US-006 基础 UI
    - Success: Page renders with clear sections and TODO hooks.

- [x] FE-008 构建 `/pipeline/plan` 传输计划页面
  - 文件：`frontend/src/app/pipeline/plan/page.tsx`（或客户端组件）
  - 输出：左侧 GDrive 树、中央传输对象复选区、右侧计划摘要；仅包含传输相关操作
  - _Prompt:
    - Role: Senior Frontend Engineer
    - Task: Implement Transfer Planner page that consumes `gdrive-status` / `gdrive-folders`, manages selection state, and prepares payload for transfer API.
    - Restrictions: Avoid mixing job监控逻辑；优化渲染性能（虚拟滚动/懒加载）。
    - _Leverage: Existing hooks/components from FE-004/005/006 once ready。
    - _Requirements: US-016 `/pipeline/plan`
    - Success: Operations team can select directories, view summary, and trigger POST `/api/pipeline/transfer` without unrelated UI噪音。

- [x] FE-009 构建 `/pipeline/monitor` 任务监控页面（基础版本）
  - 文件：`frontend/src/app/pipeline/monitor/page.tsx`
  - 输出：状态分栏（传输中/压制中/完成/失败），实时进度、语种进度、失败重试按钮
  - _Prompt:
    - Role: Realtime Frontend Engineer
    - Task: Subscribe to Firestore pipeline_jobs with filters, bucket items by status, render detailed cards with progress, counts, retry CTA.
    - Restrictions: Ensure subscriptions cleaned up; handle empty states; keep page read-only except retry actions.
    - _Leverage: Firestore hooks from FE-006；AntD Collapse/List components。
    - _Requirements: US-016 `/pipeline/monitor`
    - Success: Ops can monitor tasks at a glance and trigger retries.

- [x] FE-011 重构 `/pipeline/monitor` 任务监控页面 UI（以剧集为单位聚合）
  - 文件：`frontend/src/app/pipeline/monitor/page.tsx`，新增组件 `components/pipeline/monitor/DramaCard.tsx`、`components/pipeline/monitor/StatusTabs.tsx`
  - 输出：
    1. 顶部 Tab 筛选栏：进行中的任务、传输中、压制中、失败任务、已完成任务（最近30天），每个 Tab 显示对应状态的任务数量
    2. "清除筛选"按钮：点击后恢复默认展示
    3. 表格以 drama_name 为单位聚合展示：
       - 每一行代表一个唯一的剧集名称
       - 如果该剧集下有多个执行中的任务，聚合在一张卡片中
       - 卡片分区：剧集名称、传输任务（进行中任务 id/状态/进度 + 已完成任务数）、压制任务（进行中任务 id/语种/状态/进度 + 已完成任务数）、失败任务（解译后的出错原因）
    4. 排序：以最新创建的任务为准，如果最新创建的任务对应的 drama_name 是 KR001，那么 KR001 这张卡片排在前面
  - _Prompt:
    - Role: Frontend UI/UX Engineer
    - Task: Refactor monitor page to group tasks by drama_name, implement tab filtering, and aggregate task information per drama card.
    - Restrictions: Maintain real-time updates via Firestore onSnapshot; handle empty states gracefully; ensure performance with large datasets.
    - _Leverage: Firestore hooks, AntD Tabs/Card/Table components, useMemo for aggregation logic.
    - _Requirements: US-019 任务监控页面 UI 重构
    - Success: Users can filter by status tabs, view aggregated drama cards with all task information, and see sorted by latest task creation time.

- [ ] FE-012 任务监控页面增加任务创建时间和操作按钮
  - 文件：`frontend/src/components/pipeline/monitor/DramaCard.tsx`、`frontend/src/features/pipeline/api.ts`
  - 输出：
    1. 每个任务显示任务创建时间（`created_at`）：
       - 格式化为相对时间（如"2 小时前"）或绝对时间（如"2025-01-15 14:30"）
       - 显示在任务 id 旁边或下方
    2. 排队任务（`QUEUED`）显示"取消"按钮：
       - 点击后弹出 Modal.confirm 强提醒对话框
       - 标题："确认取消任务"
       - 内容："此操作不可撤销，确定要取消该任务吗？"
       - 按钮：取消（关闭）、确认取消（调用取消 API）
       - 使用 `danger` 类型的确认按钮
    3. 进行中任务（`TRANSFERRING`、`PROCESSING`）显示"暂停"按钮：
       - 点击后弹出 Modal.confirm 确认对话框
       - 标题："确认暂停任务"
       - 内容："暂停后任务将停止执行，可以稍后恢复。确定要暂停该任务吗？"
       - 按钮：取消（关闭）、确认暂停（调用暂停 API）
    4. 暂停任务（`PAUSED`）显示"恢复"按钮（可选，后续实现）：
       - 点击后调用恢复 API
    5. 新增 API 函数：`cancelJob(jobId)`, `pauseJob(jobId)`, `resumeJob(jobId)`（可选）
  - _Prompt:
    - Role: Frontend UI/UX Engineer
    - Task: Add task creation time display and cancel/pause buttons to task cards with proper confirmation dialogs.
    - Restrictions: Use AntD Modal.confirm for strong warnings; handle loading states; show success/error messages; update UI immediately after action.
    - _Leverage: AntD Modal, Button components, existing API client, formatRelativeTime utility.
    - _Requirements: US-020 任务取消与暂停功能
    - Success: Users can see task creation time, cancel queued tasks with strong warning, and pause running tasks with confirmation.

- [x] FE-010 构建 `/pipeline/library` 资源浏览页面
  - 文件：`frontend/src/app/pipeline/library/page.tsx` + 共享组件 `components/pipeline/library/*`
  - 输出：Tab 切换未压制/已压制；树形/列表视图；搜索、下载、下载到 NAS 操作
  - _Prompt:
    - Role: Storage Explorer Engineer
    - Task: Implement GCS file explorer UI; integrate backend processed-files API (source vs processed) with lazy loading and search.
    - Restrictions: Avoid loading整桶；分页/深度懒加载；所有下载通过后端签名 URL。
    - _Leverage: AntD Tree/Table；`api-client`.
    - _Requirements: US-009, US-016 `/pipeline/library`
    - Success: Users can browse raw/processed assets, download locally or trigger NAS downloads.

- [x] FE-003 集成 Google 登录（前端）并在请求中附 ID Token
  - 文件：`frontend/src/lib/providers.tsx` 或新建 `lib/auth.ts`；更新 API 客户端在请求头加 Authorization
  - 输出：获取 Google/Firebase ID Token，Axios 拦截器在请求头加 `Authorization: Bearer <id_token>`
  - _Prompt:
    - Role: Frontend Auth Engineer
    - Task: Implement Google Sign-In (or Firebase Auth Google provider). Expose a hook to get ID token; set axios interceptor.
    - Restrictions: Don’t store tokens in localStorage; prefer in-memory or cookie if already used.
    - _Leverage: `frontend/src/lib/api-client.ts`, existing providers.
    - _Requirements: US-002
    - Success: User logged-in state available; protected calls include ID token.

- [x] FE-004 实现 GDrive 列表与状态视图
  - 文件：`frontend/src/app/pipeline/page.tsx`、新建 hooks/components：`usePipelineStatus.ts`, `components/pipeline/StatusTable.tsx`
  - 输出：调用 GET `/api/pipeline/gdrive-status`，显示 JR/KR/US 下剧集，标注 `in_gcs`
  - _Prompt:
    - Role: Frontend Data Integration Engineer
    - Task: Fetch and render `gdrive-status` with loading/error, search/filter.
    - Restrictions: Paginate or virtualize large lists; no blocking UI.
    - _Leverage: `frontend/src/lib/api-client.ts`
    - _Requirements: US-003, 性能要求
    - Success: Can view which dramas exist in GCS; performance acceptable.

- [x] FE-005 展开剧集并拉取子文件夹（复选）
  - 文件：新增 `components/pipeline/ProgramBrowserTree.tsx`、`components/pipeline/DirectoryTreeSelector.tsx`
  - 输出：调用 GET `/api/pipeline/gdrive-roots` + `/api/pipeline/gdrive-browse` 懒加载节点；允许勾选多级目录并标记 GCS 同步状态
  - _Prompt:
    - Role: Frontend Engineer
    - Task: Implement lazily-loaded folder picker using Ant Design Tree `loadData`; show “已传输/未传输”状态、收集 `{id,name,path}` 回填摘要。
    - Restrictions: No assumptions on exact folder names beyond contains Episodes/Subtitles.
    - _Leverage: API hooks; AntD Tree loadData。
    - _Requirements: US-004
    - Success: User can choose folders before transfer.

- [x] FE-006 触发传输与实时进度订阅
  - 文件：在 `/pipeline` 页面集成“开始传输”按钮；新增 Firestore 监听模块 `usePipelineJobs.ts`
  - 输出：POST `/api/pipeline/transfer`；使用 Firestore `onSnapshot` 实时更新 job 列表与进度条
  - _Prompt:
    - Role: Realtime Frontend Engineer
    - Task: Wire POST transfer and Firestore subscription to show job progress in realtime.
    - Restrictions: Handle permission errors; unsubscribe on unmount.
    - _Leverage: Firestore Web SDK; UI progress components.
    - _Requirements: US-005, US-006
    - Success: Job queues and progress auto-updates without refresh.

- [x] FE-007 下载成品与下载到 NAS
  - 文件：`components/pipeline/Downloads.tsx`
  - 输出：GET `/api/pipeline/processed-files` → 列表，点击项调用 GET `/api/pipeline/download-link` 自动下载；“下载到 NAS” 调用 POST `/api/pipeline/download-to-nas`
  - _Prompt:
    - Role: Frontend Engineer
    - Task: Implement file listing and signed URL download; NAS task creation.
    - Restrictions: Do not directly expose GCS paths; rely on backend.
    - _Leverage: API client; UI components.
    - _Requirements: US-009
    - Success: Files downloadable; NAS task created and acknowledged.

## 后端（FastAPI）

- [x] BE-001 引入 Firestore 客户端并在应用生命周期中初始化
  - 文件：`backend/app/main.py` 或 `backend/app/core/` 新建 `firestore.py`
  - 输出：全局 Firestore 客户端（Native, us-central1），在 lifespan 启停；CORS 配置更新
  - _Prompt:
    - Role: Senior FastAPI Engineer
    - Task: Initialize Firestore client and CORS from env; expose helper getter.
    - Restrictions: Use ADC; no local key files in prod.
    - _Leverage: Existing config/env loading code.
    - _Requirements: 依赖与初始化章节
    - Success: Health OK; Firestore connection works on Cloud Run.

- [x] BE-002 验证 Google/Firebase ID Token 的依赖与中间件（⚠️ 需同步安装 `firebase-admin`、`email-validator` / `pydantic[email]`）
  - 文件：`backend/app/api/deps.py` 或 `core/security.py`
  - 输出：依赖项 `get_google_user()` 验证 ID Token，返回 email/sub
  - _Prompt:
    - Role: Backend Auth Engineer
    - Task: Implement ID token verification using Google JWKS or Firebase Admin.
    - Restrictions: Don’t trust client; cache JWKS.
    - _Leverage: `google-auth`, optional Firebase Admin if present.
    - _Requirements: US-002
    - Success: Secured endpoints; 401 on invalid token.

- [x] BE-003 OAuth 授权与刷新令牌存储（一次授权流）
  - 文件：新增 `backend/app/api/v1/oauth.py` 与服务 `services/google_oauth_service.py`
  - 输出：后端接收前端的 auth_code，交换到 refresh token，并安全存储（Secret Manager 或 Firestore 加密字段）
  - _Prompt:
    - Role: Google OAuth Engineer
    - Task: Implement OAuth code exchange for scope `drive.readonly`, store refresh token securely and return reference id to client.
    - Restrictions: Do not store tokens in plaintext; no logs of secrets.
    - _Leverage: `google-auth-oauthlib`, Secret Manager helpers.
    - _Requirements: 认证策略
    - Success: Worker later can refresh access token using stored ref.

- [x] BE-004 实现 GET `/api/pipeline/gdrive-status`
  - 文件：`backend/app/api/v1/pipeline.py`
  - 输出：列出三根目录剧集并标注 `in_gcs`
  - _Prompt:
    - Role: Backend API Engineer
    - Task: Implement Drive listing using user token; list GCS folders using SA; return merged status.
    - Restrictions: Handle "Shared with me"; pagination.
    - _Leverage: `googleapiclient.discovery` Drive v3; `google-cloud-storage`.
    - _Requirements: US-003
    - Success: Returns array with in_gcs flags.

- [x] BE-005 实现按需目录浏览接口
  - 文件：`backend/app/api/v1/pipeline.py`，`services/pipeline_status_service.py`
  - 输出：GET `/api/pipeline/gdrive-roots` + `/api/pipeline/gdrive-browse`，根据 folderId 列出一级子目录并返回 `has_children/in_gcs`
  - _Prompt:
    - Role: Backend API Engineer
    - Task: List root definitions from env、并按需列出指定 folderId 的子目录，包含 `has_children`、`in_gcs`。
    - Restrictions: Support paths and drive IDs; robust errors.
    - _Leverage: Drive API + GCS 前缀检查。
    - _Requirements: US-004
    - Success: Returns child folders accurately.

- [x] BE-006 实现 POST `/api/pipeline/transfer`（排队与触发 Job）
  - 文件：`backend/app/api/v1/pipeline.py`、`services/pipeline_transfer_service.py`
  - 输出：在 Firestore 建 `pipeline_jobs` 文档并触发 Cloud Run Job（通过 SDK 注入 JOB_ID/REFRESH_TOKEN_REF），返回 202
  - _Prompt:
    - Role: Backend Orchestrator Engineer
    - Task: Create Firestore job doc; run Cloud Run Job with env JOB_ID and REFRESH_TOKEN_REF; return 202.
    - Restrictions: API itself must not run transfer; no long blocking.
    - _Leverage: `google-cloud-run` REST or gcloud via subprocess (prefer REST).
    - _Requirements: US-005
    - Success: Job queued; worker starts asynchronously.

- [ ] BE-007 实现成品列出与签名下载链接
  - 文件：同 `pipeline.py`
  - 输出：GET `/processed-files`、GET `/download-link`；POST `/download-to-nas`
  - _Prompt:
    - Role: Backend Storage Engineer
    - Task: List processed files from `vigloo_processed`, generate signed URL, create NAS tasks.
    - Restrictions: Signed URL ttl ≤ 12h; input validation.
    - _Leverage: `google-cloud-storage`, Firestore.
    - _Requirements: US-009
    - Success: Local download and NAS task creation work.

- [x] BE-008 Firestore 运行时配置与权限校验
  - 文件：`backend/app/core/config.py`, `backend/app/main.py`, `infra/github/workflows/backend-deploy.yaml`
  - 输出：Cloud Run 服务启用 Firestore API、运行时 SA 具备 `roles/datastore.user`，并在部署流程中注入 Firestore 项目/集合相关环境变量
  - _Prompt:
    - Role: Backend Platform Engineer
    - Task: Ensure Firestore is enabled , runtime service accounts have `roles/datastore.user`, and backend config loads `FIRESTORE_PROJECT_ID`/`FIRESTORE_NAMESPACE`. Update backend deploy workflow to include `gcloud services enable firestore.googleapis.com` and document required IAM.
    - Restrictions: No hardcoded project IDs outside env vars; reuse existing config patterns.
    - _Leverage: `backend/app/core/config.py`, `.github/workflows/backend-deploy.yaml`.
    - _Requirements: BE-001 支撑、US-016 monitor 依赖 Firestore.
    - Success: Backend Firestore client可在本地/Cloud Run 成功初始化；部署日志记录 Firestore API 已启用；权限不足会在启动前检测并给出指引。

- [x] BE-009 实现 GET `/api/pipeline/jobs`（任务监控 API）
  - 文件：`backend/app/api/v1/pipeline.py`、`services/pipeline_status_service.py`
  - 输出：查询 Firestore `pipeline_jobs` 集合，按创建时间倒序返回所有传输/压制任务；每行包含剧集名称、GDrive 路径、传输进度 `transferred_files/total_files`、压制进度 `processed_files/total_files`、当前状态（`QUEUED/TRANSFERRING/PROCESSING/SUCCEEDED/FAILED`）、失败原因、最后更新时间等信息
  - _Prompt:
    - Role: Backend Observability Engineer
    - Task: Build monitor endpoint feeding `/pipeline/monitor`; support分页/过滤进行中的任务、默认返回最近 50 条；确保字段兼容 Firestore 实时订阅结构
    - Restrictions: 仅允许授权用户访问；对 Firestore 查询添加 index 说明；严禁返回敏感 token
    - _Leverage: Firestore client、`usePipelineJobs` 前端订阅模型
    - _Requirements: US-016（任务监控页面）
    - Success: 前端可渲染"任务监控"表格，含剧集名称/进度/失败信息，状态排序正确

- [ ] BE-010 扩展任务监控 API 支持按剧集聚合和状态统计
  - 文件：`backend/app/api/v1/pipeline.py`、`services/pipeline_status_service.py`
  - 输出：
    1. 新增 GET `/api/pipeline/jobs/stats` 端点，返回各状态的任务数量统计：
       - `in_progress_count`: 进行中的任务数量（未标记结束）
       - `transferring_count`: 传输中任务数量
       - `processing_count`: 压制中任务数量（包括已传输完成在压制中 + 单独在压制）
       - `failed_count`: 失败任务数量
       - `completed_count`: 最近30天已完成任务数量
    2. 扩展 GET `/api/pipeline/jobs` 支持按 `drama_name` 聚合查询参数（可选）
    3. 错误解译逻辑：将原始错误信息解译为用户友好的错误原因（如 `FileNotFoundError` → "文件未找到"）
  - _Prompt:
    - Role: Backend API Engineer
    - Task: Extend jobs API to support status statistics and drama_name aggregation; implement error message translation logic.
    - Restrictions: Maintain backward compatibility; optimize Firestore queries with proper indexes; cache statistics if needed.
    - _Leverage: Firestore aggregation queries, error translation mapping.
    - _Requirements: US-019 任务监控页面 UI 重构
    - Success: Frontend can fetch status counts and aggregated drama tasks efficiently; error messages are user-friendly.

- [ ] BE-011 实现任务取消和暂停 API
  - 文件：`backend/app/api/v1/pipeline.py`、`services/pipeline_status_service.py`
  - 输出：
    1. POST `/api/v1/pipeline/jobs/{job_id}/cancel`：
       - 验证任务状态为 `QUEUED`，否则返回 400
       - 更新 Firestore：`status="CANCELLED"`, `cancelled_at=now()`, `cancelled_by=current_user.email`
       - 返回 200 + `{ job_id, status: "CANCELLED" }`
    2. POST `/api/v1/pipeline/jobs/{job_id}/pause`：
       - 验证任务状态为 `TRANSFERRING` 或 `PROCESSING`，否则返回 400
       - 更新 Firestore：`status="PAUSED"`, `paused_at=now()`, `paused_by=current_user.email`
       - 返回 200 + `{ job_id, status: "PAUSED" }`
    3. POST `/api/v1/pipeline/jobs/{job_id}/resume`（可选，后续实现）：
       - 验证任务状态为 `PAUSED`，否则返回 400
       - 更新 Firestore：`status` 恢复为 `TRANSFERRING` 或 `PROCESSING`（根据 `stage` 判断），`resumed_at=now()`, `resumed_by=current_user.email`
       - 重新触发对应的 Cloud Run Job
       - 返回 200 + `{ job_id, status: "TRANSFERRING" | "PROCESSING" }`
  - _Prompt:
    - Role: Backend API Engineer
    - Task: Implement cancel and pause APIs for pipeline jobs with proper state validation and Firestore updates.
    - Restrictions: Only allow cancel for QUEUED tasks; only allow pause for TRANSFERRING/PROCESSING tasks; ensure atomic Firestore updates; handle concurrent state changes.
    - _Leverage: Firestore transactions for state updates, existing pipeline job service.
    - _Requirements: US-020 任务取消与暂停功能
    - Success: Users can cancel queued tasks and pause running tasks; state changes are atomic and properly recorded.

- [ ] WK-004 传输 Worker 支持暂停和取消
  - 文件：`backend/app/workers/transfer/main.py`
  - 输出：
    1. 在传输循环中定期（每 15 秒）检查 Firestore 任务状态
    2. 如果检测到 `status="PAUSED"` 或 `status="CANCELLED"`，立即停止 rclone 进程并退出
    3. 停止时记录当前进度到 Firestore（可选）
    4. 退出时返回适当的退出码（0 表示正常完成，非 0 表示被暂停/取消）
  - _Prompt:
    - Role: Cloud Run Job Engineer
    - Task: Add status checking logic to transfer worker to support pause and cancel operations.
    - Restrictions: Check status frequently enough to respond quickly; gracefully stop rclone process; preserve progress state.
    - _Leverage: Firestore client, subprocess management, signal handling.
    - _Requirements: US-020 任务取消与暂停功能
    - Success: Transfer worker stops immediately when task is paused or cancelled; progress is preserved.

- [ ] WK-005 压制 Worker 支持暂停和取消
  - 文件：`backend/app/workers/process/main.py`
  - 输出：
    1. 在处理每个文件前检查 Firestore 任务状态
    2. 如果检测到 `status="PAUSED"` 或 `status="CANCELLED"`，立即停止当前 ffmpeg 进程并退出
    3. 停止时记录当前进度到 Firestore（已完成的文件数）
    4. 退出时返回适当的退出码
  - _Prompt:
    - Role: Cloud Run Job Engineer
    - Task: Add status checking logic to process worker to support pause and cancel operations.
    - Restrictions: Check status before processing each file; gracefully stop ffmpeg process; preserve progress state.
    - _Leverage: Firestore client, subprocess management, signal handling.
    - _Requirements: US-020 任务取消与暂停功能
    - Success: Process worker stops immediately when task is paused or cancelled; progress is preserved.

## Workers（Cloud Run Jobs）

- [x] WK-001 传输器镜像与脚本
  - 目录：`workers/transfer/`（`Dockerfile`, `main.py`）
  - 输出：rclone + Python，解析 `JOB_ID`/`REFRESH_TOKEN_REF`，执行复制并更新 Firestore，上传 `_PROCESS_NOW.txt`
  - _Prompt:
    - Role: Cloud Run Job Engineer
    - Task: Implement rclone-based transfer with Drive user token and GCS; update Firestore progress from `-P` output; upload `_PROCESS_NOW.txt`.
    - Restrictions: Use `--drive-shared-with-me`; safe temp files; handle retries.
    - _Leverage: rclone; google-cloud libs.
    - _Requirements: US-007
    - Success: Files copied and progress visible; signal file created.

- [x] WK-002 压制器镜像与脚本（旧版本）
  - 目录：`workers/process/`（`Dockerfile`, `main.py`）
  - 输出：解析 Eventarc 事件，匹配 mp4/srt，ffmpeg 字幕样式压制并上传到 `vigloo_processed`，更新 Firestore 进度
  - _Prompt:
    - Role: Video Processing Engineer
    - Task: Implement ffmpeg pipeline with subtitle styling and language routing; update Firestore per output.
    - Restrictions: Include Noto Sans CJK; consider encoding; efficient temp storage.
    - _Leverage: ffmpeg, chardet, GCS client.
    - _Requirements: US-008
    - Success: Processed outputs uploaded and counted; job completes.
  - ✅ 扩展：失败捕获 + 单文件重试
    - 新增 `processing_failures` 集合，记录 video/subtitle GCS 路径、语言、错误堆栈
    - Worker 支持 `type=retry`，可根据 `target_video_path` / `target_subtitle_path` 仅压制单集
    - 新 API `POST /api/pipeline/retry-process/{failure_id}` 创建 retry Job 并触发 `drama-processor-job`
    - 提供脚本 `backend/scripts/test_retry_logic.py` 方便本地验证 Retry 流程

- [ ] WK-002-R 压制器架构重构：Sharding + 细粒度进度追踪 ⭐ **新增**
  - 目录：`backend/app/workers/process/main.py`
  - 背景：单实例处理 500+ 视频时 OOM 崩溃，需要水平扩展 + 细粒度进度追踪
  - 输出：重构为 Cloud Run Jobs Sharding 模式，实现 Task 级进度追踪
  - 子任务：
    - [x] WK-002-R-1 引入分片算法
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 `DramaProcessWorker.__init__` 中获取 `CLOUD_RUN_TASK_INDEX` 和 `CLOUD_RUN_TASK_COUNT`
      - 修改：在 `run()` 方法中，获取所有 `all_episodes` 后，使用取模算法过滤：
        ```python
        task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
        task_count = int(os.environ.get("CLOUD_RUN_TASK_COUNT", "1"))
        my_episodes = [e for i, e in enumerate(all_episodes) if i % task_count == task_index]
        ```
      - 日志：打印 `"Task {task_index}/{task_count}: Claimed {len(my_episodes)} of {len(all_episodes)} episodes"`
      - 测试：本地设置环境变量 `CLOUD_RUN_TASK_INDEX=0 CLOUD_RUN_TASK_COUNT=3` 验证分片正确
    - [x] WK-002-R-2 初始化 Task 状态文档
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 `run()` 方法中，处理 `my_episodes` 之前，创建 Task 文档：
        ```python
        task_ref = self.job_ref.collection("tasks").document(str(task_index))
        task_ref.set({
            "task_index": task_index,
            "status": "RUNNING",
            "current_file": None,
            "success_files": [],
            "failed_files": [],
            "progress_count": 0,
            "total_count": len(my_episodes),
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP
        })
        ```
      - 测试：验证 Firestore 中 `pipeline_jobs/{job_id}/tasks/{task_index}` 文档创建成功
    - [x] WK-002-R-3 处理循环中的 Firestore 更新
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 `_process_single_pair` 方法中：
        - **处理前**：更新 `task_ref.update({"current_file": f"{pair.language}/ep{pair.episode}.mp4"})`
        - **成功后**：
          - 更新 Task 文档：`task_ref.update({"success_files": firestore.ArrayUnion([文件名]), "progress_count": firestore.Increment(1)})`
          - 原子更新主文档：`job_ref.update({"processed_files": firestore.Increment(1)})`
        - **失败后**：
          - 更新 Task 文档：`task_ref.update({"failed_files": firestore.ArrayUnion([{"path": 文件名, "error": 错误信息}]), "progress_count": firestore.Increment(1)})`
          - 原子更新主文档：`job_ref.update({"failed_files": firestore.Increment(1)})`
          - 记录到 `processing_failures` 集合（保持原有逻辑）
        - **重要**：禁止 Worker 更新主文档的 `progress` 文本字段，避免 500+ 并发时的写入冲突。
      - 测试：验证每个文件处理前后 Firestore 更新正确，且主文档 `progress` 字段未被频繁覆写
    - [x] WK-002-R-4 Task 完成与主 Job 状态终结
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 `run()` 方法中，处理完所有 `my_episodes` 后：
        1. 更新当前 Task 状态：
           ```python
           task_ref.update({
               "status": "COMPLETED",
               "current_file": None,
               "updated_at": SERVER_TIMESTAMP
           })
           ```
        2. **使用 Transaction 检查是否所有文件都已处理**：
           - 读取主文档 `job_ref`
           - 检查 `processed_files + failed_files >= total_files`
           - 如果条件满足，原子性更新主文档 `status="SUCCEEDED"` (或 `"FAILED"` 如果全是失败)
      - 测试：验证最后一个完成的 Worker 能正确将主任务状态标记为完成
    - [x] WK-002-R-5 FFmpeg 参数优化
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 `_process_single_pair` 方法中：
        - 动态线程数：`threads = min(multiprocessing.cpu_count(), 4)` 或 `0`（自动检测）
        - Preset：`veryfast`（已存在，确认）
        - CRF：`23`（已存在，确认）
        - 保留：`-movflags +faststart`（已存在，确认）
      - 测试：验证 FFmpeg 命令参数正确
    - [x] WK-002-R-6 显式资源清理
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 `_process_single_pair` 方法中，处理完每个文件后：
        - 立即删除 `video_path`, `subtitle_path`, `output_path`（如果存在）
        - 调用 `import gc; gc.collect()` 强制垃圾回收
      - 测试：验证临时文件被正确删除，内存使用不累积
    - [x] WK-002-R-7 移除内部并发
      - 文件：`backend/app/workers/process/main.py`
      - 检查：搜索 `ThreadPoolExecutor` 或 `ProcessPoolExecutor`
      - 修改：如果存在，删除或将 `max_workers=1`，确保单实例内部串行处理
      - 测试：验证没有内部并发，依靠 Cloud Run 水平扩展实现并发
    - [x] WK-002-R-8 更新主文档字段
      - 文件：`backend/app/services/pipeline_process_service.py`
      - 修改：在创建 process job 时，设置 `total_files` 字段：
        ```python
        job_ref.set({
            ...
            "total_files": len(all_episodes),  # 总文件数
            "processed_files": 0,  # 成功数（初始为 0）
            "failed_files": 0,    # 失败数（初始为 0）
            ...
        })
        ```
      - 测试：验证主文档字段正确设置
    - [x] WK-002-R-9 更新 Job 触发逻辑（动态 task_count）与公共文件列表
      - 文件：`backend/app/services/pipeline_process_service.py`
      - 修改：在 `enqueue_process_job` 或相关方法中：
        - **重构**：将 `_build_processing_pairs` 逻辑提取为公共 Utility (如 `PipelineDiscoveryService`)，确保 Service 和 Worker 使用完全一致的排序算法（按 `language, episode`）获取文件列表。
        - 在 `enqueue_process_job` 中调用该 Utility 获取 `total_count`。
        - 在 `RunJobRequest` 的 `overrides` 中设置 `task_count`：
          ```python
          # 设定上限为 100，防止 1000+ 文件时对 DB 造成瞬时压力
          # 少于 100 个文件时，1:1 处理（task_count = total_count）
          # 多于 100 个文件时，每个 Task 处理多个文件（task_count = 100）
          task_count = min(total_count, 100)
          
          overrides = run_v2.RunJobRequest.Overrides(
              task_count=task_count,
              container_overrides=[
                  run_v2.RunJobRequest.Overrides.ContainerOverride(env=env_vars)
              ]
          )
          ```
        - 同时设置主文档的 `total_files` 字段
      - 测试：验证触发 Job 时 `task_count` 正确设置
    - [x] WK-002-R-10 更新部署配置（资源规格）
      - 文件：`.github/workflows/backend-deploy.yaml`
      - 修改：更新 `drama-processor-job` 的部署参数：
        - `--cpu=2`（从 8 改为 2）
        - `--memory=4Gi`（从 32Gi 改为 4Gi）
        - `--task-timeout=2h`（保持或调整）
        - --parallelism 50  # 【关键新增】防爆阀：单个 Job Execution 最大并发实例数设为 50
      - 测试：验证部署后 Job 规格正确
    - [x] WK-002-R-11 本地测试脚本（Sharding 模拟）
      - 文件：`backend/scripts/test_sharding_local.py`（新建）
      - 输出：模拟 Cloud Run 分片环境，验证分片算法正确性
      - 要求：
        - 模拟生成 100 个假任务 ID
        - 模拟启动 5 个"进程"，分别设置不同的 `CLOUD_RUN_TASK_INDEX` (0-4) 和 `CLOUD_RUN_TASK_COUNT` (5)
        - 验证每个"进程"是否正确领取了属于它的 20 个任务，且没有遗漏或重复
        - 打印每个 Task 分配到的任务列表
      - 测试：运行脚本验证分片逻辑正确
    - [x] WK-002-R-12 分片启动检查（断点续传）
      - 文件：`backend/app/workers/process/main.py`
      - 修改：在 Worker 启动并获取 `my_episodes` 后：
        - 读取当前 Task 的状态文档 `tasks/{task_index}` (如果存在)
        - 获取 `success_files` 列表
        - 从 `my_episodes` 中移除已存在的成功文件
        - 日志：`"Task {task_index}: Skipping {skipped_count} already processed files"`
      - 测试：手动重启已部分完成的 Job，验证 Worker 跳过已完成文件
- [x] WK-003 Zip 压缩器
  - 目录：`workers/zip_compress/`（`main.py`）
  - 输出：读取 Firestore `zip_tasks`，下载路径列表，打包 ZIP 上传至 `vigloo-temp-downloads`，设置 24h 失效并写回下载链接
  - 触发：新 API `/pipeline/download-zip` 创建任务并在 Dev/Prod 分别启动本地/Cloud Run Job
  - 状态：`zip_tasks` 记录 `status`, `zip_gcs_path`, `download_url`, `expires_at`

## 基础设施（CI/CD 与 Eventarc）

- [x] INF-001 GitHub Actions：构建与部署三个 Jobs
  - 文件：`.github/workflows/backend-deploy.yaml`
  - 输出：新增 steps 构建并部署 `workers/transfer`、`workers/process`、`workers/zip_compress` 三个 Cloud Run Jobs，`gcloud run jobs deploy ...`
  - _Prompt:
    - Role: DevOps Engineer
    - Task: Extend workflow to build/push images and deploy Cloud Run Jobs with high CPU/mem and long timeout.
    - Restrictions: Enable required APIs; use existing SA; region us-central1.
    - _Leverage: current workflow patterns.
    - _Requirements: 任务 6.1
    - Success: CI deploys jobs idempotently.

- [-] INF-002 创建/更新 Eventarc 触发器
  - 文件：同工作流；或 `infra/` 脚本
  - 输出：`google.cloud.storage.object.v1.finalized` on `vigloo_source`, name ends with `_PROCESS_NOW.txt`，目标 `drama-processor-job`
  - 现状：新增脚本 `infra/eventarc_setup.sh`，可在本地运行以创建/验证触发器；仍需在 GCP 项目中执行脚本并验证触发器状态
  - _Prompt:
    - Role: GCP Infra Engineer
    - Task: Add idempotent script/steps to ensure Eventarc trigger exists and is bound to the job.
    - Restrictions: Ensure permissions for service agents.
    - _Leverage: gcloud commands.
    - _Requirements: 任务 6.2
    - Success: Trigger fires worker on signal file.

- [ ] INF-003 GitHub Secrets 注入 Firebase 环境变量
  - 文件：`.github/workflows/frontend-deploy.yaml`, `infra/DEPLOYMENT_IN_PROGRESS.md`
  - 输出：在部署流程中读取 `NEXT_PUBLIC_FIREBASE_*` Secrets 写入 `.env.production`
  - _Prompt:
    - Role: DevOps Engineer
    - Task: Document required Firebase secrets, add workflow steps to export them into `.env.production`/`firebaseConfig`, and verify CI 阶段 `firebase deploy` 可读取。
    - Restrictions: 不在仓库提交实际密钥；使用 GitHub Encrypted Secrets。
    - _Leverage: 现有写 `.env.production` 的脚本；`firebase.json`.
    - _Requirements: US-002（前端登录/Firebase 集成）
    - Success: CI 日志显示成功写入 env 文件且未泄漏值；手动部署无需本地 .env。

- [x] INF-004 Eventarc 中继服务（Relay Service）
  - 文件：`backend/app/api/v1/relay.py`, `backend/app/api/v1/router.py`, `.github/workflows/backend-deploy.yaml`
  - 输出：新增 `POST /api/v1/relay/event`，解析 CloudEvents（GCS `_PROCESS_NOW.txt`），提取 `DRAMA_NAME`，以 `PROCESSOR_JOB_NAME` + `PIPELINE_DEFAULT_TOKEN_REF` 触发 `drama-processor-job`；部署专用 Cloud Run Service `drama-processor-relay-service`
  - **Sharding 改造**：
    1. 引入 `PipelineDiscoveryService.discover_file_pairs`，计算待处理文件总数 `total_files`。
    2. 计算 `task_count = min(total_files, 100)`。
    3. 调用 Cloud Run Jobs API 时，在 `overrides` 中注入 `taskCount`。
    4. 在触发 Job 前，更新 Firestore 主文档状态（`total_files`, `processed_files=0`, `failed_files=0`）。
  - _Prompt:
    - Role: Platform Engineer
    - Task: 实现 relay API、使用 google-auth 调用 `projects.locations.jobs.run`，并在 CI/CD 中部署/注入环境变量
    - Restrictions: 端点必须始终返回 200，避免 Eventarc 重试；Service Account 需具备 `roles/run.jobUser`
    - _Leverage: 现有 Cloud Run 调度逻辑、`PIPELINE_DEFAULT_TOKEN_REF` 配置
    - _Requirements: US-017 Eventarc Relay Service
    - Success: Eventarc 触发 relay service -> Cloud Run Job 成功启动；本地可用示例 payload 模拟验证

- [ ] INF-005 资源库页面功能增强
  - 文件：
    - Backend：`backend/app/services/pipeline_status_service.py`, `backend/app/api/v1/pipeline.py`, `backend/app/services/pipeline_process_service.py`, `backend/app/schemas/pipeline.py`, `backend/app/workers/process/main.py`
    - Frontend：`frontend/src/app/pipeline/library/page.tsx`, `frontend/src/components/pipeline/ProgramBrowserTree.tsx`, `frontend/src/components/pipeline/DownloadActions.tsx`（或新增 `ProcessActions.tsx`）、`frontend/src/features/pipeline/api.ts`, `frontend/src/features/pipeline/types.ts`
  - 输出：
    1. `list_unprocessed_dramas()` 比较 source/processed 桶一级目录返回待压制剧集，并通过 API 提供。
    2. 定义 `ManualProcessRequest` + `POST /api/v1/pipeline/process-manual`，`trigger_manual_process_job()` 写入 Firestore job（携带 `file_paths`、`stage=1`）并触发 `drama-processor-job`；process worker 能消费 `file_paths`。
    3. Library 页面切成“已压制 / 待压制”Tab；ProgramBrowserTree 修复懒加载/展开；右侧新增“压制字幕”按钮，根据勾选文件调用新 API，成功后提示任务进入监控。
    4. 在文档或脚本中提供本地调试指引（例如 `debug_rclone_filter.py` 用法、如何调用 `process-manual` API）。
  - _Prompt:
    - Role: Full-stack Engineer
    - Task: 扩展资源库页面以支持补压字幕流程，确保后端/前端/Worker 对齐。
    - Restrictions: 保持现有 API 兼容；按钮仅在有选中项时可用；filter 规则需兼容含空格/特殊字符的目录。
    - _Leverage: 既有 pipeline API、Process Worker 触发逻辑、调试脚本。
    - _Requirements: US-018
    - Success: 待压制列表准确、手动压制任务可触发并显示在监控页，Tree 展开深层目录无误伤。

## 说明
- 在开始任务前：将该任务前的 `[ ]` 改为 `[-]`。完成后改为 `[x]`。
- 若任务拆分进一步细化，可在本文件下追加子任务，但保持原子性与清晰性。

## 依赖管理记录（2025-11-17）
- **BE-001**：新增 Firestore 客户端需要 `google-cloud-firestore`，同时在 `.env` 中配置 `FIRESTORE_PROJECT_ID=autogrowth-477909`（若为空会回退到 `FIREBASE_PROJECT_ID`）及可选 `FIRESTORE_NAMESPACE`/`FIRESTORE_EMULATOR_HOST`。
- **BE-002**：在引入 `AuthenticatedUser.email: EmailStr` 时必须安装 `email-validator`（或 `pydantic[email]`），否则 FastAPI 无法启动。已在 `backend/requirements.txt` 补充并安装。
- **后续任务依赖提醒**：
  - **BE-003**：需写明并安装 `google-auth-oauthlib`（若未安装）用于 OAuth code exchange。
  - **BE-004/BE-005**：需要 `google-api-python-client`（Drive v3）与 `google-cloud-storage`，请在任务执行时检查 requirements。
  - **BE-006**：若通过 SDK 触发 Cloud Run Jobs，需添加 `google-cloud-run` 或使用 REST 客户端依赖。
  - **BE-007**：依赖 `google-cloud-storage`、`google-cloud-firestore`（若需记录 NAS 任务）。
  - ✅ 扩展：新增 `GET /download-link`、`POST /download-zip`、`POST /download-to-nas`，串联 ZIP Worker，生成临时签名链接与 Firestore 任务记录。
  - **BE-008**：初始化 Firestore 客户端时需安装 `google-cloud-firestore` 并在部署脚本中启用 API。
- **改进措施**：以后在任务描述中补充“Dependencies”小节，执行代码前运行 `uvicorn app.main:app` 或 `pytest` 以尽早暴露缺失依赖；CI 里新增 `pip check` 以自动挡。


