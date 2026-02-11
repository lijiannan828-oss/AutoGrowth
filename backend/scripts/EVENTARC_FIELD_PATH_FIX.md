# Eventarc 触发器字段路径问题修复

## 问题发现

用户在使用 `gcloud eventarc triggers describe` 命令时，发现 `destination.runService` 和 `destination.runRegion` 返回空值。

## 根本原因

**字段路径错误**：Eventarc API 中的字段路径是：
- ✅ **正确**: `destination.cloudRun.service`
- ✅ **正确**: `destination.cloudRun.region`
- ✅ **正确**: `destination.cloudRun.path`
- ❌ **错误**: `destination.runService` (不存在)
- ❌ **错误**: `destination.runRegion` (不存在)

## 验证

### 错误的命令（返回空值）
```bash
gcloud eventarc triggers describe drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7 \
  --format="get(destination.runService,destination.runRegion)"
# 返回: (空)
```

### 正确的命令（返回正确值）
```bash
gcloud eventarc triggers describe drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7 \
  --format="get(destination.cloudRun.service,destination.cloudRun.region,destination.cloudRun.path)"
# 返回:
# drama-processor-relay-service
# us-central1
# /api/relay/event
```

### 使用 YAML 格式（推荐）
```bash
gcloud eventarc triggers describe drama-processor-trigger \
  --location=asia-northeast3 \
  --project=fleet-blend-469520-n7 \
  --format="yaml(destination.cloudRun)"
```

输出：
```yaml
destination:
  cloudRun:
    path: /api/relay/event
    region: us-central1
    service: drama-processor-relay-service
```

## 触发器配置状态

✅ **触发器配置实际上是正确的**！

当前配置：
- **Service**: `drama-processor-relay-service`
- **Region**: `us-central1`
- **Path**: `/api/relay/event`
- **Event Filters**: 
  - `type=google.cloud.storage.object.v1.finalized`
  - `bucket=vigloo_source`

## 为什么之前会出现疏漏？

1. **字段路径混淆**：
   - 创建触发器时使用的参数是 `--destination-run-service` 和 `--destination-run-region`
   - 但在查询时，API 返回的字段路径是 `destination.cloudRun.service` 和 `destination.cloudRun.region`
   - 如果使用错误的字段路径查询，会返回空值

2. **验证脚本问题**：
   - `backend/scripts/diagnose_auto_trigger.py` 中使用了 `destination.get("cloudRunService", {})`，这也是错误的
   - 正确的应该是 `destination.get("cloudRun", {})`

3. **文档不一致**：
   - 某些文档中可能使用了错误的字段路径示例

## 修复措施

### 1. 修复诊断脚本

更新 `backend/scripts/diagnose_auto_trigger.py` 中的字段路径：

```python
# 错误：
run_service = destination.get("cloudRunService", {}).get("service", "N/A")
run_region = destination.get("cloudRunService", {}).get("region", "N/A")

# 正确：
run_service = destination.get("cloudRun", {}).get("service", "N/A")
run_region = destination.get("cloudRun", {}).get("region", "N/A")
```

### 2. 更新验证命令

在所有验证脚本中使用正确的字段路径：
- `destination.cloudRun.service`
- `destination.cloudRun.region`
- `destination.cloudRun.path`

### 3. 使用标准格式

推荐使用 `--format="yaml"` 或 `--format="json"` 来查看完整配置，避免字段路径错误。

## 当前状态

✅ **触发器配置正确，无需修复**

问题只是字段路径查询错误，触发器本身配置是正确的。现在需要排查为什么自动触发没有工作。

## 下一步排查

既然触发器配置是正确的，问题可能在于：
1. Eventarc 事件延迟（通常需要几秒钟）
2. Relay Service 日志级别设置
3. `_find_latest_ready_job` 查询逻辑
4. 代码部署状态


