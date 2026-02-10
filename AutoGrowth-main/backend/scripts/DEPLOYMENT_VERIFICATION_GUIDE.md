# 部署验证指南：中继服务和文件配对修复

## 部署信息

### ✅ 代码已推送
- **Commit**: `028b014`
- **Branch**: `main`
- **Push Time**: 刚刚
- **GitHub URL**: https://github.com/lijiannan828-oss/AutoGrowth/commit/028b014
- **GitHub Actions URL**: https://github.com/lijiannan828-oss/AutoGrowth/actions

## 本次部署的修复

### 1. ✅ 视频格式扩展
- **问题**: 只支持 `.mp4`，无法识别 `.mov` 等格式
- **修复**: 扩展支持 30+ 种主流视频格式
- **影响**: 文件配对现在可以识别 `.mov`, `.avi`, `.mkv` 等格式

### 2. ✅ Eventarc 触发器修复（已在生产环境应用）
- **问题**: 路径配置错误（`/` 而不是 `/api/relay/event`）
- **修复**: 触发器已重新创建，路径正确
- **状态**: ✅ 已完成（无需代码部署）

## 部署后验证步骤

### Step 1: 检查 GitHub Actions 部署状态

访问：https://github.com/lijiannan828-oss/AutoGrowth/actions

**验证点**：
- ✅ 工作流运行成功（绿色 ✓）
- ✅ 所有部署步骤完成
- ✅ 健康检查通过

### Step 2: 验证视频格式识别（生产环境）

#### 2.1 使用诊断脚本测试

```bash
cd /Users/mac/AutoGrowth
python3 backend/scripts/test_file_pairing_with_mov.py
```

**预期结果**：
- ✅ 找到文件对（之前是 0 个）
- ✅ `.mov` 文件被正确识别
- ✅ 配对逻辑正常工作

#### 2.2 检查实际传输任务

使用传输任务 `f7DTMToHvkNLqBe4Bl97` 或创建新任务：

```bash
# 检查文件配对
python3 backend/scripts/diagnose_auto_trigger.py
```

**验证点**：
- ✅ "File Pairing Accuracy" 部分显示找到文件对
- ✅ 视频格式统计包含 `.mov`

### Step 3: 验证 Relay Service（生产环境）

#### 3.1 检查 Relay Service 日志

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=drama-processor-relay-service" \
  --limit=20 \
  --format="table(timestamp,textPayload)" \
  --project=fleet-blend-469520-n7
```

**预期日志**：
- ✅ `📬 接收到 Eventarc 事件` - 事件接收正常
- ✅ `⏭️  非目标对象，直接忽略` - 路径过滤正常
- ✅ `🎯 匹配到 pipeline job` - Job 查找正常
- ✅ `✅ 已触发 Cloud Run Job` - Job 触发成功

#### 3.2 测试 Relay Service 端点（可选）

```bash
# 使用测试脚本（需要修改为生产环境 URL）
python3 backend/scripts/test_relay_service.py
```

**注意**: 需要修改脚本中的 `RELAY_SERVICE_URL` 为生产环境地址。

### Step 4: 端到端测试（推荐）

#### 4.1 创建新的传输任务

1. 通过前端或 API 创建一个新的传输任务
2. 等待传输完成
3. 观察是否自动触发压制任务

#### 4.2 验证自动触发流程

**检查点**：
1. ✅ 传输任务完成 → 创建 `_PROCESS_NOW.txt`
2. ✅ Eventarc 捕获事件
3. ✅ Relay Service 接收请求（路径：`/api/relay/event`）
4. ✅ Relay Service 找到 ready job
5. ✅ 触发 Cloud Run Job（Sharding 架构）
6. ✅ 文件配对成功（找到视频/字幕对）

#### 4.3 验证文件配对

```bash
# 检查 Firestore 中的 process job
# 查看 total_files 是否正确设置
gcloud firestore documents get pipeline_jobs/<JOB_ID> \
  --project=fleet-blend-469520-n7
```

**验证点**：
- ✅ `total_files` 字段正确设置（之前可能是 0）
- ✅ `processed_files` 和 `failed_files` 正确更新
- ✅ Task 文档正确创建

### Step 5: 验证 Sharding 执行

#### 5.1 检查 Cloud Run Jobs Execution

```bash
gcloud run jobs executions list \
  --job=drama-processor-job \
  --region=us-central1 \
  --project=fleet-blend-469520-n7 \
  --limit=5
```

**验证点**：
- ✅ Execution 状态：RUNNING 或 SUCCEEDED
- ✅ Task 数量：符合预期（基于 `task_count` 计算）

#### 5.2 检查 Task 文档

```bash
# 使用诊断脚本
python3 backend/scripts/diagnose_auto_trigger.py
```

**验证点**：
- ✅ Task 文档正确创建（`pipeline_jobs/{job_id}/tasks/{task_index}`）
- ✅ 每个 Task 处理不同的文件
- ✅ 进度正确更新

## 关键监控点

### Cloud Run Jobs 控制台
```
https://console.cloud.google.com/run/jobs/us-central1/drama-processor-job/executions
```

**观察**:
- ✅ Execution 状态
- ✅ Task 数量和分布
- ✅ 执行时间
- ✅ 错误日志

### Firestore 控制台
```
https://console.cloud.google.com/firestore/databases/-default-/data/~2Fpipeline_jobs
```

**观察**:
- ✅ 主文档 `total_files` 正确设置（之前可能是 0）
- ✅ `processed_files` 和 `failed_files` 正确更新
- ✅ Task 文档正确创建和更新
- ✅ 最终状态为 `SUCCEEDED`

### Cloud Logging
```
https://console.cloud.google.com/logs/query
```

**查询示例**:
```
resource.type="cloud_run_revision"
resource.labels.service_name="drama-processor-relay-service"
severity>=INFO
```

**关注**:
- ✅ Relay Service 接收事件
- ✅ 路径过滤逻辑（忽略非 `_PROCESS_NOW.txt` 文件）
- ✅ Job 查找和触发成功

## 验证清单

### ✅ 部署验证
- [ ] GitHub Actions 部署成功
- [ ] 所有服务正常启动
- [ ] 健康检查通过

### ✅ 视频格式验证
- [ ] `.mov` 文件被正确识别
- [ ] 文件配对返回正确数量的文件对（之前是 0）
- [ ] 其他视频格式（`.avi`, `.mkv` 等）也能识别

### ✅ Relay Service 验证
- [ ] 端点路径正确（`/api/relay/event`）
- [ ] 正确接收 Eventarc 事件
- [ ] 路径过滤逻辑正常（忽略非目标文件）
- [ ] 成功找到 ready job
- [ ] 成功触发 Cloud Run Job

### ✅ 端到端验证
- [ ] 传输任务完成 → 自动触发压制任务
- [ ] 文件配对成功（`total_files` 正确）
- [ ] Sharding 架构正常工作
- [ ] Task 文档正确创建和更新
- [ ] 压制任务成功完成

## 故障排查

### 问题 1: 文件配对仍返回 0 个文件对

**可能原因**:
- 部署未完成
- 视频格式识别逻辑未更新

**排查步骤**:
1. 确认代码已部署（检查 GitHub Actions）
2. 运行 `test_file_pairing_with_mov.py` 验证
3. 检查 GCS 文件结构

### 问题 2: Relay Service 仍返回 404

**可能原因**:
- Eventarc 触发器路径未更新
- Relay Service 路由配置错误

**排查步骤**:
1. 检查 Eventarc 触发器配置：
   ```bash
   gcloud eventarc triggers describe drama-processor-trigger \
     --location=asia-northeast3 \
     --project=fleet-blend-469520-n7 \
     --format="yaml(destination.cloudRun.path)"
   ```
2. 检查 Relay Service 路由配置
3. 查看 Relay Service 日志

### 问题 3: 自动触发未工作

**可能原因**:
- Eventarc 触发器未激活
- Relay Service 未找到 ready job
- 信号文件路径不正确

**排查步骤**:
1. 检查 Eventarc 触发器状态
2. 检查 Relay Service 日志
3. 验证信号文件是否存在
4. 检查 Firestore job 状态

## 成功标准

✅ **所有以下条件必须满足**：

1. ✅ GitHub Actions 部署成功
2. ✅ 视频格式识别正常（`.mov` 等格式）
3. ✅ 文件配对成功（找到文件对，`total_files` > 0）
4. ✅ Relay Service 正确接收事件（路径：`/api/relay/event`）
5. ✅ 自动触发流程正常（传输完成 → 压制任务触发）
6. ✅ Sharding 架构正常工作（Task 文档创建，进度更新）

---

**部署时间**: [待填写]
**验证时间**: [待填写]
**验证状态**: [待填写]

