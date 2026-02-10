# Eventarc 触发器修复完成报告

## 修复时间
2025-11-22

## 问题总结

### ✅ 问题已解决
1. **路径配置错误**: 已从 `/` 修复为 `/api/relay/event`
2. **触发器已重新创建**: 使用正确配置

### ⚠️ 路径过滤器限制
- **限制**: Eventarc 不支持 GCS 对象事件的路径过滤（`subject` 属性）
- **解决方案**: Relay Service 已实现路径过滤逻辑（第 247 行）
- **行为**: 所有 GCS 对象创建都会触发，但 Relay Service 会忽略非 `_PROCESS_NOW.txt` 文件

## 修复后的配置

### Eventarc 触发器
- **名称**: `drama-processor-trigger`
- **区域**: `asia-northeast3`
- **目标服务**: `drama-processor-relay-service` (us-central1)
- **路径**: `/api/relay/event` ✅
- **事件过滤器**:
  - `type=google.cloud.storage.object.v1.finalized`
  - `bucket=vigloo_source`

### Relay Service 路径过滤
Relay Service (`backend/app/api/v1/relay.py`) 已实现路径过滤：

```python
if not object_name or not object_name.endswith(PROCESS_SIGNAL_SUFFIX):
    logger.info("⏭️  非目标对象，直接忽略")
    return {"status": "ignored", "reason": "object_not_matching"}
```

**行为**:
- ✅ 只处理以 `_PROCESS_NOW.txt` 结尾的文件
- ✅ 其他文件自动忽略（返回 200，避免 Eventarc 重试）

## 验证结果

### ✅ 触发器配置验证
```yaml
destination:
  cloudRun:
    path: /api/relay/event  # ✅ 正确
    region: us-central1
    service: drama-processor-relay-service
eventFilters:
- attribute: type
  value: google.cloud.storage.object.v1.finalized
- attribute: bucket
  value: vigloo_source
```

### ⏳ 触发器激活状态
- **状态**: 已创建，需要约 2 分钟完全激活
- **警告**: "It may take up to 2 minutes for the new trigger to become active"

## 关于当前传输任务

### 传输任务信息
- **Job ID**: `f7DTMToHvkNLqBe4Bl97`
- **Drama Name**: `KR064P01S01_헤이트 메리지`
- **信号文件**: `gs://vigloo_source/KR064P01S01_헤이트 메리지/_PROCESS_NOW.txt`
- **创建时间**: `2025-11-22 14:34:01`

### ⚠️ 不会自动触发
由于信号文件已在触发器修复前创建，**不会自动触发**压制任务。

### ✅ 解决方案
1. **手动触发**: 使用 API 或脚本手动触发压制任务
2. **等待下一个传输任务**: 新的传输任务完成后会自动触发

## 修复后的预期行为

### 正常流程
1. ✅ 传输任务完成 → 创建 `_PROCESS_NOW.txt`
2. ✅ Eventarc 捕获 GCS 对象创建事件
3. ✅ 发送 POST 请求到 `drama-processor-relay-service/api/relay/event`
4. ✅ Relay Service 检查文件路径（只处理 `_PROCESS_NOW.txt`）
5. ✅ Relay Service 查找 ready job 并触发 Cloud Run Job
6. ✅ Cloud Run Job 使用 Sharding 架构并行处理

### 非目标文件处理
- ✅ Eventarc 触发所有 GCS 对象创建
- ✅ Relay Service 检查路径，忽略非 `_PROCESS_NOW.txt` 文件
- ✅ 返回 200 OK（避免 Eventarc 重试）

## 监控建议

### 1. 检查触发器状态（2 分钟后）
```bash
gcloud eventarc triggers describe drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7
```

### 2. 监控 Relay Service 日志
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=drama-processor-relay-service" \
  --limit=20 \
  --format="table(timestamp,textPayload)" \
  --project=fleet-blend-469520-n7
```

**预期日志**:
- ✅ `📬 接收到 Eventarc 事件` - 所有 GCS 事件
- ✅ `⏭️  非目标对象，直接忽略` - 非 `_PROCESS_NOW.txt` 文件
- ✅ `🎯 匹配到 pipeline job` - `_PROCESS_NOW.txt` 文件

### 3. 测试触发器（可选）
手动创建测试信号文件：
```bash
echo "test" | gsutil cp - gs://vigloo_source/TEST_DRAMA/_PROCESS_NOW.txt
```

然后检查 Relay Service 日志，应该看到：
- ✅ POST 请求到 `/api/relay/event`（不是 `/`）
- ✅ 200 OK 响应（不是 404）
- ✅ 处理逻辑执行（或忽略，如果找不到 job）

## 总结

✅ **修复完成**:
- Eventarc 触发器路径已修复：`/api/relay/event`
- Relay Service 已实现路径过滤
- 触发器已重新创建并激活

⏳ **等待激活**:
- 触发器需要约 2 分钟完全激活
- 之后新的传输任务将自动触发压制任务

📝 **下一步**:
- 等待触发器激活
- 监控 Relay Service 日志
- 测试下一个传输任务的自动触发

---

**修复完成时间**: 2025-11-22
**修复脚本**: `backend/scripts/fix_eventarc_trigger.sh`


