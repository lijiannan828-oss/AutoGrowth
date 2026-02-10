# Relay 端点问题修复报告

## 问题描述

线上传输任务（Job ID: `cmSLOCznhQOxY4jozRXP`）完成后，压制任务未被触发。

## 诊断结果

使用诊断脚本 `diagnose_relay_issue.py` 检查后发现：

### ✅ 正常的部分
1. **Job 存在且条件正确**
   - `drama_name`: "US044P01S01_Runaway Prince's Secret Vacation"
   - `transfer_completed`: `true`
   - `stage`: `1`
   - `status`: "COMPLETE"

2. **GCS 信号文件存在**
   - 路径: `gs://vigloo_source/US044P01S01_Runaway Prince's Secret Vacation/_PROCESS_NOW.txt`
   - ✅ 文件存在

3. **drama_name 提取逻辑正确**
   - 从 GCS 对象路径能正确提取 drama_name

### ❌ 问题所在

**Relay 查询逻辑未按时间排序，导致选择了错误的 job**

诊断结果显示：
- 查询条件 `drama_name == 'US044P01S01_Runaway Prince's Secret Vacation'` 找到了 **7 个匹配的 job**
- 其中 **5 个是 ready job**（`transfer_completed=True, stage=1`）
- Relay 查询逻辑**没有按 `updated_at` 排序**，返回的是第一个匹配的 job（`7jOFh81IF2v2SVA1ijlz`）
- 目标 job (`cmSLOCznhQOxY4jozRXP`) 虽然也是 ready job，但因为不是第一个，所以**没有被选中**

## 根本原因

`_find_latest_ready_job` 函数的查询逻辑：

```python
# 修复前（错误）
query = (
    firestore_client.collection(FIRESTORE_COLLECTION)
    .where("drama_name", "==", drama_name)
    .limit(20)  # ❌ 没有排序，返回的是第一个匹配的 job
)
```

**问题：** Firestore 查询默认按文档 ID 排序，不是按时间排序。当同一个 drama_name 有多个 ready job 时，会返回第一个匹配的 job，而不是最新的 job。

## 修复方案

在查询中添加 `order_by("updated_at", direction=firestore.Query.DESCENDING)`，确保返回最新的 job：

```python
# 修复后（正确）
query = (
    firestore_client.collection(FIRESTORE_COLLECTION)
    .where("drama_name", "==", drama_name)
    .order_by("updated_at", direction=firestore.Query.DESCENDING)  # ✅ 按更新时间降序排序
    .limit(20)
)
```

**修复效果：**
- 查询结果按 `updated_at` 降序排序
- 返回第一个匹配的 ready job，即**最新的 ready job**
- 确保选择的是最近完成的传输任务

## 修复验证

修复后，使用诊断脚本验证：

```bash
python scripts/diagnose_relay_issue.py --job-id cmSLOCznhQOxY4jozRXP --bucket vigloo_source
```

**预期结果：**
- ✅ Relay 会选择目标 job (`cmSLOCznhQOxY4jozRXP`)
- ✅ 因为它是按 `updated_at` 排序后的第一个 ready job

## 影响范围

### 受影响的情况
- 同一个 drama_name 有多个传输任务
- 多个传输任务都已完成（`transfer_completed=True, stage=1`）
- Relay 查询时，旧的传输任务会被错误地选中

### 不受影响的情况
- 每个 drama_name 只有一个传输任务
- 传输任务完成后立即触发压制（没有其他 ready job）

## 部署步骤

1. **部署修复后的代码**
   ```bash
   git push origin main  # 触发 CI/CD
   ```

2. **等待 CI/CD 完成**
   - 确认 `drama-processor-relay-service` 已更新

3. **验证修复**
   - 创建一个新的传输任务
   - 等待传输完成
   - 确认压制任务被正确触发
   - 检查 relay 服务日志，确认选择了正确的 job

4. **对于已存在的任务**
   - 如果传输已完成但压制未触发，可以：
     - 手动触发压制（通过前端）
     - 或者等待下次传输完成后自动触发（如果 drama_name 相同）

## 相关文件

- `backend/app/api/v1/relay.py` - Relay 端点实现（已修复）
- `backend/scripts/diagnose_relay_issue.py` - 诊断脚本
- `backend/scripts/test_relay_job_id.py` - 测试脚本

## 总结

✅ **问题已修复**：Relay 查询逻辑现在按 `updated_at` 降序排序，确保选择最新的 ready job。

✅ **根本原因**：查询未排序，导致选择了错误的 job。

⚠️ **待部署**：需要在生产环境部署修复后的代码。

