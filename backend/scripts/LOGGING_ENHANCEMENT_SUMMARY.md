# Relay Service 日志增强总结

## 改进目标

增强 Relay Service 和 ConcurrencyService 的日志记录，确保所有关键步骤都有详细的日志输出，便于排查问题。

## 改进内容

### 1. Relay Service (`backend/app/api/v1/relay.py`)

#### 改进点：

1. **添加请求 ID 追踪**
   - 每个请求生成唯一的 `request_id`（UUID 前 8 位）
   - 所有日志都包含 `request_id`，便于追踪单个请求的处理流程

2. **双重日志输出**
   - **结构化日志**：使用 `logger.info()` 和 `extra` 参数，输出结构化 JSON 日志
   - **stdout 日志**：使用 `print()` 输出到 stdout，确保 Cloud Run 能捕获所有日志

3. **关键步骤日志**
   - ✅ Eventarc 事件接收
   - ✅ 信号文件验证
   - ✅ drama_name 提取
   - ✅ 查询 ready job
   - ✅ Job slot 获取
   - ✅ 并发控制结果
   - ✅ Cloud Run Job 触发
   - ✅ 错误处理和 slot 释放

4. **日志格式统一**
   - 使用 `[RELAY-{request_id}]` 前缀
   - 使用 emoji 标识不同状态（📬、🎯、⏳、✅、❌等）
   - 包含关键信息：job_id、drama_name、operation 等

#### 示例日志输出：

```
[RELAY-a1b2c3d4] 📬 Eventarc event received: type=google.cloud.storage.object.v1.finalized, bucket=vigloo_source, name=US032P03S01_Contracted Hearts/_PROCESS_NOW.txt
[RELAY-a1b2c3d4] 📝 Extracted drama_name: US032P03S01_Contracted Hearts
[RELAY-a1b2c3d4] 🔍 Searching for ready job: drama=US032P03S01_Contracted Hearts
[RELAY-a1b2c3d4] 🎯 Found ready job: job_id=fnfOqA3U32u0o8JUG1qh, drama=US032P03S01_Contracted Hearts
[RELAY-a1b2c3d4] 🔐 Acquiring job slot: job_id=fnfOqA3U32u0o8JUG1qh
[RELAY-a1b2c3d4] 🔐 Slot acquisition result: can_start=True, message=Job slot acquired (running=1/1)
[RELAY-a1b2c3d4] 🚀 Triggering Cloud Run Job: job_id=fnfOqA3U32u0o8JUG1qh, env=production
[RELAY-a1b2c3d4] ✅ Cloud Run Job triggered: job_id=fnfOqA3U32u0o8JUG1qh, operation=operations/abc123
[RELAY-a1b2c3d4] ✅ Request completed: status=triggered
```

### 2. ConcurrencyService (`backend/app/services/concurrency_service.py`)

#### 改进点：

1. **并发控制状态日志**
   - 记录清理完成的任务数量
   - 记录当前运行任务数和队列大小
   - 记录 slot 获取和释放的详细过程

2. **队列自动触发日志**
   - 记录 `try_trigger_next_job` 的完整流程
   - 记录队列状态变化（FIFO 顺序）
   - 记录 Cloud Run Job 触发结果

3. **错误处理日志**
   - 记录所有异常和错误类型
   - 记录失败重试逻辑

#### 示例日志输出：

```
[CONCURRENCY] 🔐 Starting acquire_job_slot: job_id=fnfOqA3U32u0o8JUG1qh, max_concurrent=1
[CONCURRENCY] 📊 Current state: running=0/1, queue_size=0, running_job_ids=[], queue=[]
[CONCURRENCY] ✅ Job slot acquired: job_id=fnfOqA3U32u0o8JUG1qh, Job slot acquired (running=1/1)
[CONCURRENCY] ✅ Acquire transaction completed: job_id=fnfOqA3U32u0o8JUG1qh, can_start=True, message=Job slot acquired (running=1/1)
```

## 日志查询方法

### 1. 查询 Relay Service 日志

```bash
# 查询特定请求的日志
gcloud logging read \
  "resource.type=cloud_run_revision \
   AND resource.labels.service_name=drama-processor-relay-service \
   AND textPayload=~\"RELAY-a1b2c3d4\"" \
  --limit=100 \
  --format=json

# 查询所有 Relay Service 日志
gcloud logging read \
  "resource.type=cloud_run_revision \
   AND resource.labels.service_name=drama-processor-relay-service \
   AND textPayload=~\"RELAY-\"" \
  --limit=100 \
  --format=json
```

### 2. 查询 ConcurrencyService 日志

```bash
# 查询并发控制相关日志
gcloud logging read \
  "resource.type=cloud_run_revision \
   AND resource.labels.service_name=drama-processor-relay-service \
   AND textPayload=~\"CONCURRENCY\"" \
  --limit=100 \
  --format=json
```

### 3. 查询结构化日志（JSON）

```bash
# 查询结构化日志
gcloud logging read \
  "resource.type=cloud_run_revision \
   AND resource.labels.service_name=drama-processor-relay-service \
   AND jsonPayload.request_id=\"a1b2c3d4\"" \
  --limit=100 \
  --format=json
```

## 预期效果

1. **完整的请求追踪**
   - 每个 Eventarc 事件都有唯一的 `request_id`
   - 可以通过 `request_id` 追踪整个处理流程

2. **详细的处理步骤**
   - 所有关键步骤都有日志记录
   - 可以清楚地看到每个步骤的执行情况

3. **问题排查能力**
   - 如果处理失败，可以快速定位失败原因
   - 如果任务被排队，可以清楚地看到排队原因和位置

4. **性能监控**
   - 可以分析每个步骤的耗时
   - 可以监控并发控制的效果

## 下一步

1. **部署代码**：将增强的日志记录部署到生产环境
2. **验证日志**：触发一个传输任务，验证日志是否正确输出
3. **监控分析**：使用日志分析工具（如 GCP Logging）分析日志

## 注意事项

1. **日志量增加**：由于增加了详细的日志记录，日志量会显著增加
2. **性能影响**：日志输出对性能的影响应该很小，但需要监控
3. **日志存储成本**：GCP Logging 的存储成本可能会增加，需要关注


