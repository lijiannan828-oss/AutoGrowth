# 清理僵尸任务操作指南

## 问题症状
- 新任务一直卡在 `QUEUED` 状态（超过 5 分钟）
- Firestore `concurrency_control/global` 文档中 `active_jobs` 数量已满（通常是 3）
- `active_job_ids` 数组中有已完成但未释放的任务 ID

## 操作步骤

### 步骤 1：打开 Firestore Console
访问：https://console.cloud.google.com/firestore/data/concurrency_control?project=fleet-blend-469520-n7

### 步骤 2：查看 global 文档
点击 `global` 文档，查看当前状态：
```json
{
  "active_jobs": 3,
  "max_concurrent_jobs": 3,
  "active_job_ids": [
    "job_abc123",
    "job_def456",
    "job_ghi789"
  ],
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### 步骤 3：识别僵尸任务
对于 `active_job_ids` 中的每个任务 ID：

1. 在 Firestore 中打开 `pipeline_jobs` 集合
2. 搜索该任务 ID（使用 Ctrl+F 或搜索框）
3. 查看任务状态：
   - ✅ `status = "PROCESSING"` 且 `updated_at` 在最近 30 分钟内 → **正常任务**（保留）
   - ❌ `status = "SUCCEEDED"` 或 `"FAILED"` → **僵尸任务**（需要清理）
   - ❌ `status = "PROCESSING"` 但 `updated_at` 超过 2 小时前 → **卡死任务**（需要清理）

### 步骤 4：手动清理
1. 返回 `concurrency_control/global` 文档
2. 点击右上角的 **"编辑文档"** 按钮（铅笔图标）
3. 修改 `active_job_ids` 数组：
   - 删除僵尸任务的 ID
   - 只保留正常运行的任务 ID
   
   **示例：**
   ```json
   // 修改前
   "active_job_ids": ["job_abc123", "job_def456", "job_ghi789"]
   
   // 修改后（假设 job_abc123 和 job_ghi789 是僵尸任务）
   "active_job_ids": ["job_def456"]
   ```

4. 修改 `active_jobs` 数量：
   ```json
   // 修改前
   "active_jobs": 3
   
   // 修改后（只剩 1 个正常任务）
   "active_jobs": 1
   ```

5. 点击 **"更新"** 按钮保存

### 步骤 5：验证修复
1. 返回 `pipeline_jobs` 集合
2. 找到之前卡在 QUEUED 的任务
3. 刷新页面（F5）
4. 查看任务状态：
   - ✅ `status` 应该从 `QUEUED` 变为 `PROCESSING`
   - ✅ `updated_at` 应该更新为最近时间
   - ✅ `progress` 应该显示 "开始处理..."

### 步骤 6：监控任务执行
1. 打开 Cloud Run Jobs 日志：
   https://console.cloud.google.com/run/jobs/details/us-central1/process-worker/logs?project=fleet-blend-469520-n7

2. 查看实时日志输出：
   - 应该看到 `[process-worker]` 开头的日志
   - 应该看到 `🎞️ 正在压制` 等进度信息

## 预防措施

### 方法 1：增加最大并发数
如果资源充足，可以增加并发数：

1. 编辑 `concurrency_control/global` 文档
2. 修改 `max_concurrent_jobs`：
   ```json
   "max_concurrent_jobs": 5  // 从 3 改为 5
   ```

### 方法 2：定期检查
建议每天检查一次 `concurrency_control` 状态，及时清理僵尸任务。

### 方法 3：添加自动清理机制（开发任务）
可以添加 Cloud Function 定期检查并自动清理超时任务：
- 每 10 分钟运行一次
- 检查 `active_job_ids` 中的任务状态
- 自动清理已完成或超时的任务

## 常见问题

### Q1：清理后任务仍然不开始？
**可能原因：**
- Cloud Run Job 未部署或崩溃
- Backend API 未正确触发 Worker

**排查步骤：**
1. 检查 Cloud Run Jobs 是否存在：
   ```bash
   gcloud run jobs list --region=us-central1 --project=fleet-blend-469520-n7
   ```
2. 查看 Backend API 日志

### Q2：如何判断任务是否真的卡死？
**判断标准：**
- `status = "PROCESSING"`
- `updated_at` 超过 30 分钟未更新
- `processed_files` 数量不增加
- Cloud Run 日志无新输出

### Q3：清理后会丢失数据吗？
**不会。** 清理只是释放并发槽位，不会删除任务数据：
- 任务文档仍然保留在 `pipeline_jobs` 集合中
- 已处理的文件仍然在 GCS 中
- 可以使用 "重试" 功能重新处理失败的文件

## 紧急联系
如果清理后仍然无法解决问题，请联系开发团队并提供：
1. 任务 ID
2. Firestore 截图
3. Cloud Run 日志截图

