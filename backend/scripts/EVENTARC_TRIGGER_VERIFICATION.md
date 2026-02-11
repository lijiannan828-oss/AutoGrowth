# Eventarc 触发器配置验证报告

## 问题诊断

### 用户报告的问题
用户执行了某个命令，发现 `destination.runService` 和 `destination.runRegion` 返回空值。

### 根本原因

**字段路径错误**：Eventarc API 的字段结构是：
- ✅ `destination.cloudRun.service` (正确)
- ✅ `destination.cloudRun.region` (正确)
- ✅ `destination.cloudRun.path` (正确)
- ❌ `destination.runService` (错误 - 不存在)
- ❌ `destination.runRegion` (错误 - 不存在)
- ❌ `destination.cloudRunService` (错误 - 在诊断脚本中使用)

### 验证结果

**触发器配置实际上是正确的！**

```bash
# 正确的查询命令
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

## 为什么会出现疏漏？

### 1. 诊断脚本中的字段路径错误

在 `backend/scripts/diagnose_auto_trigger.py` 第 163-164 行：

```python
# ❌ 错误（之前）
run_service = destination.get("cloudRunService", {}).get("service", "N/A")
run_region = destination.get("cloudRunService", {}).get("region", "N/A")

# ✅ 正确（已修复）
cloud_run = destination.get("cloudRun", {})
run_service = cloud_run.get("service", "N/A")
run_region = cloud_run.get("region", "N/A")
run_path = cloud_run.get("path", "N/A")
```

### 2. gcloud 命令格式混淆

如果用户使用了错误的字段路径：
```bash
# ❌ 错误 - 返回空值
gcloud eventarc triggers describe ... \
  --format="get(destination.runService,destination.runRegion)"

# ✅ 正确 - 返回实际值
gcloud eventarc triggers describe ... \
  --format="get(destination.cloudRun.service,destination.cloudRun.region)"
```

### 3. API 字段命名不一致

- **创建触发器时**：使用参数 `--destination-run-service` 和 `--destination-run-region`
- **查询触发器时**：API 返回的字段是 `destination.cloudRun.service` 和 `destination.cloudRun.region`
- **这种不一致**容易导致混淆

## 已修复的问题

### ✅ 修复诊断脚本

已更新 `backend/scripts/diagnose_auto_trigger.py`：
- 使用正确的字段路径 `destination.cloudRun`
- 添加了 `path` 字段的显示
- 确保所有字段都能正确读取

### ✅ 创建验证文档

创建了 `backend/scripts/EVENTARC_FIELD_PATH_FIX.md` 文档，说明：
- 正确的字段路径
- 错误的字段路径
- 如何正确验证触发器配置

## 当前触发器配置状态

✅ **配置完全正确**：

- **Service**: `drama-processor-relay-service`
- **Region**: `us-central1`
- **Path**: `/api/relay/event`
- **Event Filters**:
  - `type=google.cloud.storage.object.v1.finalized`
  - `bucket=vigloo_source`
- **Service Account**: `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`

## 结论

**触发器配置没有问题**。之前看到的"空值"是因为：
1. 诊断脚本使用了错误的字段路径 (`cloudRunService` 而不是 `cloudRun`)
2. 如果用户使用了错误的 gcloud 命令格式，也会返回空值

**触发器本身配置正确，无需修复。**

现在需要排查的是为什么自动触发没有工作，这可能与：
1. Eventarc 事件延迟
2. Relay Service 日志级别
3. `_find_latest_ready_job` 查询逻辑
4. 代码部署状态

有关。


