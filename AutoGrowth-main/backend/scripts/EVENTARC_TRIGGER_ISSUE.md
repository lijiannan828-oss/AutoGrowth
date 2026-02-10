# Eventarc 触发器问题诊断与修复

## 问题发现

### ✅ 触发器存在
- **名称**: `drama-processor-trigger`
- **区域**: `asia-northeast3`
- **目标服务**: `drama-processor-relay-service` (us-central1)

### ❌ 配置错误

#### 问题 1: 路径配置错误
- **当前**: `path: /`
- **应该**: `path: /api/relay/event`
- **影响**: Eventarc 触发时发送请求到 `/`，导致 Relay Service 返回 `404 Not Found`

#### 问题 2: 缺少路径过滤器
- **当前**: 只有 `type` 和 `bucket` 过滤器
- **缺少**: `subject` 过滤器来匹配 `_PROCESS_NOW.txt`
- **影响**: 所有 GCS 对象创建都会触发，包括非信号文件

### 证据

#### Relay Service 日志显示大量 404 错误：
```
2025-11-22T14:46:33.300548Z  INFO:     169.254.169.126:29766 - "POST / HTTP/1.1" 404 Not Found
2025-11-22T14:46:32.206225Z  INFO:     169.254.169.126:29752 - "POST / HTTP/1.1" 404 Not Found
...
```

这说明：
1. ✅ Eventarc **确实在触发**（有 POST 请求）
2. ❌ 但路径错误（请求到 `/` 而不是 `/api/relay/event`）
3. ❌ Relay Service 无法处理这些请求（404）

## 根本原因

Eventarc 触发器配置不正确：
- 路径设置为 `/` 而不是 `/api/relay/event`
- 缺少路径过滤器来只匹配 `_PROCESS_NOW.txt` 文件

## 解决方案

### 方法 1: 使用修复脚本（推荐）

```bash
cd /Users/mac/AutoGrowth
./backend/scripts/fix_eventarc_trigger.sh
```

脚本会：
1. 显示当前配置
2. 删除现有触发器
3. 使用正确配置重新创建触发器

### 方法 2: 手动修复

```bash
# 1. 删除现有触发器
gcloud eventarc triggers delete drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7

# 2. 重新创建（正确配置）
gcloud beta eventarc triggers create drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7 \
  --destination-run-service=drama-processor-relay-service \
  --destination-run-region=us-central1 \
  --destination-run-path="/api/relay/event" \
  --service-account=sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=vigloo_source" \
  --event-filters-path-pattern="subject=objects/**/_PROCESS_NOW.txt" \
  --transport-topic="projects/fleet-blend-469520-n7/topics/drama-processor-trigger-topic" \
  --labels="autogrowth=eventarc,worker=drama-processor"
```

### 关键修复点

1. **路径修复**: `--destination-run-path="/api/relay/event"`
2. **路径过滤器**: `--event-filters-path-pattern="subject=objects/**/_PROCESS_NOW.txt"`

## 验证步骤

### 1. 检查触发器配置
```bash
gcloud eventarc triggers describe drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7 \
  --format="yaml(destination.cloudRun.path,eventFilters)"
```

**预期输出**:
```yaml
destination:
  cloudRun:
    path: /api/relay/event
eventFilters:
- attribute: type
  value: google.cloud.storage.object.v1.finalized
- attribute: bucket
  value: vigloo_source
- attribute: subject
  value: objects/**/_PROCESS_NOW.txt
```

### 2. 测试触发器（可选）

手动创建一个测试信号文件：
```bash
echo "test" | gsutil cp - gs://vigloo_source/TEST_DRAMA/_PROCESS_NOW.txt
```

然后检查 Relay Service 日志：
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=drama-processor-relay-service" --limit=10 --format="table(timestamp,textPayload)" --project=fleet-blend-469520-n7
```

应该看到：
- ✅ POST 请求到 `/api/relay/event`（不是 `/`）
- ✅ 200 OK 响应（不是 404）

### 3. 对于当前传输任务

由于信号文件 `_PROCESS_NOW.txt` 已经在 `2025-11-22 14:34:01` 创建，修复触发器后：
- ⚠️ **不会自动触发**（因为事件已经发生）
- ✅ **可以手动触发**压制任务，或等待下一个传输任务

## 修复后的预期行为

1. ✅ 传输任务完成时创建 `_PROCESS_NOW.txt`
2. ✅ Eventarc 捕获事件（只匹配 `_PROCESS_NOW.txt`）
3. ✅ 发送 POST 请求到 `drama-processor-relay-service/api/relay/event`
4. ✅ Relay Service 接收请求并处理
5. ✅ 创建压制任务并触发 Cloud Run Job

---

**问题诊断时间**: 2025-11-22
**修复脚本**: `backend/scripts/fix_eventarc_trigger.sh`


