# 如何触发新的压制任务

## 方式 1: 手动触发（推荐）

### 通过 API 端点

**端点**: `POST /api/v1/pipeline/process-manual`

**请求体**:
```json
{
  "drama_name": "US009P03S01_Good Girl Gone Bad",
  "file_paths": []
}
```

**说明**:
- `drama_name`: 剧集名称（必须与 GCS 中的文件夹名称一致）
- `file_paths`: 文件路径列表（可选，空数组表示处理所有文件）

### 使用脚本

```bash
# 设置认证 token
export API_TOKEN='your_token_here'

# 触发任务
./backend/scripts/trigger_manual_process.sh "US009P03S01_Good Girl Gone Bad"
```

### 使用 Python

```python
from app.services.pipeline_process_service import PipelineProcessService
from app.schemas.auth import AuthenticatedUser

# 创建服务实例
service = PipelineProcessService()

# 触发任务（需要认证用户）
job_id = service.trigger_manual_process_job(
    drama_name="US009P03S01_Good Girl Gone Bad",
    file_paths=[],  # 空列表表示处理所有文件
    current_user=authenticated_user
)

print(f"任务已创建: {job_id}")
```

## 方式 2: 自动触发（传输完成后）

### 流程

1. **传输任务完成** → 在 GCS 中创建 `_PROCESS_NOW.txt` 信号文件
2. **Eventarc 触发** → 检测到信号文件创建事件
3. **Relay Service 处理** → 查找最新的 ready job 并触发压制任务

### 前提条件

- 传输任务必须完成（`status=COMPLETE`）
- GCS 中必须存在 `{drama_name}/_PROCESS_NOW.txt` 文件
- Eventarc 触发器必须正确配置

### 检查自动触发状态

```bash
# 检查信号文件
gsutil ls gs://vigloo_source/{drama_name}/_PROCESS_NOW.txt

# 检查 Eventarc 触发器
gcloud eventarc triggers list --location=asia-northeast3

# 检查 Relay Service 日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=drama-processor-relay-service" --limit=50
```

## 方式 3: 重试失败的文件

### 通过 API 端点

**端点**: `POST /api/v1/pipeline/retry-process/{failure_id}`

**说明**:
- `failure_id`: 失败记录的 ID（从 `processing_failures` 集合中获取）

### 使用脚本

```python
from app.services.pipeline_process_service import PipelineProcessService
from app.schemas.auth import AuthenticatedUser

service = PipelineProcessService()
job_id = service.enqueue_retry_job(
    failure_id="failure_id_here",
    current_user=authenticated_user
)
```

## 队列状态检查

### 检查并发控制队列

```python
from app.core.firestore import get_firestore_client

firestore_client = get_firestore_client()
control_ref = firestore_client.collection('system_config').document('concurrency_control')
snapshot = control_ref.get()

if snapshot.exists:
    data = snapshot.to_dict() or {}
    print(f"运行中的任务: {data.get('running_job_ids')}")
    print(f"队列中的任务: {data.get('queue')}")
```

### 使用诊断脚本

```bash
# 检查特定任务
python backend/scripts/diagnose_blocked_job.py <job_id>

# 检查所有阻塞的任务
python backend/scripts/diagnose_blocked_job.py
```

## 常见问题

### Q: 任务创建后一直处于 QUEUED 状态？

**A**: 检查以下几点：
1. 并发控制队列是否已满（当前最大并发数: 1）
2. 是否有僵尸任务占用 slot
3. 运行清理脚本：`python -c "from app.services.concurrency_service import ConcurrencyService; ConcurrencyService()._cleanup_completed_jobs()"`

### Q: 任务执行失败，提示"未找到文件对"？

**A**: 检查以下几点：
1. GCS 中是否存在视频文件（`episodes/final/` 目录）
2. GCS 中是否存在字幕文件（`subtitles/final/` 目录）
3. 文件名格式是否正确（包含 episode 号）
4. 运行文件配对检查：`python -c "from app.services.pipeline_discovery_service import discover_file_pairs; pairs = discover_file_pairs('drama_name'); print(f'找到 {len(pairs)} 个文件对')"`

### Q: 如何查看任务执行进度？

**A**: 
1. 检查 Firestore: `pipeline_jobs/{job_id}`
2. 检查 Cloud Run Job 执行: `gcloud run jobs executions list --job=drama-processor-job`
3. 检查 Worker 日志: `gcloud logging read "resource.type=cloud_run_job" --limit=100`

## 最佳实践

1. **手动触发前检查**:
   - 确认 GCS 中有文件
   - 确认文件配对正常
   - 检查队列状态

2. **监控任务执行**:
   - 使用诊断脚本定期检查
   - 监控 Cloud Run Job 执行状态
   - 检查 Worker 日志

3. **处理失败任务**:
   - 查看失败原因
   - 修复问题后重试
   - 使用重试 API 而不是创建新任务


