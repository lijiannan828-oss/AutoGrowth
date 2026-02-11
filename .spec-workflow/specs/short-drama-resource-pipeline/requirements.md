# 需求文档

## 项目信息

- **规范名称**: `short-drama-resource-pipeline`
- **项目名称**: 短剧资源流水线控制面板
- **创建日期**: 2025-11-15
- **状态**: 待审批

## 背景与机会

- 现有 AutoGrowth 系统只覆盖“命名工具”，短剧原片与字幕的同步、传输、压制与分发仍依赖人工操作和本地 Mac，无法满足海量剧集与跨地区协作的效率需求。
- 韩国团队将原片存于 Google Drive，并以“Share with me”方式共享；需要利用操作者的真人帐号令牌才能读取。
- 已验证 rclone 可完成 GDrive→GCS 的复制，但缺乏云端编排、任务跟踪与权限隔离。
- 业务希望扩展为“短剧资源流水线控制面板”，统一入口提供命名工具与资源同步模块，并可交由专职人员在云端执行。

## 目标与成功指标

1. 通过云端 Web 控制面板完成剧集目录扫描、同步、压制与下载调度，全流程不再依赖本地电脑。
2. 将 GDrive→GCS 同步任务的发起时间控制在 < 2 分钟（选择目录到任务排队）。
3. 同步 + 压制完成率≥99%，进度可在前端实时查看。
4. 提供可审计的 Firestore 任务记录，以及 NAS 下载队列以支撑后续自动化。

## 范围

**在范围**
- Next.js 前端（`frontend/`）重构，引入全局侧边栏、`/pipeline` 页面及资源流水线 UI。
- FastAPI 后端（`backend/app/main.py`）新增 Firestore 依赖、Google OAuth 校验、面向流水线的 API。
- 新增两个 Cloud Run Job（Worker 1: rclone 传输；Worker 2: ffmpeg 压制）及对应 Dockerfile/代码。
- 新增 Firestore 集合（`pipeline_jobs`、`nas_download_tasks`）、GCS 信号文件 `_PROCESS_NOW.txt` 协议。
- GitHub Actions 工作流扩展，部署 Cloud Run Jobs 与 Eventarc 触发器。

**不在范围**
- 改动现有命名工具业务逻辑（功能继续可用即可）。
- 自动字幕翻译、AI 质检等后续阶段需求。
- NAS 端轮询脚本实现（只需在 Firestore 创建任务文档）。

## 用户画像

| 角色 | 目标 | 痛点 |
| --- | --- | --- |
| 资源调度专员（如 Beckett） | 在云端选择剧集、发起同步、追踪状态 | 目前必须登陆本地 Mac 运行 rclone，无法多人协作 |
| 压制技术员 | 关注压制进度、下载成品到 NAS 或本地 | 无统一面板查看进度或下载路径 |
| 运营/投手 | 仍需使用命名工具 | 需要单一入口快速切换工具 |

## 用户故事与验收标准

### US-001: 全局布局与导航
- **作为** 控制面板用户 **我想要** 在一个界面内切换命名工具与资源流水线 **以便** 降低来回跳转成本。
- **验收标准**
  1. `app/layout.tsx` 提供持久化侧边栏，包含“命名工具”(`/`)与“资源流水线”(`/pipeline`)两个导航项，当前路由高亮。
  2. 命名工具现有页面沿用，无功能回归。
  3. `/pipeline` 页面载入基础骨架（顶栏、列表区、任务面板）。

### US-002: Google 登录与权限
- **作为** 资源调度专员 **我想要** 通过 Google 登录授权 **以便** 后端可代表我访问“Share with me”的 GDrive 文件。
- **验收标准**
  1. 前端引入 Google Sign-In（可复用 Firebase Auth 或直接 OAuth），要求特定邮箱/域名白名单。
  2. 登录成功将 ID Token 发送给后端 Pipeline API，后端验证 token（Google 公钥或 Firebase Admin）。
  3. 后端代表用户调用 GDrive API 时使用其 OAuth 令牌（不可使用服务账号）。

### US-003: GDrive 状态总览
- **作为** 专员 **我想要** 浏览 JR/KR/US Programs 目录下剧集并知晓是否已在 GCS **以便** 优先处理缺失剧集。
- **验收标准**
  1. GET `/api/pipeline/gdrive-status` 接收用户令牌、列出三个根目录的全部剧集（program code 命名），结构包含 `name`, `path`, `gdrive_id`.
  2. 后端使用服务账号列出 `vigloo_source` GCS bucket 下目录，返回 `in_gcs` 布尔标记。
  3. 前端页面展示树状/表格，缺失项标注（如红点）。

### US-004: 剧集详情与可选文件夹
- **作为** 专员 **我想要** 查看某剧集的子文件夹并勾选需要同步的目录 **以便** 只复制 Episode/Subtitles。
- **验收标准**
  1. GET `/api/pipeline/gdrive-roots` 返回 `.env` 中配置的 `PIPELINE_GDRIVE_ROOTS`（如 KR/JP/US Programs）供前端渲染根节点。
  2. GET `/api/pipeline/gdrive-browse?drive_folder_id=<id>&gcs_prefix=<可选>` 仅列出指定 folder_id 的一级子目录，返回 `[{ id, name, has_children, in_gcs }]`，其中 `in_gcs` 通过快速 GCS 前缀比对得出。
  3. 前端使用 Ant Design `Tree` + `loadData` 懒加载 GDrive 目录树，节点标题显示“✅ 已传输 / ⬜️ 未传输”标识，并允许逐层展开。
  4. “目录勾选”卡片复用 `/gdrive-browse` 构建树形复选框，勾选后将节点 `{id,name,path}` 回填到“传输确认”摘要，并暂时打印到控制台（为后续接入传输 API 做准备）。

### US-005: 传输任务排队
- **作为** 专员 **我想要** 选择目录并发起传输 **以便** 云端异步执行且可追踪。
- **验收标准**
  1. POST `/api/pipeline/transfer` 请求体 `{ drama_name, gdrive_path, include_folders[] }`；校验 drama_name 在状态列表中存在。
  2. API 在 Firestore `pipeline_jobs` 新建文档（包含 drama_name、source path、include_folders、状态 `QUEUED`、`stage=1`、用户信息、OAuth refresh token/短期 token 存储方案）。
  3. API 触发 Cloud Run Job `gdrive-transfer-worker`，传参 job_id（环境变量或参数），并安全传递用户 OAuth refresh token。
  4. 立即返回 202 + job_id。

### US-006: Firestore 实时监控
- **作为** 前端用户 **我想要** 实时查看任务状态/进度 **以便** 无需轮询。
- **验收标准**
  1. `/pipeline` 页面使用 Firestore Web SDK `onSnapshot` 监听 `pipeline_jobs`，过滤近期或按用户。
  2. UI 同时展示“传输进度（Episodes/Subtitles m/n）”与“压制进度（语种 m/n）”，并明确当前处于 `stage=TRANSFER` 还是 `stage=PROCESS`。
  3. 当传输阶段全部目录完成时，Job 自动标记 `transfer_completed=true` 并触发压制阶段；压制阶段的进度与失败状态独立记录。
  4. 任务列表显示 `status`, `stage`, `progress`, 时间戳和触发人，进度条实时更新。

### US-007: 传输 Worker（Cloud Run Job）
- **作为** 技术系统 **我想要** 可靠执行 rclone 传输 **以便** 将选定目录同步到 `vigloo_source/PROGRAM_CODE/`.
- **验收标准**
  1. `workers/transfer/` 包含 Dockerfile（python:3.11-slim + rclone + google-cloud-firestore + google-auth）。
  2. `main.py` 启动读取 `JOB_ID`、Firestore 文档、用户 OAuth token（刷新或访问 token）。
  3. 动态生成 `rclone.conf`（GDrive remote 使用用户 token，GCS remote 使用服务账号/ADC）。
  4. 根据 `include_folders` 构造 `--filter` 规则（允许多目录），执行 `rclone copy --progress`.
  5. 解析 `rclone -P` 输出，至少每 15 秒更新 Firestore：`status=TRANSFERRING`, `progress=NN%`, `bytes_transferred`.
  6. 完成后上传 `_PROCESS_NOW.txt` 至 `vigloo_source/DRAMA_NAME/`，内容包含 job_id 与时间戳。
  7. Firestore 更新 `status=PROCESSING`, `stage=1`, `progress=100%`, 并记录文件计数。
  8. 错误时写入 `status=FAILED`、`error_message`。

### US-008: 压制 Worker（Cloud Run Job）
- **作为** 技术系统 **我想要** 监测 `_PROCESS_NOW.txt` 并对剧集进行 ffmpeg 压制 **以便** 生成含字幕的成品。
- **验收标准**
  1. `workers/process/` 包含 Dockerfile（python:3.11-slim + ffmpeg + google-cloud-storage + google-cloud-firestore + chardet）。
  2. `process_drama.py` 通过 Eventarc 触发，解析对象路径，确定 `DRAMA_NAME`.
  3. Firestore 查询 `pipeline_jobs` 中 `drama_name` 与 `stage=1` 的任务，更新为 `status=PROCESSING`, `stage=2`.
  4. 逻辑：列出 `vigloo_source/DRAMA_NAME/` 下 mp4/srt，匹配 Episode + 语种，下载到本地临时目录，执行 ffmpeg 上字幕（字体 Noto Sans CJK，白字黑描边，距离底部 1/3）。
  5. 每完成一条输出 `progress` 如 `压制完成 (en): 5 / 80`.
  6. 产出上传到 `vigloo_processed/DRAMA_NAME/Subtitled_Episodes/<lang>/filename.mp4`.
  7. 所有文件完成后 Firestore 更新 `status=COMPLETE`, `stage=2`, `progress=全部压制完成`.
  8. 错误时写 `status=FAILED_STAGE2` 并附错误详情。

### US-009: 前端下载能力
- **作为** 剪辑师/专员 **我想要** 在完成后下载文件到本地或触发 NAS 下载 **以便** 快速交付。
- **验收标准**
  1. Job 处于 `stage=2 && status=COMPLETE` 时出现“下载”与“下载到 NAS”按钮。
  2. 前端调用 GET `/api/pipeline/processed-files?drama=...` 列出 `vigloo_processed` 下文件树。
  3. 选择文件后调用 GET `/api/pipeline/download-link?file_path=...` 生成带时效的签名 URL 并在浏览器触发下载。
  4. “下载到 NAS” 调用 POST `/api/pipeline/download-to-nas`，后端在 Firestore `nas_download_tasks` 创建文档（包含目标文件、优先级、状态），返回 202。

### US-010: 进度可视化 + 刷新
- **作为** 专员 **我想要** 刷新梯度并看到状态 **以便** 做出下一步操作。
- **验收标准**
  1. `/pipeline` 页面支持手动刷新（重新调用 `gdrive-status`）并保留当前展开态。
  2. 任务列表支持过滤器（全部、排队、传输中、压制中、完成、失败）。
  3. 失败任务展示错误信息，并允许重新触发（调 `transfer` 端点或后续"重试"端点 TBC）。

### US-019: 任务监控页面 UI 重构
- **作为** 运营专员 **我想要** 以剧集为单位查看任务状态 **以便** 快速了解每个剧集的整体进度。
- **验收标准**
  1. 顶部 Tab 筛选：
     - "进行中的任务"：显示 Firestore 中未标记结束的任务数量，点击后筛选显示这些任务对应的剧集卡片
     - "传输中"：显示传输中任务总数，点击后筛选显示传输中任务对应的剧集卡片
     - "压制中"：显示压制中任务总数（包括已传输完成在压制中 + 单独在压制），点击后筛选显示压制中任务对应的剧集卡片
     - "失败任务"：显示失败任务数量，点击后筛选显示失败任务对应的剧集卡片
     - "已完成任务"：显示最近30天已完成任务数量，点击后筛选显示已完成任务对应的剧集卡片
     - 每个 Tab 下方提供"清除筛选"按钮，点击后恢复默认展示（按最新创建任务排序的所有剧集卡片）
  2. 表格以 drama name 为单位聚合：
     - 每一行代表一个唯一的剧集名称（drama_name）
     - 如果该剧集下有多个执行中的任务，聚合在一张卡片中展示
     - 卡片包含以下分区：
       - 剧集名称（drama_name）
       - 传输任务区域：
         - 进行中的传输任务：显示任务 id、任务创建时间、传输状态、传输进度（实时进度，保留当前代码中的进度信息）
         - 已完成的传输任务：仅显示一个数字（已完成任务数）
       - 压制任务区域：
         - 进行中的压制任务：显示任务 id、任务创建时间、目标语种（从 srt 文件路径的上一级目录名称提取）、压制状态、压制进度条
         - 已完成的压制任务：仅显示一个数字（已完成任务数）
       - 失败任务区域：
         - 展示失败任务的解译后出错原因（不展示大段报错信息）
  3. 排序规则：以最新创建的任务为准，如果最新创建的任务对应的 drama_name 是 KR001，那么 KR001 这张卡片排在前面

### US-020: 任务取消与暂停功能
- **作为** 运营专员 **我想要** 取消排队中的任务或暂停进行中的任务 **以便** 灵活管理任务优先级和资源分配。
- **验收标准**
  1. 任务取消功能：
     - 每个状态为 `QUEUED`（排队中）的任务显示"取消"按钮
     - 点击"取消"按钮时，弹出强提醒对话框：
       - 标题："确认取消任务"
       - 内容："此操作不可撤销，确定要取消该任务吗？"
       - 按钮：取消（关闭对话框）、确认取消（执行取消操作）
     - 取消成功后，任务状态更新为 `CANCELLED`，前端实时更新显示
     - 后端 API：`POST /api/v1/pipeline/jobs/{job_id}/cancel`，需要验证任务状态为 `QUEUED` 才允许取消
  2. 任务暂停功能：
     - 每个状态为 `TRANSFERRING`（传输中）或 `PROCESSING`（压制中）的任务显示"暂停"按钮
     - 点击"暂停"按钮时，弹出确认对话框：
       - 标题："确认暂停任务"
       - 内容："暂停后任务将停止执行，可以稍后恢复。确定要暂停该任务吗？"
       - 按钮：取消（关闭对话框）、确认暂停（执行暂停操作）
     - 暂停成功后，任务状态更新为 `PAUSED`，前端实时更新显示
     - 后端 API：`POST /api/v1/pipeline/jobs/{job_id}/pause`，需要验证任务状态为 `TRANSFERRING` 或 `PROCESSING` 才允许暂停
     - Worker 需要支持检测 `PAUSED` 状态并停止执行（传输 Worker 停止 rclone，压制 Worker 停止 ffmpeg）
  3. 任务恢复功能（可选，后续实现）：
     - 状态为 `PAUSED` 的任务可以恢复执行
     - 恢复后任务状态更新为 `TRANSFERRING` 或 `PROCESSING`
     - 后端 API：`POST /api/v1/pipeline/jobs/{job_id}/resume`

### US-011: 下载/压制进度可视
- **作为** 运营管理者 **我想要** 看见压制完成率与剩余时间提示 **以便** 进行排期。
- **验收标准**
  1. Firestore 文档包含 `eta` 或 `last_update` 字段，前端显示“最近更新：xx 分钟前”。
  2. 如果 10 分钟无更新，UI 提示可能卡住。

### US-016: 资源流水线多页面分层

- **作为** 运营与技术专员 **我想要** 将传输操作、任务监控与资源浏览拆分到不同页面 **以便** 信息不过载并提高操作效率。
- **验收标准**
  - `/pipeline/plan`（传输计划页）
    - 第一行采用两列等宽布局：左侧为 GDrive 剧集树，右侧为目录勾选；第二行单列显示传输确认摘要，保证日志/统计信息横向铺满。
    - 树节点名称前使用状态圆点（绿=已传输，灰=未传输），页面标题区域提供图例说明。
    - 选定剧集后自动展开其第一层目录（例如 Episodes/Subtitles），便于立即确认需要勾选的目录。
    - 勾选 Episodes/Subtitles 等子目录后，可看到计划摘要：文件夹数、估算大小、目标 bucket、预计耗时。
    - 只暴露与“发起传输”相关的动作：刷新目录、全选/清空、确认提交。
  - `/pipeline/monitor`（任务监控页）
    - 顶部状态 Tab 筛选：
      - "进行中的任务"：Firestore 中未标记结束的任务（`status` 不为 `COMPLETE` 且 `status` 不为 `FAILED` 且 `status` 不为 `FAILED_STAGE2`）
      - "传输中"：总计有多少任务是在传输中（`stage=1` 且 `status=TRANSFERRING`）
      - "压制中"：总计有多少任务已传输完成在压制中，或者单独在压制（`stage=2` 且 `status=PROCESSING`，或 `type=manual` 且 `stage=1` 且 `status=PROCESSING`）
      - "失败任务"：有多少任务中存在失败项（`status=FAILED` 或 `status=FAILED_STAGE2`）
      - "已完成任务"：已经成功执行完的任务（`status=COMPLETE`，仅提取最近30天）
      - 交互：点击每个 Tab 起到筛选作用，展示存在该状态的剧集卡片；提供"清除筛选"按钮，点击后按默认顺序展示所有卡片
    - 表格以 drama name 为单位：
      - 每一行是一个唯一的剧集名称，如果该剧集下有多个执行中的任务，则被聚合在这个剧集下的一张卡片里
      - 卡片分区展示：
        - 剧集名称
        - 传输任务：如有多个进行中任务 id 可同时展示，显示任务 id、传输状态和传输进度（实时进度，当前代码中的进度信息可以保留），该剧下的已完成的传输任务仅显示一个数字（已完成任务数）
        - 压制任务：如有多个进行中任务 id 可同时展示，显示 id、压制的目标语种（取自具体 srt 文件所在的上一级目录名称）、压制状态和压制进度条，该剧已压制完成的任务仅显示一个数字（已完成任务数）
        - 失败任务：有失败报错的任务展现在这个区域，但不用大段展示报错信息，展示解译后的具体出错原因即可
      - 表格排序：以最新创建的任务为准，如最新创建的任务对应的 dramaname 是 KR001，那么 KR001 这张卡片靠前
  - `/pipeline/library`（资源浏览页）
    - Tab1 “未压制”：展示 `vigloo_source` 目录树，可展开到单个文件，支持关键字搜索与下载。
    - Tab2 “已压制”：一级目录 Program Code，二级目录语种（如 en/kr/jp/...），列出压制成品；支持下载、下载到 NAS、复制签名链接。
    - 两个 Tab 默认显示文件大小、最后更新时间，并可按 Program Code/语种过滤。

### US-012: CI/CD 与 Eventarc 自动化
- **作为** DevOps **我想要** 在部署时自动构建 Workers、部署 Cloud Run Job，并创建 Eventarc 触发器 **以便** 一键交付。
- **验收标准**
  1. `.github/workflows/backend-deploy.yaml` 新增步骤：构建/推送 `workers/transfer` 与 `workers/process` 镜像，执行 `gcloud run jobs deploy ... --cpu 4 --memory 16Gi --max-retries 1 --timeout 3h`.
  2. 工作流创建或更新 Eventarc trigger（`google.cloud.storage.object.v1.finalized`，目标 `drama-processor-job`，过滤 `_PROCESS_NOW.txt`）。若已存在则更新。
  3. 工作流确保 `vigloo_processed` bucket 存在，不存在则创建。

### US-017: Eventarc Relay Service
- **作为** 平台服务 **我想要** 在 GCS `_PROCESS_NOW.txt` 完成事件到达时，通过一个 Cloud Run Service 中继触发压制 Job **以便** 规避 Eventarc 无法直接调用 Cloud Run Job 的限制。
- **验收标准**
  1. FastAPI 新增模块 `backend/app/api/v1/relay.py` 并在 `router.py` 中以 `/api/v1/relay` 注册，暴露 `POST /event`。
  2. 端点接收 CloudEvents v1.0 JSON（`google.cloud.storage.object.v1.finalized`），解析 `bucket` 与 `name` 字段。若 `name` 不以 `_PROCESS_NOW.txt` 结尾则立即返回 200 并写日志，不触发 Job。
  3. 从对象路径解析 `DRAMA_NAME`（示例：`KR065P01S01/.../_PROCESS_NOW.txt`），构造 Job 所需环境变量：`DRAMA_NAME` 以及 `PIPELINE_DEFAULT_TOKEN_REF`（来自中继服务环境变量）。
  4. 调用 Cloud Run Admin API `projects.locations.jobs.run` 触发 `drama-processor-job`，使用 google-auth 生成 ID Token 并附 `Authorization: Bearer <token>`。调用结果（成功/失败）都写 Cloud Logging，但 HTTP 响应始终 200，避免 Eventarc 重试风暴。
  5. `.github/workflows/backend-deploy.yaml` 在三大 Job 部署后、主服务之前新增 `drama-processor-relay-service` 部署步骤，复用主镜像，`--timeout 60s --allow-unauthenticated --port 8000`，并注入 `PROCESSOR_JOB_NAME`（完整路径）与 `PIPELINE_DEFAULT_TOKEN_REF`。
  6. 本地调试指导：提供示例 curl/HTTPie 请求（带 CloudEvents JSON）命中 `/api/v1/relay/event`，借此模拟 Eventarc。
  7. IAM：运行该 relay service 的服务账号需具备 `roles/run.jobUser`，确保可调用 `jobs.run`；CI/CD 部署服务账号同样需要该角色以便设置/验证。

### US-018: 资源库（Library）页面功能增强
- **作为** 运营专员 **我想要** 在资源库页区分“已压制/待压制”并可手动触发压制流程 **以便** 在 rclone 完成后仍可补跑遗漏字幕，并在展开树形时不会丢失深层目录。
- **验收标准**
  1. 后端提供“待压制”列表：比较 `PIPELINE_GCS_SOURCE_BUCKET` 与 `PIPELINE_GCS_PROCESSED_BUCKET` 的一级目录，将源存在且 processed 缺失的剧集返回（`list_unprocessed_dramas()` 服务函数）。
  2. 后端暴露 `POST /api/v1/pipeline/process-manual`，请求体 `ManualProcessRequest`（`drama_name: str`, `file_paths: List[str]`），服务层 `trigger_manual_process_job()` 创建 Firestore job（`stage=1, status=TRANSFER_COMPLETED`），携带 `file_paths` 并直接触发 `drama-processor-job`。
  3. `pipeline_process_service`（或 scheduler）应复用 Cloud Run Job 触发逻辑，注入 `JOB_ID`、`REFRESH_TOKEN_REF`；`process` worker 支持读取 job `file_paths` 字段，当存在时优先按该列表生成 `SubtitlePair`（例如新增 `_build_manual_pairs`）。
  4. 前端 `/pipeline/library` 页面改为 “已压制 / 待压制” 双 Tab；待压制 Tab 调用新的 API、已压制沿用现有接口。Tab 切换时缓存各自的树数据。
  5. `ProgramBrowserTree` 修复懒加载：点击节点时能调用后端 GCS browse API 拉取子节点，支持多层展开；保持节点勾选状态传递至右侧详情卡。
  6. 右侧详情卡新增 “压制字幕” 按钮，仅在有选中文件/文件夹时启用；点击后调用 `triggerManualProcess()`，成功后提示“任务已加入监控列表”。
  7. 提供本地调试步骤：如何使用 `debug_rclone_filter.py` 验证 filter、以及如何在开发环境下手动触发 `process-manual` 请求，确保 rclone 及 Worker 端逻辑正确。

## 非功能需求

- **性能**: `gdrive-status` API 在 5k 剧集下响应 < 3s（分页或懒加载）；转发任务 API 延迟 < 1s；前端加载 Firestore 监听后 UI 更新延迟 < 1s。
- **可靠性**: 传输与压制 Job 支持失败重试策略（手动重试即可）；任务日志保存 90 天。Cloud Run Job 采用最低并发 1、最大并发 1，避免资源争用。
- **安全**: 所有 API 需验证 Google ID Token + Firestore 读写权限。用户 OAuth refresh token 需加密存储（Secret Manager 或 Firestore Field Encryption）。GCS 签名 URL 有效期 ≤ 12h。
- **可观察性**: Workers 输出写入 Cloud Logging，关键事件同步到 Firestore `logs` 子集合。

## 数据需求

- **Firestore**:
  - `pipeline_jobs`: `drama_name`, `gdrive_path`, `include_folders`, `status`, `stage`, `progress`, `created_by`, `created_at`, `updated_at`, `oauth_refresh_token_ref`, `gcs_prefix`, `stats`.
  - `nas_download_tasks`: `drama_name`, `files[]`, `priority`, `status`, `requested_by`, `assigned_to`, `notes`.
- **GCS**:
  - `vigloo_source`: 源文件 + `_PROCESS_NOW.txt`.
  - `vigloo_processed`: 产出目录（若不存在需自动创建）。
- **Secrets**: 记录 GDrive API client, OAuth refresh token encryption key, rclone config template。

## 集成需求

1. **Google Drive API**: 调用使用用户 OAuth token；需要列目录、下载 metadata、生成共享可下载链接供 rclone 使用。
2. **GCS API**: 使用服务账号（ADC）列目录、创建 buckets、生成签名 URL。
3. **Firestore**: FastAPI 与 Workers 均需读写；需要在 `startup` 中初始化客户端并重用。
4. **Cloud Run Jobs**: 需要 `jobs.run` 权限与 API；FastAPI 触发 Job 需使用 Projects.Locations.Jobs.Run API（REST 或 `gcloud`）。
5. **Eventarc**: GCS 事件触发 `drama-processor-job`；需要 Pub/Sub + Service Agent 权限。

## 约束与假设

- **技术**: 前端维持 Next.js 14 + TypeScript；后端 FastAPI + Python 3.11；Workers 采用 Python 3.11 + shell/rclone/ffmpeg。
- **账号**: 生产和开发沿用既有 Cloud Run 服务账号（`sa-run-prod@...`, `sa-dev@...`），需要附加 Firestore、Drive API 调用、Run Jobs 权限。
- **网络**: 所有操作在云端完成，用户端仅发起 API。
- **假设**:
  - 韩国团队 Google Drive 目录结构稳定，Program Code 作为目录名。
  - 每个剧集 Episodes/Subtitles 命名含 `Episode/Subtitles` 文本，可通过模式匹配。
  - NAS 轮询脚本会在后续由人工实现并消费 `nas_download_tasks` 集合。

## 待定事项 (TBD)

1. **OAuth Token 托管方式**: 是保存 refresh token 于 Firestore 加密字段，还是要求专员每次登录重新授权？
2. **进度监听范围**: 是否需要按 dramacode 过滤 Firestore 监听以减少读费用？
3. **rclone 限速策略**: 需确认目标带宽及避开 KR 团队限额的配置。
4. **字幕样式模板**: 是否需要多语字体/颜色定制？目前要求 Noto Sans CJK。
5. **NAS 下载任务执行频率**: 需专员提供预计的轮询频率以设置 TTL/优先级逻辑。

## 验收测试场景 (高层)

1. **端到端同步**: 登录 → 选定 `KR065` → 勾选 Episodes/Subtitles → 提交 → Firestore 看到 job queued → 传输 worker 更新进度 → `_PROCESS_NOW` 触发压制 → Firestore 标记 COMPLETE → 前端显示下载按钮。
2. **权限校验**: 使用非白名单 Gmail 登录，所有 Pipeline API 返回 401。
3. **失败恢复**: 人为让 rclone 失败，Firestore 记录 `FAILED`，前端显示错误并允许重新触发。
4. **下载链路**: Job 完成后列出 `vigloo_processed` 文件，点击下载生成签名 URL，可直接下载；NAS 下载创建任务文档。
5. **CI/CD**: 推送 main 触发 GitHub Actions，成功构建两套 Job 镜像、部署 Cloud Run Jobs，并确认 Eventarc trigger 存在。

## 参考资源 & 约束重述

- GCP 项目：`fleet-blend-469520-n7`（后端 + Workers）。
- Firebase 项目：`autogrowth-477909`（前端托管）。
- GCS 桶：`vigloo_source`（已存在）、`vigloo_processed`（需创建）。
- Cloud SQL：实例 `yvideo-factory-db-prod` / 数据库 `auto_growth` / 用户 `appdev` / 密码 `930828Krisrita*`.
- Cloud Run 服务账号：生产 `sa-run-prod@...`、开发 `sa-dev@...`。

---

*本需求文档编写完成，等待审批。*

