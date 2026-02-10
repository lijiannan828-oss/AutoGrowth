# Eventarc 触发器更新指南

## 背景

修复了 Eventarc 触发器配置，使其通过 relay 服务传递 JOB_ID，而不是直接触发 Job。

## 部署步骤

### 1. 等待 CI/CD 完成

确保以下服务已成功部署：
- ✅ `drama-processor-relay-service` (Relay 服务)
- ✅ `drama-processor-job` (Process Job)

### 2. 更新 Eventarc 触发器

**重要：** 如果触发器已存在，需要先删除再重新创建。

#### 步骤 2.1: 检查现有触发器

```bash
gcloud beta eventarc triggers describe drama-processor-trigger \
  --location=us-central1 \
  --project=fleet-blend-469520-n7
```

#### 步骤 2.2: 删除旧触发器（如果存在）

```bash
gcloud beta eventarc triggers delete drama-processor-trigger \
  --location=us-central1 \
  --project=fleet-blend-469520-n7
```

#### 步骤 2.3: 创建新触发器

```bash
cd infra
PROJECT_ID=fleet-blend-469520-n7 \
REGION=us-central1 \
RELAY_SERVICE_NAME=drama-processor-relay-service \
SERVICE_ACCOUNT=sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com \
./eventarc_setup.sh
```

### 3. 验证触发器配置

```bash
gcloud beta eventarc triggers describe drama-processor-trigger \
  --location=us-central1 \
  --project=fleet-blend-469520-n7 \
  --format="yaml"
```

**确认以下配置：**
- `destination.runService`: `drama-processor-relay-service`
- `destination.runPath`: `/api/relay/event`
- `eventFilters[0].value`: `google.cloud.storage.object.v1.finalized`
- `eventFilters[1].value`: `vigloo_source`
- `eventFilters[2].pathPattern`: `objects/**/_PROCESS_NOW.txt`

### 4. 验证 Relay 服务

```bash
# 检查服务状态
gcloud run services describe drama-processor-relay-service \
  --region=us-central1 \
  --project=fleet-blend-469520-n7 \
  --format="value(status.url)"

# 检查服务日志
gcloud run services logs read drama-processor-relay-service \
  --region=us-central1 \
  --project=fleet-blend-469520-n7 \
  --limit=20
```

### 5. 端到端测试

1. **创建一个传输任务**（通过前端或 API）
2. **等待传输完成**
3. **检查 Relay 服务日志**，确认收到 Eventarc 事件：
   ```bash
   gcloud run services logs read drama-processor-relay-service \
     --region=us-central1 \
     --project=fleet-blend-469520-n7 \
     --limit=50 \
     --format="table(timestamp,textPayload)"
   ```
   应该看到类似以下日志：
   ```
   📬 接收到 Eventarc 事件 type=google.cloud.storage.object.v1.finalized bucket=vigloo_source name=...
   🎯 匹配到 pipeline job ... (drama=...)
   ✅ 已触发 Cloud Run Job ... (operation=...)
   ```

4. **检查 Process Job 是否被触发**，并确认包含 `JOB_ID` 环境变量：
   ```bash
   gcloud run jobs executions list \
     --job=drama-processor-job \
     --region=us-central1 \
     --project=fleet-blend-469520-n7 \
     --limit=5
   ```

5. **检查 Process Job 日志**，确认 JOB_ID 正确传递：
   ```bash
   # 获取最新的 execution
   EXECUTION=$(gcloud run jobs executions list \
     --job=drama-processor-job \
     --region=us-central1 \
     --project=fleet-blend-469520-n7 \
     --limit=1 \
     --format="value(name)")
   
   # 查看日志
   gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=drama-processor-job AND resource.labels.location=us-central1" \
     --limit=50 \
     --project=fleet-blend-469520-n7 \
     --format="table(timestamp,textPayload)"
   ```

## 故障排查

### 问题 1: Relay 服务返回 404

**原因：** 端点路径不正确

**解决：** 确认路由配置已更新，端点路径应为 `/api/relay/event`

### 问题 2: Relay 服务找不到 job

**原因：** Firestore 查询条件不匹配

**检查：**
- Job 文档的 `transfer_completed` 是否为 `True`
- Job 文档的 `stage` 是否为 `1`
- Job 文档的 `drama_name` 是否与 GCS 对象路径匹配

### 问题 3: Process Job 未触发

**原因：** Relay 服务触发 Job 失败

**检查：**
- Relay 服务是否有权限调用 Cloud Run Jobs API
- `PROCESSOR_JOB_NAME` 环境变量是否正确配置
- Service Account 是否有 `roles/run.invoker` 权限

### 问题 4: Process Job 缺少 JOB_ID

**原因：** Relay 服务未正确传递环境变量

**检查：**
- Relay 服务日志，确认 `_trigger_cloud_run_job` 是否成功调用
- Process Job 的环境变量配置

## 验证清单

- [ ] CI/CD 部署完成
- [ ] Relay 服务已部署并可访问
- [ ] Eventarc 触发器已更新
- [ ] 触发器配置指向 relay 服务
- [ ] 测试传输任务完成
- [ ] Relay 服务收到 Eventarc 事件
- [ ] Process Job 被正确触发
- [ ] Process Job 包含正确的 JOB_ID 环境变量

## 相关文档

- `backend/scripts/RELAY_JOB_ID_TEST_REPORT.md` - 详细测试报告
- `infra/eventarc_setup.sh` - Eventarc 触发器配置脚本
- `backend/app/api/v1/relay.py` - Relay 端点实现

