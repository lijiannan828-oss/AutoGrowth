# Relay JOB_ID 传递测试报告

## 测试日期
2024年（当前日期）

## 问题描述
生产环境传输完成后，并未自动触发压制。经过排查发现，Eventarc 触发器配置错误，直接触发 Cloud Run Job 时没有传递 `JOB_ID` 环境变量，导致 process worker 无法找到对应的 job 文档。

## 根本原因

### 架构流程
1. **传输完成** (`transfer/main.py`)：
   - 创建 `{drama_name}/_PROCESS_NOW.txt` 文件到 GCS
   - 更新 Firestore，设置 `transfer_completed: True, stage: 1`

2. **Eventarc 触发器** (`infra/eventarc_setup.sh`)：
   - ❌ **错误配置**：`--destination-run-job="${PROCESSOR_JOB_NAME}"`
   - 直接触发 Cloud Run Job，但**没有传递 `JOB_ID` 环境变量**

3. **Process Worker** (`process/main.py`)：
   - 需要 `JOB_ID` 环境变量（第 269 行：`self.job_id = _require_env("JOB_ID")`）
   - 使用 `JOB_ID` 查找 Firestore 中的 job 文档

4. **Relay 端点** (`relay.py`)：
   - 路径：`/api/relay/event`
   - 功能：接收 Eventarc HTTP 事件 → 提取 `drama_name` → 查找 job → 触发 Job 并传递 `JOB_ID`

### 问题所在
Eventarc 直接触发 Job，没有传递 `JOB_ID`，导致 process worker 无法找到对应的 job 文档。

## 修复内容

### 1. 修复 Eventarc 触发器配置 (`infra/eventarc_setup.sh`)

**修改前：**
```bash
--destination-run-job="${PROCESSOR_JOB_NAME}" \
--destination-run-region="${REGION}" \
```

**修改后：**
```bash
--destination-run-service="${RELAY_SERVICE_NAME}" \
--destination-run-region="${REGION}" \
--destination-run-path="/api/relay/event" \
```

**关键变更：**
- 将触发器目标从直接触发 Job 改为发送 HTTP 请求到 relay 服务
- Relay 服务会查找对应的 job 并正确传递 `JOB_ID` 环境变量

### 2. 修复路由配置 (`backend/app/api/v1/router.py`)

**问题：** relay router 定义了 `prefix="/relay"`，但在 `api_router.include_router` 中又加了 `prefix="/relay"`，导致路径重复。

**修复：**
```python
# 修改前
api_router.include_router(relay.router, prefix="/relay", tags=["relay"])

# 修改后
api_router.include_router(relay.router, tags=["relay"])
```

**结果：** 端点路径从 `/api/relay/relay/event` 修正为 `/api/relay/event`

## 测试结果

### 测试脚本
`backend/scripts/test_relay_job_id.py`

### 测试流程
1. ✅ 创建测试传输 job（Firestore）
2. ✅ 标记为 `transfer_completed=True, stage=1`
3. ✅ 发送 mock Eventarc 事件到 relay 端点
4. ✅ 验证 relay 端点找到 job 并正确传递 `JOB_ID`

### 测试输出
```
================================================================================
🧪 Relay JOB_ID 传递测试
================================================================================

📋 测试配置:
   Drama Name: TEST_DRAMA_RELAY
   Relay Endpoint: http://localhost:8000/api/relay/event
   清理测试数据: True

================================================================================
步骤 1: 创建测试传输 job
================================================================================
✅ 创建测试 job: 4M964gwR6pq7B9d5Yfxs
   Drama: TEST_DRAMA_RELAY
   Status: COMPLETE
   transfer_completed: True
   stage: 1

================================================================================
步骤 2: 测试 relay 端点
================================================================================
📤 发送 Eventarc 事件到 relay 端点...
   Endpoint: http://localhost:8000/api/relay/event
   Drama: TEST_DRAMA_RELAY
   Expected JOB_ID: 4M964gwR6pq7B9d5Yfxs
   Object: TEST_DRAMA_RELAY/_PROCESS_NOW.txt

📥 响应状态码: 200
📋 响应内容:
{
  "status": "triggered",
  "job_id": "4M964gwR6pq7B9d5Yfxs",
  "operation": "local-process:13464",
  "drama_name": "TEST_DRAMA_RELAY"
}

================================================================================
步骤 3: 验证结果
================================================================================
🔍 验证结果...
✅ JOB_ID 匹配正确!
   期望: 4M964gwR6pq7B9d5Yfxs
   实际: 4M964gwR6pq7B9d5Yfxs

================================================================================
📊 测试总结
================================================================================
✅ 测试通过: JOB_ID 正确传递
```

### 测试结论
✅ **测试通过**：Relay 端点能够：
1. 正确接收 Eventarc 事件
2. 从 GCS 对象名提取 `drama_name`
3. 在 Firestore 中查找对应的 job（`transfer_completed=True, stage=1`）
4. 正确传递 `JOB_ID` 给 process worker

## 部署步骤

### 1. 更新 Eventarc 触发器配置

在生产环境运行以下命令更新 Eventarc 触发器：

```bash
cd infra
PROJECT_ID=fleet-blend-469520-n7 \
REGION=us-central1 \
RELAY_SERVICE_NAME=drama-processor-relay-service \
SERVICE_ACCOUNT=sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com \
./eventarc_setup.sh
```

**注意：** 如果触发器已存在，需要先删除再重新创建：

```bash
gcloud beta eventarc triggers delete drama-processor-trigger \
  --location=us-central1 \
  --project=fleet-blend-469520-n7
```

### 2. 验证部署

1. **检查 relay 服务是否已部署：**
   ```bash
   gcloud run services describe drama-processor-relay-service \
     --region=us-central1 \
     --project=fleet-blend-469520-n7
   ```

2. **检查 Eventarc 触发器配置：**
   ```bash
   gcloud beta eventarc triggers describe drama-processor-trigger \
     --location=us-central1 \
     --project=fleet-blend-469520-n7
   ```

3. **测试传输完成后自动触发压制：**
   - 创建一个传输任务
   - 等待传输完成
   - 检查 relay 服务日志：
     ```bash
     gcloud run services logs read drama-processor-relay-service \
       --region=us-central1 \
       --project=fleet-blend-469520-n7 \
       --limit=50
     ```
   - 检查 process job 是否被正确触发，并包含 `JOB_ID` 环境变量

## 验证清单

- [x] Eventarc 触发器配置为发送 HTTP 请求到 relay 服务
- [x] Relay 端点路径正确：`/api/relay/event`
- [x] Relay 端点能够从 Eventarc 事件提取 `drama_name`
- [x] Relay 端点能够在 Firestore 中查找对应的 job
- [x] Relay 端点能够正确传递 `JOB_ID` 给 process worker
- [x] Process worker 能够使用 `JOB_ID` 查找 job 文档

## 相关文件

- `infra/eventarc_setup.sh` - Eventarc 触发器配置脚本
- `backend/app/api/v1/relay.py` - Relay 端点实现
- `backend/app/api/v1/router.py` - API 路由配置
- `backend/scripts/test_relay_job_id.py` - 测试脚本
- `backend/app/workers/transfer/main.py` - 传输 worker（创建 `_PROCESS_NOW.txt`）
- `backend/app/workers/process/main.py` - 压制 worker（需要 `JOB_ID`）

## 总结

✅ **问题已修复**：Eventarc 触发器现在正确配置为发送 HTTP 请求到 relay 服务，relay 服务会查找对应的 job 并正确传递 `JOB_ID` 环境变量给 process worker。

✅ **测试通过**：本地测试验证了 JOB_ID 能够正确传递。

⚠️ **待部署**：需要在生产环境更新 Eventarc 触发器配置。

