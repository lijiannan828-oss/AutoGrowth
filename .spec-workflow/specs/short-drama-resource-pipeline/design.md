# 设计文档

## 基本信息
- **规范名称**: `short-drama-resource-pipeline`
- **阶段**: 设计（Design）
- **状态**: 待审批
- **关联**: 已批准的《需求文档》

## 架构总览

### 目标
将 AutoGrowth 扩展为“短剧资源流水线控制面板”。在保留“命名工具”的同时，新增“资源同步与压制”模块，通过云端 Web 界面完成从 GDrive 同步到 GCS，再到 ffmpeg 压制与下载的全流程，任务状态由 Firestore 实时驱动。

### 高层架构
```
Next.js (frontend) ───────────────┐
  - Google Sign-In                │  HTTPS
  - Firestore onSnapshot          ▼
                             FastAPI (Cloud Run Service)
                             - 验证 Google ID Token / Firebase ID Token
                             - 初始化 Firestore 客户端
                             - 调用 Drive API（使用用户 OAuth 令牌）
                             - 调用 GCS（服务账号）
                             - 触发 Cloud Run Jobs（transfer/process）
                             - 生成签名 URL
          ▲                                                │
          │Firestore 实时变更                               │Run Jobs API / Eventarc
          │                                                ▼
  Browser UI ◀────────────── Firestore (Native mode) ◀─── Cloud Run Job (Worker 1: rclone)
                                                               │  上传 _PROCESS_NOW.txt
                                                               ▼
                                                           Eventarc → Cloud Run Job (Worker 2: ffmpeg)
                                                               │  产出上传 vigloo_processed
                                                               ▼
                                                           Google Cloud Storage
```

### 关键设计决策
- Drive 访问必须使用“真人账号”的 OAuth 令牌（因为资源是 “Share with me”）。前端通过 Google 登录，后端验证 ID Token，并在“排队任务”时确保 Worker 可以使用用户刷新令牌访问 GDrive。
- 后端与 Workers 访问 Firestore/GCS 使用运行时服务账号（ADC）；仅 Worker 访问 Drive 使用用户令牌。
- 传输、压制均由 Cloud Run Job 异步执行，FastAPI 仅编排并即时返回 202。
- Firestore 作为任务编排/状态存储；前端用 onSnapshot 实时更新。
- GCS 信号文件 `_PROCESS_NOW.txt` 作为转入压制阶段触发器（Eventarc）。

## 前端设计（Next.js 14 + TS）

### 导航与布局
- 修改 `frontend/src/app/layout.tsx`：
  - 引入持久化侧边栏（Shell），包含：
    - “命名工具” → `/`
    - “资源流水线” → `/pipeline`
  - 当前路由高亮，页面区域用于展示功能。

### 资源流水线页面分层
- 采用 Next.js App Router 子路由结构：
  - `/pipeline/plan` → 传输计划页（默认入口）
  - `/pipeline/monitor` → 任务监控页
  - `/pipeline/library` → 资源浏览页
- `SidebarNav` 中新增二级链接或在 `/pipeline` 下提供内嵌标签，方便切换。

#### `/pipeline/plan`（Transfer Planner）
- 目标：聚焦“选择&确认”动作，操作员仅看到 GDrive 与本次传输相关信息。
- 布局：
  - 第一行使用两列等宽 Grid：左卡“剧集目录”、右卡“目录勾选”。两卡都使用 Antd Tree 的 `loadData` 懒加载，并在标题区域提供状态圆点图例（绿=已传输，灰=未传输），树节点标题同样将圆点置于文件夹名称左侧以统一对齐。
  - 第二行单列展示“传输确认”卡片，横向宽度与上方两卡一致，用于呈现统计信息、路径摘要与操作按钮。
- 交互细节：
  - 剧集目录：首次仅渲染 `PIPELINE_GDRIVE_ROOTS`（调用 `gdrive-roots`），展开根节点时通过 `Tree.loadData` 调 `gdrive-browse` 列出 Program。选中剧集后，右侧卡片会在数据返回后自动展开第一层目录（Episodes/Subtitles 等）。
  - 目录勾选：以选定 Program folderId 为根继续调用 `gdrive-browse` 懒加载子目录，勾选后收集 `{id,name,path}`。开发态仍打印到控制台，正式串 `/transfer` 时可直接复用该结构。
  - 传输确认：展示 Program Code、源/目标路径、已选目录统计及 Tag 列表；按钮区提供“刷新目录（触发 query invalidate）”与“开始传输”。
- 动作：
  - 当前阶段点击“开始传输”仅打印选中目录，后续再串联 POST `/api/pipeline/transfer`。
  - 成功后显示 toast + link 跳转到 `/pipeline/monitor`.

#### `/pipeline/monitor`（Operations Monitor）
- 目标：集中展示所有任务状态，以剧集为单位聚合展示，提供筛选和重试入口。
- UI 结构：
  - **顶部 Tab 筛选栏**：
    - Tab 1: "进行中的任务" - 显示未标记结束的任务数量（`status` 不为 `COMPLETE`、`FAILED`、`FAILED_STAGE2`）
    - Tab 2: "传输中" - 显示传输中任务总数（`stage=1` 且 `status=TRANSFERRING`）
    - Tab 3: "压制中" - 显示压制中任务总数（`stage=2` 且 `status=PROCESSING`，或 `type=manual` 且 `stage=1` 且 `status=PROCESSING`）
    - Tab 4: "失败任务" - 显示失败任务数量（`status=FAILED` 或 `status=FAILED_STAGE2`）
    - Tab 5: "已完成任务" - 显示最近30天已完成任务数量（`status=COMPLETE`）
    - Tab 下方提供"清除筛选"按钮，点击后恢复默认展示
  - **表格区域**（以 drama_name 为单位）：
    - 每一行代表一个唯一的剧集名称（drama_name）
    - 如果该剧集下有多个执行中的任务，聚合在一张长卡片中展示
    - 卡片分区结构：
      - **剧集名称区域**：显示 drama_name（如 `KR051P07S01_김대표의 엽기적인 부인`）
      - **传输任务区域**：
        - 进行中的传输任务：显示任务 id、任务创建时间（`created_at`，格式化为相对时间如"2 小时前"或绝对时间）、传输状态（`QUEUED`/`TRANSFERRING`）、传输进度（实时进度条，从 Firestore `stats.bytes_total/bytes_done` 计算，保留当前代码中的进度信息如 `Episodes 12/12, Subtitles 10/12`）
        - 状态为 `QUEUED` 的任务显示"取消"按钮，点击后弹出强提醒对话框确认取消
        - 状态为 `TRANSFERRING` 的任务显示"暂停"按钮，点击后弹出确认对话框暂停任务
        - 已完成的传输任务：仅显示一个数字（已完成任务数，统计该剧集下 `status=COMPLETE` 且 `stage=1` 的任务数）
      - **压制任务区域**：
        - 进行中的压制任务：显示任务 id、任务创建时间（`created_at`，格式化为相对时间如"2 小时前"或绝对时间）、目标语种（从 srt 文件路径的上一级目录名称提取，如 `Subtitles/en/` → `en`）、压制状态（`PROCESSING`）、压制进度条（从 Firestore `process_stats` 计算，如 `5/80`）
        - 状态为 `PROCESSING` 的任务显示"暂停"按钮，点击后弹出确认对话框暂停任务
        - 已完成的压制任务：仅显示一个数字（已完成任务数，统计该剧集下 `status=COMPLETE` 且 `stage=2` 的任务数）
      - **失败任务区域**：
        - 展示失败任务的解译后出错原因（不展示大段原始报错信息，需要后端提供错误解译逻辑）
        - 显示失败时间、失败任务 id
- 交互细节：
  - 点击 Tab 后，表格仅展示符合该 Tab 状态的剧集卡片（通过前端过滤或后端查询实现）
  - 点击"清除筛选"后，恢复默认展示：按最新创建的任务排序（如果最新创建的任务对应的 drama_name 是 KR001，那么 KR001 这张卡片排在前面）
  - 每个剧集卡片支持展开/折叠，展开后显示该剧集下所有任务的详细信息
- 技术实现：
  - 使用 Firestore `onSnapshot` + query（限制最近 N 天），避免一次订阅过多文档
  - 前端聚合逻辑：按 `drama_name` 分组，计算每个剧集下的任务统计信息
  - 排序逻辑：找到每个剧集下最新创建的任务（`created_at` 最大），按该时间戳倒序排列剧集卡片

#### `/pipeline/library`（Resource Explorer）
- 功能：浏览/搜索/下载 GCS 文件，分“未压制”“已压制”两类。
- Tab 1 未压制：
  - 使用树控件展示 `vigloo_source`，支持懒加载子节点（调用新的后端 API 或 reuse processed-files with `type=source`）。
  - 支持关键字搜索（client 侧 fuzzy + server filter）。
  - 为每个文件提供下载/复制路径/下载到 NAS 操作。
- Tab 2 已压制：
  - 一级 Program Code，二级语种（en/kr/jp/...），下钻至文件列表。
  - 提供筛选（Program Code、语种、更新时间范围）。
  - 行动点：下载（签名 URL）、下载到 NAS、复制 GCS 路径。
- 与 `/pipeline/monitor` 打通：完成的任务可携带 query param `program` 自动选中对应 Program。

### 身份认证（前端）
- 使用 Google 登录（可沿用 Firebase Authentication 的 Google Provider，或 Google Identity Services）。
- 登录成功后将 ID Token 附到请求（Authorization: Bearer <id_token>）。
- Firestore Web SDK 访问策略：仅用于订阅 `pipeline_jobs`；安全规则采用“严格”模式并限制读取范围（如仅允许白名单用户，或按创建者过滤）。

## 后端设计（FastAPI）

### 依赖与初始化
- `requirements.txt` 新增：
  - `google-cloud-firestore`
  - `google-auth`
  - `google-cloud-storage`
  - `google-api-python-client`（或 `googleapiclient` + `google-auth-oauthlib`）用于 Drive 调用
- `app/main.py`：
  - 在 lifespan 启动时初始化 Firestore 客户端（全局单例），优先从 ADC 读取凭证。
  - CORS 来源从环境变量 `FRONTEND_ORIGINS` 读取（逗号分隔），allow_credentials=true。

### 认证策略（后端）
- 前端传入 Google ID Token：
  - 验证方式 1：使用 Google 公钥（OIDC JWKS）验证（偏底层）。
  - 验证方式 2（推荐）：使用 Firebase Admin SDK 校验（若沿用 Firebase 登录，集成更简单）。
- 若需要后续访问 Drive，需交换/保存用户 OAuth 刷新令牌：
  - 前端初次授权获取 `auth_code` → 后端通过 OAuth client 交换到 `access_token` + `refresh_token`（一次性），将 `refresh_token` 加密保存（Secret Manager 或 Firestore 加密字段）。
  - FastAPI 触发 Job 时将 `refresh_token` 的“引用”或密文凭证注入 Worker 作为环境变量（Worker 再用 client_id/client_secret 刷新出 access token）。
  - 最小化存储：仅保存 refresh token（不可保存明文 access token，过期短）。

> 注意：如果使用 Firebase 仅能得到 ID Token，不包含 Drive 的 refresh token。则需要一次 OAuth 授权流（scope: `https://www.googleapis.com/auth/drive.readonly`）以便后端获得 refresh token。可以在 `/pipeline` 首次使用时引导完成授权。

### 新增 API 设计

1) POST `/api/v1/pipeline/jobs/{job_id}/cancel`
- 认证：需要有效 Google ID Token。
- 请求体：无（job_id 从路径参数获取）
- 流程：
  - 验证任务状态为 `QUEUED`，否则返回 400
  - 更新 Firestore 文档：`status="CANCELLED"`, `cancelled_at=now()`, `cancelled_by=current_user.email`
  - 如果任务已触发 Cloud Run Job，尝试取消 Job 执行（可选，取决于 Job 是否已启动）
  - 返回 200 + `{ job_id, status: "CANCELLED" }`
- 错误：任务不存在（404）、任务状态不允许取消（400）、权限不足（403）

2) POST `/api/v1/pipeline/jobs/{job_id}/pause`
- 认证：需要有效 Google ID Token。
- 请求体：无（job_id 从路径参数获取）
- 流程：
  - 验证任务状态为 `TRANSFERRING` 或 `PROCESSING`，否则返回 400
  - 更新 Firestore 文档：`status="PAUSED"`, `paused_at=now()`, `paused_by=current_user.email`
  - Worker 在下次轮询 Firestore 时检测到 `PAUSED` 状态，停止执行并退出
  - 返回 200 + `{ job_id, status: "PAUSED" }`
- 错误：任务不存在（404）、任务状态不允许暂停（400）、权限不足（403）

3) POST `/api/v1/pipeline/jobs/{job_id}/resume`（可选，后续实现）
- 认证：需要有效 Google ID Token。
- 请求体：无（job_id 从路径参数获取）
- 流程：
  - 验证任务状态为 `PAUSED`，否则返回 400
  - 更新 Firestore 文档：`status` 恢复为 `TRANSFERRING` 或 `PROCESSING`（根据 `stage` 判断），`resumed_at=now()`, `resumed_by=current_user.email`
  - 重新触发对应的 Cloud Run Job（传输或压制）
  - 返回 200 + `{ job_id, status: "TRANSFERRING" | "PROCESSING" }`
- 错误：任务不存在（404）、任务状态不允许恢复（400）、权限不足（403）

4) GET `/api/pipeline/gdrive-status`
- 认证：需要有效 Google ID Token。
- 流程：
  - 使用用户 access token 或使用保存的 refresh token 刷新出 access token。
  - 调用 Drive API 列出 `JR Programs`、`KR Programs`、`US Programs` 下一级目录（剧集）。
  - 使用服务账号列出 `vigloo_source/` 下已有目录。
  - 返回数组：`[{ name, path, gdrive_id, in_gcs }]`。

2) GET `/api/pipeline/gdrive-roots`
- 认证：Google ID Token。
- 流程：读取 `.env` 中的 `PIPELINE_GDRIVE_ROOTS`，返回 `[{ label, folder_id }]`，供前端渲染根节点。

3) GET `/api/pipeline/gdrive-browse?drive_folder_id=<id>&gcs_prefix=<可选>`
- 认证：Google ID Token。
- 流程：
  - 使用用户 Drive 凭证列出 `drive_folder_id` 下一级（仅 `mimeType=folder`）目录。
  - 对每个目录判断是否还存在子目录（`has_children`)，并调用 GCS 客户端快速检查 `vigloo_source/<gcs_prefix>/<folder_name>` 是否存在（`in_gcs`）。
  - 返回 `[{ id, name, has_children, in_gcs }]`，供前端树控件懒加载。

4) POST `/api/pipeline/transfer`
- 认证：Google ID Token。
- 请求体：
```json
{ "drama_name": "KR065", "gdrive_path": "KR Programs/KR065", "include_folders": ["[Final]Episodes", "[Final]Subtitles"] }
```
- 流程：
  - 在 `pipeline_jobs` 创建文档：
    - `status="QUEUED"`, `stage=1`, `created_by`, `drama_name`, `gdrive_path`, `include_folders`, `created_at/updated_at`
    - 保存 `oauth_refresh_token_ref`（或加密后的 refresh token）
  - 触发 Cloud Run Job `gdrive-transfer-worker`，将 `JOB_ID=<doc_id>` 和 `REFRESH_TOKEN_REF=...` 注入环境变量。
  - 返回 202 和 `job_id`。

5) GET `/api/pipeline/processed-files?drama=...`
- 认证：服务账号（后端）列出 `vigloo_processed/<drama>/` 的对象树，返回扁平/树形结构。

6) GET `/api/pipeline/download-link?file_path=...`
- 认证：后端使用 SA 生成签名 URL（有效期≤12h），返回 `{ url }`。

7) POST `/api/pipeline/download-to-nas`
- 认证：记录 Firestore 文档 `nas_download_tasks`，包含 `files[]/priority/requested_by/status="QUEUED"`。

8) POST `/api/pipeline/batch-urls`
- 认证：Google ID Token。
- 请求体：`{ paths: string[] }` - GCS 路径列表（支持文件或目录）
- 流程：解析每个路径，如果是文件则生成签名 URL，如果是目录则列出所有文件并生成签名 URL
- 返回：`{ files: [{ path: string, url: string, size: number }] }`

9) GET `/api/pipeline/download-proxy?file_path=...`
- 认证：Google ID Token。
- 流程：通过后端代理流式传输 GCS 文件，解决前端 CORS 限制
- 返回：StreamingResponse，流式传输文件内容
- 说明：NAS 端脚本后续轮询该集合（本项目不实现该脚本）。

### 错误与审计
- 错误：统一返回 JSON 错误结构；重要失败写入 Firestore 文档 `error_message`，并追加到 `jobs/{id}/logs` 子集合。
- 审计：记录每次 API 调用的 `user/email`, `job_id`, `action`, `timestamp`。

## Worker 1：GDrive 传输器（Cloud Run Job）

### 目录与镜像
- 代码：`workers/transfer/`
  - `Dockerfile`: 基于 `python:3.11-slim`；安装 `rclone`, `google-cloud-firestore`, `google-auth`, `google-auth-oauthlib`。
  - `main.py`: 传输脚本。
- 运行参数建议：
  - `--cpu 4 --memory 16Gi --timeout 3h --max-retries 1 --task-timeout 3h`

### 运行流程
1. 读取环境变量：`JOB_ID`，`REFRESH_TOKEN_REF`（或加密 token），`GCP_PROJECT`, `GCS_SOURCE_BUCKET=vigloo_source`。
2. Firestore 获取任务文档；获取 `drama_name`, `gdrive_path`, `include_folders`。
3. **检查任务状态**：如果 `status="PAUSED"` 或 `status="CANCELLED"`，立即退出，不执行传输。
4. 使用 `client_id/client_secret + refresh_token` 刷新出 `access_token`（Drive read-only）。
5. 动态生成 `rclone.conf`：
   - `[my-drive] type=drive; token=...`（包含 access token/refresh token 结构）
   - `[my-gcs] type=google cloud storage; project_number=...`（或使用 `gcs` 官方 rclone 驱动）
6. 生成过滤规则：
   - 多 include：`--filter="+ /[Final]Episodes/**" --filter="+ /[Final]Subtitles/**" --filter="- **"`
7. 执行复制（在循环中定期检查状态）：
   - `rclone copy "my-drive:<gdrive_path>" "my-gcs:vigloo_source/<DRAMA_NAME>" -P --transfers=8 --checkers=8 --drive-shared-with-me`
   - 在执行过程中，每 15 秒检查一次 Firestore 任务状态，如果 `status="PAUSED"` 或 `status="CANCELLED"`，立即停止 rclone 进程并退出
8. 解析 `-P` 进度（stdout），定期（≤15s）更新 Firestore：
   - `status="TRANSFERRING"`, `progress="31%"`, `bytes_transferred`, `last_update`.
   - 同时检查任务状态，如果被暂停或取消，停止执行
9. 完成后上传 `_PROCESS_NOW.txt` 到 `vigloo_source/<DRAMA_NAME>/_PROCESS_NOW.txt`；内容包含 `job_id`、时间戳。
10. 更新任务：`status="PROCESSING"`, `stage=1`, `progress="100%"`。
11. 异常捕获：`status="FAILED"`, `error_message=...`。

> 兼容“Shared with me”：rclone 需要 `--drive-shared-with-me`；或在 Drive API 端列出并用 `driveId`/`corpora="user"` + `supportsAllDrives`。

## Worker 2：视频压制器（Cloud Run Job）

### 目录与镜像
- 代码：`workers/process/`
  - `Dockerfile`: 基于 `python:3.11-slim`；安装 `ffmpeg`, `google-cloud-storage`, `google-cloud-firestore`, `chardet`, 字体 `noto-cjk`。
  - `main.py`: 压制脚本。
- 触发：Eventarc（`google.cloud.storage.object.v1.finalized`）针对 `vigloo_source`，后缀 `_PROCESS_NOW.txt`。
- 运行参数建议：
  - **生产环境**：`--cpu=2 --memory=4Gi --task-timeout=2h --max-retries=1`
  - **并发控制**：通过 `task_count` 参数实现水平扩展（见下方 Sharding 架构）

### Sharding 架构（水平扩展）

#### 架构概述
从 **单实例串行处理** 迁移到 **Cloud Run Jobs 分片（Sharding）并行处理** 模式，解决大规模视频处理（500+）时的内存累积（OOM）问题。

#### 核心机制
- **分片算法**：利用 Cloud Run Jobs 的 `CLOUD_RUN_TASK_INDEX` 和 `CLOUD_RUN_TASK_COUNT` 环境变量
- **资源隔离**：每个 Task 是独立的容器实例，处理完即销毁，彻底解决内存泄漏
- **并发控制**：Job 的并发度（Parallelism）由部署配置控制，代码层面无需关心

#### 分片逻辑
```python
# 获取环境变量（默认为单实例模式）
task_index = int(os.environ.get("CLOUD_RUN_TASK_INDEX", "0"))
task_count = int(os.environ.get("CLOUD_RUN_TASK_COUNT", "1"))

# 获取所有待处理的视频列表
all_episodes = [...]  # 从 GCS 或 Firestore 获取

# 使用取模算法分配任务
my_episodes = [
    e for i, e in enumerate(all_episodes) 
    if i % task_count == task_index
]
```

#### 任务分配策略
- **理想情况**：1 个 Task 处理 1-5 个视频
- **动态计算**：`task_count = ceil(total_episodes / 5)` 或 `task_count = total_episodes`（1:1 映射）
- **触发逻辑**：在 `pipeline_process_service.py` 中，根据待处理文件数量动态设置 `task_count`

#### 资源优化
- **内存限制**：每个 Task 使用 4GB 内存（足够处理单个视频）
- **CPU 限制**：2 vCPU（适配 FFmpeg `-threads` 参数）
- **FFmpeg 参数**：
  - 动态线程数：`min(multiprocessing.cpu_count(), 4)` 或设为 `0`（自动检测）
  - Preset：`veryfast`（提升速度）
  - CRF：`23`（平衡画质与体积）
  - 保留：`-movflags +faststart`（Web 播放优化）

#### 资源清理
- **显式清理**：每个视频处理完成后立即删除临时文件（`video_path`, `subtitle_path`, `output_path`）
- **内存回收**：显式调用 `gc.collect()` 强制垃圾回收
- **单实例串行**：移除内部并发（`ThreadPoolExecutor`），依靠 Cloud Run 的水平扩展实现并发

#### 优势
1. **解决 OOM**：每个 Task 只处理少量文件，用完即毁，无内存累积
2. **水平扩展**：可根据文件数量动态调整并发度
3. **故障隔离**：单个 Task 失败不影响其他 Task
4. **资源效率**：小规格容器（4GB/2CPU）成本更低

### 运行流程（Sharding 模式）

1. **获取分片信息**：
   - 读取环境变量 `CLOUD_RUN_TASK_INDEX`（默认为 0）和 `CLOUD_RUN_TASK_COUNT`（默认为 1）
   - 打印日志：`"Task {index}/{count}: Starting processing"`

2. **从事件中解析对象路径**，提取 `DRAMA_NAME`（或从 `JOB_ID` 环境变量获取）

3. **Firestore 查询** `pipeline_jobs` where `drama_name==DRAMA_NAME && stage==1`（limit 1）

4. **检查任务状态**：如果 `status="PAUSED"` 或 `status="CANCELLED"`，立即退出

5. **更新状态**：`status="PROCESSING"`, `stage=2`

6. **列出所有待处理文件**：
   - 列出 `vigloo_source/DRAMA_NAME/` 下 mp4/srt
   - 语种推断：文件名包含 `_en/_jp/_kr/_th/_id` 等；也可基于路径子目录命名
   - 字幕编码检测：`chardet`，必要时转为 UTF-8
   - 匹配策略：
     - Episode 文件：基于文件名中的 `ep\d+` 或统一规则
     - 字幕：按语言对应最近似的同名/同集数文件
   - 生成 `all_episodes` 列表（所有视频/字幕配对）

7. **分片分配**：
   - 使用取模算法：`my_episodes = [e for i, e in enumerate(all_episodes) if i % task_count == task_index]`
   - 打印日志：`"Task {index}/{count}: Claimed {len(my_episodes)} of {len(all_episodes)} episodes"`

8. **初始化 Task 状态文档**：
   - 在 `pipeline_jobs/{job_id}/tasks/{task_index}` 创建文档：
     ```python
     task_ref = job_ref.collection("tasks").document(str(task_index))
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

9. **串行处理分配的片段**（单实例内部必须串行，以节省内存）：
   - 对每个 `pair` 在 `my_episodes` 中：
     a. **更新当前文件**：`task_ref.update({"current_file": f"{pair.language}/ep{pair.episode}.mp4"})`
     b. 下载到本地临时目录（容器可写 `/tmp`）
     c. **FFmpeg 压制**：
        - 动态线程数：`min(multiprocessing.cpu_count(), 4)` 或 `0`（自动检测）
        - Preset：`veryfast`
        - CRF：`23`
        - 保留：`-movflags +faststart`
        - 使用 `-vf subtitles=...,force_style='FontName=Noto Sans CJK,...'`
     d. **上传成品**到 `vigloo_processed/DRAMA_NAME/<lang>/epXX.mp4`
     e. **处理成功**：
        - 更新 Task 文档：`task_ref.update({"success_files": firestore.ArrayUnion([文件名]), "progress_count": firestore.Increment(1)})`
        - **原子更新主文档**：`job_ref.update({"processed_files": firestore.Increment(1)})`
     f. **处理失败**：
        - 更新 Task 文档：`task_ref.update({"failed_files": firestore.ArrayUnion([{"path": 文件名, "error": 错误信息}]), "progress_count": firestore.Increment(1)})`
        - **原子更新主文档**：`job_ref.update({"failed_files": firestore.Increment(1)})`
        - 记录到 `processing_failures` 集合（保持原有逻辑）
     g. **显式清理**：立即删除 `video_path`, `subtitle_path`, `output_path`
     h. **内存回收**：调用 `gc.collect()`
     i. **检查任务状态**：如果主文档 `status="PAUSED"` 或 `status="CANCELLED"`，停止处理

10. **完成处理**：
    - 更新 Task 文档：`task_ref.update({"status": "COMPLETED", "current_file": None, "updated_at": SERVER_TIMESTAMP})`
    - 打印日志：`"Task {index}/{count}: Completed {successes}/{total} episodes"`
    - **注意**：
      - Worker **不修改**主文档的 `status` 为 `COMPLETE`
      - 主文档的状态由外部查询逻辑判断（当 `processed_files + failed_files == total_files` 时视为完成）
      - 前端可以通过查询 `tasks` 子集合获取每个 Task 的详细进度

10. **异常处理**：
    - 单个视频失败：记录到 `processing_failures`，继续处理下一个
    - Task 级失败：记录错误，不影响其他 Task

## 浏览器直接下载实现方案（File System Access API）

### 架构概述
采用 **File System Access API (Window.showDirectoryPicker)** 技术实现浏览器直接下载到本地，废弃了之前的 ZIP 打包方案。核心流程：
1. 用户点击"下载"按钮
2. 浏览器弹出文件夹选择器（`window.showDirectoryPicker()`）
3. 前端并发下载文件并直接写入用户选定的本地目录
4. 保持 GCS 目录结构

### 关键技术点

#### 1. 前端实现（`frontend/src/context/ZipDownloadContext.tsx`）

**用户手势上下文要求**：
- `window.showDirectoryPicker()` **必须在用户手势（如点击事件）中直接调用**
- 不能在 `await` 异步操作之后调用，否则会被浏览器阻止
- 正确顺序：先调用 `showDirectoryPicker()`，再获取文件列表

```typescript
// ✅ 正确：在用户手势中直接调用
const dirHandle = await window.showDirectoryPicker();

// ❌ 错误：在异步操作后调用会被阻止
const files = await fetchBatchDownloadUrls(paths);
const dirHandle = await window.showDirectoryPicker(); // 会被阻止
```

**文件流写入**：
- 使用 `response.body.pipeTo(writable)` 进行流式写入
- **重要**：`pipeTo()` 会自动关闭 `writable` 流，**不要手动调用 `writable.close()`**
- 错误处理时检查 `writable.readyState !== 'closed'` 再尝试关闭

```typescript
// ✅ 正确：pipeTo 会自动关闭流
await response.body.pipeTo(writable);

// ❌ 错误：会导致 "Cannot close a CLOSED writable stream" 错误
await response.body.pipeTo(writable);
await writable.close(); // 不要这样做！
```

**目录结构保持**：
- 使用 `getDirectoryHandle()` 递归创建目录结构
- 路径处理：`file.path` 是相对于 bucket 的完整路径，需要解析出目录和文件名

#### 2. 后端实现（`backend/app/api/v1/pipeline.py`）

**CORS 问题解决**：
- 前端直接访问 GCS signed URLs 会被 CORS 策略阻止
- 解决方案：后端提供 `/api/pipeline/download-proxy` 代理端点
- 后端从 GCS 读取文件并流式传输给前端，添加必要的 CORS headers

**流式传输实现**：
- 使用 FastAPI `StreamingResponse` 和生成器函数
- **重要**：在读取文件前调用 `blob.reload()` 刷新元数据，确保 `blob.size` 正确
- 使用 `blob.open("rb")` 打开文件流，分块读取（8KB）并 yield

```python
# ✅ 正确：刷新 blob 元数据
blob.reload()

def generate():
    with blob.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            yield chunk
```

**API URL 构建**：
- 前端必须使用正确的后端 API URL（`http://localhost:8000/api`）
- 不要使用前端开发服务器 URL（`http://localhost:3001`）
- 使用 `apiClient.defaults.baseURL` 确保使用正确的 base URL

### 常见问题与解决方案

#### 问题 1: CORS 错误
**症状**：浏览器控制台显示 "Access to fetch at 'https://storage.googleapis.com/...' has been blocked by CORS policy"

**原因**：前端直接访问 GCS signed URLs 时，GCS 响应不包含 `Access-Control-Allow-Origin` header

**解决方案**：使用后端代理端点 `/api/pipeline/download-proxy`，后端添加 CORS headers

#### 问题 2: 文件夹选择器不弹出
**症状**：点击下载按钮后没有任何反应

**原因**：
1. `showDirectoryPicker()` 在异步操作后调用，失去了用户手势上下文
2. API 路径错误（如使用前端开发服务器 URL）

**解决方案**：
1. 确保 `showDirectoryPicker()` 在用户点击事件处理函数中直接调用
2. 使用正确的后端 API URL（`apiClient.defaults.baseURL`）

#### 问题 3: 文件大小为 0 字节
**症状**：下载成功但文件大小为 0

**原因**：
1. `pipeTo()` 后手动调用 `writable.close()` 导致流被提前关闭
2. 后端 `blob.size` 为 `None`，生成器没有正确读取数据

**解决方案**：
1. 移除 `pipeTo()` 后的 `writable.close()` 调用
2. 后端在读取前调用 `blob.reload()` 刷新元数据
3. 添加详细的日志追踪文件流状态

#### 问题 4: "Cannot close a CLOSED writable stream" 错误
**症状**：下载过程中出现此错误

**原因**：`pipeTo()` 已经自动关闭了流，再次调用 `close()` 会报错

**解决方案**：移除 `pipeTo()` 后的 `writable.close()` 调用，错误处理时检查 `readyState`

### 文件位置
- 前端：`frontend/src/context/ZipDownloadContext.tsx`
- 后端：`backend/app/api/v1/pipeline.py` (`/batch-urls`, `/download-proxy`)
- API 客户端：`frontend/src/features/pipeline/api.ts`

## Firestore 结构与规则

### 集合与字段

#### `pipeline_jobs/{job_id}`（主文档）
**职责**：宏观统计，避免写冲突和文档大小限制

**字段**：
- `drama_name`, `gdrive_path`, `include_folders[]`
- `status` ∈ {QUEUED, TRANSFERRING, PROCESSING, COMPLETE, FAILED, FAILED_STAGE2, CANCELLED, PAUSED}
- `stage` ∈ {1, 2}
- `transfer_stats`（`episodes_total`, `episodes_done`, `subs_total`, `subs_done`, `speed`, `eta`）
- **`processed_files`**：成功处理的文件数（使用 `firestore.Increment` 原子更新）
- **`failed_files`**：失败的文件数（使用 `firestore.Increment` 原子更新）
- **`total_files`**：总文件数（在任务创建时设置）
- `progress`（百分比文字/计数，可选，用于显示）
- `created_by`（email/userId）, `created_at`, `updated_at`
- `cancelled_at`, `cancelled_by`, `paused_at`, `paused_by`, `resumed_at`, `resumed_by`
- `oauth_refresh_token_ref`（引用或密文）
- **注意**：主文档**不存储**具体文件列表，避免文档 1MB 限制和写冲突（Hotspotting）

#### `pipeline_jobs/{job_id}/tasks/{task_index}`（Task 状态子集合）⭐ **新增核心**
**职责**：每个 Cloud Run Task 的详细状态，实现细粒度进度追踪

**文档 ID**：`str(task_index)`（如 "0", "1", "2"）

**字段结构**：
```json
{
  "task_index": 0,                    // Task 索引（0-based）
  "status": "RUNNING",                // RUNNING | COMPLETED | FAILED
  "current_file": "US01/ep01.mp4",    // 当前正在处理的文件（实时更新）
  "success_files": [                  // 已成功处理的文件列表
    "US01/ep01.mp4",
    "US01/ep02.mp4"
  ],
  "failed_files": [                   // 失败文件详情列表
    {
      "path": "US01/ep03.mp4",
      "error": "FFmpeg timeout"
    }
  ],
  "progress_count": 5,                // 该 Task 已处理数量（成功+失败）
  "total_count": 10,                  // 该 Task 分配到的总文件数
  "created_at": SERVER_TIMESTAMP,
  "updated_at": SERVER_TIMESTAMP
}
```

**更新策略**：
- **初始化**：Task 启动时创建文档，设置 `status="RUNNING"`, `total_count=len(my_episodes)`
- **处理前**：更新 `current_file` 为当前文件名
- **成功后**：使用 `firestore.ArrayUnion([文件名])` 添加到 `success_files`，`firestore.Increment(1)` 更新 `progress_count`
- **失败后**：使用 `firestore.ArrayUnion([{path, error}])` 添加到 `failed_files`，`firestore.Increment(1)` 更新 `progress_count`
- **完成时**：设置 `status="COMPLETED"`, `current_file=null`

**并发控制**：
- 每个 Task 只更新自己的文档（`task_index` 唯一），避免写冲突
- 主文档使用原子操作（`Increment`），避免并发更新冲突

#### `processing_failures/{failure_id}`（全局失败索引）
**职责**：记录所有失败的详细信息，用于重试和审计

**字段**：
- `job_id`, `drama_name`, `language`, `episode`
- `video_gcs_path`, `subtitle_gcs_path`
- `error_message`（完整错误堆栈）
- `status`（FAILED | RESOLVED）
- `created_at`, `updated_at`

#### `nas_download_tasks/{id}`
- `drama_name`, `files[]`, `priority`, `status`, `requested_by`, `notes`

### 安全规则（Native 严格）
- 仅允许白名单用户读取 `pipeline_jobs`（或按 `created_by` 过滤）。
- Workers（运行时 SA）具备读写权限。
- 不在 Firestore 存储任何明文敏感 OAuth 客户端密钥；如需，放入 Secret Manager。

## 基础设施与 CI/CD

### Cloud Run Jobs
- `gdrive-transfer-worker`（Worker 1）：
  - 部署参数：
    - `--cpu=4 --memory=16Gi --max-retries=1 --timeout=3h`
    - `--set-env-vars "GCS_SOURCE_BUCKET=vigloo_source,GCS_PROCESSED_BUCKET=vigloo_processed"`
    - 绑定运行时服务账号：`sa-run-prod@...`（或 dev 环境 `sa-dev@...`）

- `drama-processor-job`（Worker 2，Sharding 模式）：
  - **部署参数**（单 Task 规格）：
    - `--cpu=2 --memory=4Gi --task-timeout=2h --max-retries=1`
    - `--set-env-vars "GCS_SOURCE_BUCKET=vigloo_source,GCS_PROCESSED_BUCKET=vigloo_processed"`
    - 绑定运行时服务账号：`sa-run-prod@...`
  - **并发控制**：
    - `task_count` 在触发 Job 时动态设置（见 `pipeline_process_service.py`）
    - 公式：`task_count = ceil(total_episodes / 5)` 或 `task_count = total_episodes`（1:1 映射）
    - 示例：540 个视频 → `task_count=540`（每个 Task 处理 1 个视频）
  - **环境变量**（由 Cloud Run 自动注入）：
    - `CLOUD_RUN_TASK_INDEX`：当前 Task 索引（0-based）
    - `CLOUD_RUN_TASK_COUNT`：总 Task 数量

### Eventarc 触发器
- 事件类型：`google.cloud.storage.object.v1.finalized`
- 桶：`vigloo_source`
- 过滤：对象名后缀 `_PROCESS_NOW.txt`
- 目标：`drama-processor-job`（Cloud Run Job）

### GitHub Actions（示意）
- 在现有 `.github/workflows/backend-deploy.yaml` 中新增步骤：
  - Build & push `workers/transfer` 与 `workers/process` 镜像。
  - `gcloud run jobs deploy gdrive-transfer-worker ...`
  - `gcloud run jobs deploy drama-processor-job ...`
  - 检查/创建 `vigloo_processed` bucket。
  - `gcloud eventarc triggers create/update` 设置触发器（幂等）。
  - 确保启用 API：`eventarc.googleapis.com`, `run.googleapis.com`, `artifactregistry.googleapis.com`, `pubsub.googleapis.com`, `firestore.googleapis.com`, `iam.googleapis.com`, `serviceusage.googleapis.com`。

## 安全与权限
- 后端 Cloud Run 运行时 SA：
  - `roles/datastore.user`（Firestore）
  - `roles/storage.admin`（或更细权限，用于生成签名 URL/列对象）
  - `roles/run.admin`（如需触发 Run Jobs，可替换为 `roles/run.invoker` + 使用 `projects.locations.jobs.run` 权限）
- Eventarc/触发需要的 Service Agent 权限自动化在 CI 启用时完成。
- Drive 访问范围：`drive.readonly`；refresh token 加密存储，Job 运行时解密使用。

## 迁移与配置清单
1. 创建或确认 GCS 桶：`vigloo_source`（已存在）、`vigloo_processed`（自动化创建）。
2. Firestore：启用标准版（native, us-central1），严格规则，并确认客户端在同区域。
3. OAuth：
   - 准备 Google OAuth Client（Web 应用），配置回调 URI（前端/后端），scope 包含 `drive.readonly`。
   - 实现一次授权流程以获取 refresh token。
4. 环境变量：
   - `FRONTEND_ORIGINS`
   - `GCS_SOURCE_BUCKET=vigloo_source`
   - `GCS_PROCESSED_BUCKET=vigloo_processed`
   - `GOOGLE_OAUTH_CLIENT_ID/SECRET`（推荐放 Secret Manager）
5. 字体与 ffmpeg：
   - 镜像安装 `Noto Sans CJK` 字体；确认 ffmpeg 能找到字体路径（必要时通过 `-vf subtitles=...,fontsdir=/usr/share/fonts`）。

## 开放问题（与需求对齐的 TBD）
- OAuth refresh token 托管位置：Secret Manager（按用户分 Secret） vs Firestore（加密字段）。
- 前端是否在登录后强制触发一次 Drive 授权流程（最简实现是首次访问 `/pipeline` 时引导）。
- rclone 限速/重试策略：根据带宽及配额调整 `--bwlimit`、`--retries`、`--low-level-retries`。
- Firestore 监听范围优化：是否按 `created_by` 或最近 7 天过滤以降低费用。

## 成功度量（与需求一致）
- `/pipeline` 打开到展示 GDrive 状态 < 3s（懒加载/分页）。
- 传输任务请求返回 < 1s；Job 更新进度延迟 < 1s（onSnapshot）。
- Job 失败可定位（日志 + Firestore 错误字段）。

---

本设计文档覆盖前端 UI/交互、后端 API、Workers、Eventarc、CI/CD、安全权限与迁移清单，满足已批准的需求范围。提交审批后，进入 Tasks 分解阶段。 

