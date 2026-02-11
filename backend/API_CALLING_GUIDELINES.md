# API 调用指南

## Cloud Run Jobs API 调用规范

### ✅ 正确方式：使用官方客户端库

**必须使用**: `google.cloud.run_v2.JobsClient()`

**示例代码**:
```python
from google.cloud import run_v2

# 初始化客户端
jobs_client = run_v2.JobsClient()

# 构建请求
env_vars = [
    run_v2.EnvVar(name="JOB_ID", value=job_id),
    run_v2.EnvVar(name="DRAMA_NAME", value=drama_name),
]

overrides = run_v2.RunJobRequest.Overrides(
    container_overrides=[
        run_v2.RunJobRequest.Overrides.ContainerOverride(env=env_vars),
    ],
    task_count=task_count,  # 可选
)

request = run_v2.RunJobRequest(
    name=job_name,  # 完整路径: projects/{project}/locations/{region}/jobs/{job_name}
    overrides=overrides,
)

# 调用 API
operation = jobs_client.run_job(request=request)
```

### ❌ 错误方式：使用 REST API

**禁止使用**: 直接调用 REST API

**错误示例**:
```python
# ❌ 不要这样做
import google.auth
from google.auth.transport.requests import AuthorizedSession

RUN_API_BASE = "https://run.googleapis.com/v1"
session = AuthorizedSession(...)
url = f"{RUN_API_BASE}/{job_name}:run"
response = session.post(url, json=payload)
```

**为什么禁止**:
- REST API 端点格式可能不正确
- 需要手动处理认证和错误
- 官方推荐使用客户端库
- 客户端库提供更好的类型安全和错误处理

## 其他 GCP API 调用规范

### Firestore API

**必须使用**: `google.cloud.firestore.Client()`

```python
from google.cloud import firestore

client = firestore.Client()
collection = client.collection("pipeline_jobs")
```

### Cloud Storage API

**必须使用**: `google.cloud.storage.Client()`

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("vigloo_source")
blob = bucket.blob("path/to/file")
```

### Cloud Run Services API

**必须使用**: `google.cloud.run_v2.ServicesClient()`

```python
from google.cloud import run_v2

services_client = run_v2.ServicesClient()
request = run_v2.GetServiceRequest(name=service_name)
service = services_client.get_service(request=request)
```

## 代码审查检查清单

### API 调用检查

- [ ] 是否使用官方客户端库？
- [ ] 是否禁止使用 REST API？
- [ ] API 调用格式是否正确？
- [ ] 错误处理是否完善？

### 跨文件对比检查

- [ ] 是否有其他文件实现了相同功能？
- [ ] 实现方式是否一致？
- [ ] 是否使用相同的 API 客户端？

## 常见错误和解决方案

### 错误 1: 使用 REST API 导致 404

**错误**:
```
Cloud Run Jobs API 调用失败：status=404
```

**原因**: 使用 REST API，端点格式不正确

**解决方案**: 使用 `run_v2.JobsClient()`

### 错误 2: Job 名称格式不正确

**错误**:
```
Invalid argument: job name format incorrect
```

**原因**: Job 名称应该是完整路径

**解决方案**: 使用完整路径 `projects/{project}/locations/{region}/jobs/{job_name}`

### 错误 3: 认证失败

**错误**:
```
Permission denied: insufficient permissions
```

**原因**: 服务账号缺少必要权限

**解决方案**: 确保服务账号有 `roles/run.invoker` 权限

## 参考实现

### 正确实现示例

**文件**: `backend/app/services/pipeline_process_service.py`

```python
from google.cloud import run_v2

class PipelineProcessService:
    def __init__(self):
        self._jobs_client = run_v2.JobsClient()
        self._process_job_name = settings.process_job_name.strip()
    
    def _trigger_process_worker(self, job_id: str, total_files: int | None = None):
        env_vars = [
            run_v2.EnvVar(name="JOB_ID", value=job_id),
        ]
        
        overrides = run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(env=env_vars),
            ],
        )
        
        request = run_v2.RunJobRequest(
            name=self._process_job_name,
            overrides=overrides,
        )
        
        operation = self._jobs_client.run_job(request=request)
```

## 最佳实践

1. **统一使用客户端库**
   - 所有 GCP API 调用都使用官方客户端库
   - 禁止直接使用 REST API

2. **错误处理**
   - 捕获异常并记录详细错误信息
   - 提供有意义的错误消息

3. **类型安全**
   - 使用类型提示
   - 利用客户端库的类型检查

4. **代码复用**
   - 参考其他服务的实现
   - 保持实现方式一致

5. **测试**
   - 单元测试 API 调用逻辑
   - 集成测试端到端流程

## 相关文档

- [Google Cloud Run Jobs API](https://cloud.google.com/run/docs/reference/rest/v2/projects.locations.jobs/run)
- [Python Client Library](https://cloud.google.com/python/docs/reference/run/latest)
- [API Calling Guidelines](./API_CALLING_GUIDELINES.md)
- [Development Checklist](./DEVELOPMENT_CHECKLIST.md)


