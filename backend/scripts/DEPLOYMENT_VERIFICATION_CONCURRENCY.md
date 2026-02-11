# 并发控制功能部署验证指南

## 部署状态

代码已推送到 `main` 分支，CI/CD 应该正在运行。

## 验证步骤

### 1. 检查 GitHub Actions 部署状态

```bash
# 查看最近的 GitHub Actions 运行状态
gh run list --workflow=backend-deploy.yaml --limit 5

# 或者访问 GitHub 网页查看
# https://github.com/lijiannan828-oss/AutoGrowth/actions
```

### 2. 验证部署的服务

```bash
# 检查 Cloud Run Service 是否更新
gcloud run services describe drama-processor-relay-service \
  --region=asia-northeast3 \
  --format="value(status.url)"

# 检查 Cloud Run Job 配置
gcloud run jobs describe drama-processor-job \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

### 3. 验证并发控制配置

```bash
# 检查环境变量 MAX_CONCURRENT_JOBS
gcloud run services describe drama-processor-relay-service \
  --region=asia-northeast3 \
  --format="value(spec.template.spec.containers[0].env)" | grep MAX_CONCURRENT_JOBS
```

### 4. 验证 Firestore 并发控制文档

```bash
# 检查并发控制文档是否存在
python backend/scripts/check_concurrency_control.py
```

### 5. 端到端测试场景

#### 场景 1: 并发控制测试

1. **准备两个剧集的传输任务**
   - 剧集 A: 已完成传输，等待处理
   - 剧集 B: 已完成传输，等待处理

2. **同时触发两个处理任务**
   - 方式 1: 通过前端手动触发两个剧集的"开始压制"
   - 方式 2: 通过 API 同时触发两个处理任务

3. **验证结果**
   - ✅ 第一个任务应该立即开始（获取 slot）
   - ✅ 第二个任务应该被排队（status: QUEUED）
   - ✅ Firestore `system_config/concurrency_control` 文档中：
     - `running_jobs: 1`
     - `running_job_ids: [job_a_id]`
     - `queue: [job_b_id]`

#### 场景 2: 队列自动触发测试

1. **准备状态**
   - Job A 正在运行
   - Job B 在队列中等待

2. **等待 Job A 完成**
   - 监控 Job A 的处理进度
   - 等待 Job A 状态变为 SUCCEEDED 或 FAILED

3. **验证结果**
   - ✅ Job A 完成后，Job B 应该自动开始
   - ✅ Firestore 并发控制文档中：
     - `running_jobs: 1`
     - `running_job_ids: [job_b_id]`
     - `queue: []`
   - ✅ Job B 的 Cloud Run Job 应该被自动触发

#### 场景 3: FIFO 顺序测试

1. **准备状态**
   - Job A 正在运行
   - Job B 在队列中（位置 1）
   - Job C 在队列中（位置 2）

2. **等待 Job A 完成**

3. **验证结果**
   - ✅ Job B 应该先被触发（FIFO）
   - ✅ Job C 应该仍在队列中
   - ✅ Job B 完成后，Job C 应该被触发

#### 场景 4: 超时清理测试（可选）

1. **创建一个 Zombie Job**
   - 手动将某个 job 的 `updated_at` 设置为 4 小时前
   - 将该 job 添加到 `running_job_ids`

2. **触发新的处理任务**

3. **验证结果**
   - ✅ Zombie Job 应该被清理
   - ✅ 新任务应该能够获取 slot

## 监控命令

### 检查并发控制状态

```bash
# 查看并发控制文档
python backend/scripts/check_concurrency_control.py

# 或者直接查询 Firestore
gcloud firestore documents get \
  system_config/concurrency_control \
  --database="(default)"
```

### 检查队列中的任务

```bash
# 查看所有 QUEUED 状态的任务
python backend/scripts/check_queued_jobs.py
```

### 检查运行中的任务

```bash
# 查看所有 PROCESSING 状态的任务
python backend/scripts/check_running_jobs.py
```

## 日志检查

### Relay Service 日志

```bash
# 查看 Relay Service 日志
gcloud logging read \
  "resource.type=cloud_run_revision AND \
   resource.labels.service_name=drama-processor-relay-service" \
  --limit=50 \
  --format=json \
  --region=asia-northeast3
```

### Worker 日志

```bash
# 查看 Worker 日志（处理任务）
gcloud logging read \
  "resource.type=cloud_run_job AND \
   resource.labels.job_name=drama-processor-job" \
  --limit=50 \
  --format=json \
  --region=us-central1
```

## 预期行为

### ✅ 正常行为

1. **并发控制**:
   - 最多同时运行 `MAX_CONCURRENT_JOBS` 个任务（默认 1）
   - 超出限制的任务会被排队

2. **队列自动触发**:
   - 任务完成时，队列中的第一个任务自动开始
   - FIFO 顺序得到保证

3. **超时清理**:
   - 超过 3.5 小时未更新的任务会被清理
   - 释放的 slot 可以被新任务使用

### ❌ 异常行为（需要关注）

1. **任务永远排队**:
   - 如果任务一直在队列中，可能是自动触发机制失效
   - 检查 Worker 日志，确认是否调用了 `release_and_trigger_next()`

2. **任务插队**:
   - 如果新任务插队，可能是事务失效
   - 检查 Firestore 事务日志

3. **Zombie Lock**:
   - 如果 slot 一直被占用但没有任务运行，可能是清理机制失效
   - 检查超时清理逻辑

## 回滚方案

如果部署后出现问题，可以：

1. **快速回滚**:
   ```bash
   # 回滚到上一个版本
   git revert HEAD
   git push origin main
   ```

2. **禁用并发控制**:
   - 设置 `MAX_CONCURRENT_JOBS=100`（临时提高限制）
   - 或者注释掉并发控制逻辑

3. **手动清理队列**:
   ```bash
   # 清空队列
   python backend/scripts/clear_queue.py
   ```

## 联系信息

如果遇到问题，请提供：
1. 具体的错误信息
2. 相关的日志
3. Firestore 并发控制文档的状态
4. 受影响的任务 ID


