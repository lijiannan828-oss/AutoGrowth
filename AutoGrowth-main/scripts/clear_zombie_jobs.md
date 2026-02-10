# 清理僵尸任务（手动操作指南）

## 问题症状
- 新任务一直卡在 `QUEUED` 状态
- Firestore `concurrency_control/global` 文档中 `active_jobs` 数量已满（通常是 3）
- `active_job_ids` 数组中有很久之前的任务 ID

## 操作步骤

### 步骤 1：打开 Firestore Console
1. 访问：https://console.cloud.google.com/firestore/data?project=fleet-blend-469520-n7
2. 点击 `concurrency_control` 集合
3. 点击 `global` 文档

### 步骤 2：检查当前状态
查看以下字段：
```
active_jobs: 3  (当前活跃任务数)
max_concurrent_jobs: 3  (最大并发数)
active_job_ids: ["job_id_1", "job_id_2", "job_id_3"]  (活跃任务 ID 列表)
```

### 步骤 3：识别僵尸任务
1. 复制 `active_job_ids` 中的每个任务 ID
2. 在 `pipeline_jobs` 集合中搜索这些 ID
3. 查看每个任务的状态：
   - 如果 `status = "SUCCEEDED"` 或 `"FAILED"` → 僵尸任务（应该被清理但没有）
   - 如果 `updated_at` 超过 2 小时前 → 可能是卡住的任务

### 步骤 4：手动清理
1. 点击 `concurrency_control/global` 文档的 "编辑" 按钮
2. 修改 `active_job_ids` 数组：
   - 删除僵尸任务的 ID
3. 修改 `active_jobs` 数量：
   - 减少对应的数量（例如：从 3 改为 1）
4. 点击 "更新" 保存

### 步骤 5：验证
1. 返回 `pipeline_jobs` 集合
2. 查看排队中的任务是否开始执行
3. 如果仍然不执行，可能需要手动触发（见方案 2）

## 预防措施
- 定期检查 `concurrency_control` 状态
- 如果发现任务经常卡住，可以增加 `max_concurrent_jobs` 数量（但要注意资源限制）
- 考虑添加自动清理机制（超时任务自动释放槽位）

