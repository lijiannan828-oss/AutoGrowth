# 全局并发控制测试报告

## 测试概述

本次测试验证了使用 Firestore 事务实现的全局并发控制机制，确保在多个请求同时触发 job 时，只有指定数量的 job 能够同时运行，其他 job 会被正确排队。

## 实现方案

### 核心机制

1. **Firestore 事务保护**: 使用 `@firestore.transactional` 装饰器确保原子操作
2. **并发控制文档**: 在 `system_config/concurrency_control` 文档中维护：
   - `running_jobs`: 当前运行的 job 数量
   - `running_job_ids`: 当前运行的 job ID 列表
   - `queue`: 排队等待的 job ID 列表
3. **自动清理**: 在获取 slot 前自动清理已完成的 job

### 关键函数

- `_acquire_job_slot(job_id)`: 使用事务原子性地获取 job slot
- `_cleanup_completed_jobs()`: 清理已完成的 job，释放 slot
- `_release_job_slot(job_id)`: 释放 slot（由清理函数自动处理）

## 测试结果

### Test 1: 并发请求（100ms 延迟）

**场景**: 5 个请求，每个请求间隔 100ms

**结果**:
- ✅ 1 个 job 成功启动（`test_job_2`）
- ✅ 4 个 job 被排队（`test_job_1`, `test_job_4`, `test_job_3`, `test_job_0`）
- ✅ Firestore 文档状态正确：
  - `running_jobs: 1`
  - `running_job_ids: ['test_job_2']`
  - `queue: ['test_job_1', 'test_job_4', 'test_job_3', 'test_job_0']`

**验证**: ✅ 通过

### Test 2: 接近同时的请求（10ms 延迟）

**场景**: 5 个请求，每个请求间隔仅 10ms（模拟用户几乎同时点击）

**结果**:
- ✅ 1 个 job 成功启动（`test_job_3`）
- ✅ 4 个 job 被排队（`test_job_4`, `test_job_1`, `test_job_0`, `test_job_2`）
- ✅ Firestore 文档状态正确：
  - `running_jobs: 1`
  - `running_job_ids: ['test_job_3']`
  - `queue: ['test_job_4', 'test_job_1', 'test_job_0', 'test_job_2']`

**验证**: ✅ 通过

**关键验证点**: 即使请求几乎同时到达（10ms 间隔），Firestore 事务仍然确保了原子性，只有一个 job 能够获取 slot。

### Test 3: 清理已完成 job

**场景**: 测试自动清理已完成的 job

**结果**:
- ✅ 成功清理 1 个已完成的 job
- ✅ `running_jobs` 从 1 降为 0
- ✅ `running_job_ids` 从 `['test_completed_job']` 变为 `[]`

**验证**: ✅ 通过

## 关键发现

### ✅ 事务保护有效

测试结果证明 Firestore 事务成功防止了竞态条件：

1. **Test 1 和 Test 2** 都显示，即使多个请求几乎同时到达，也只有 1 个 job 能够获取 slot
2. 其他 job 被正确排队，没有出现"两个请求同时读取数据库，发现当前运行 0 个，于是都判断可以通过"的情况

### ✅ 原子操作保证

Firestore 事务确保了：
- 读取 `running_jobs` 和 `queue`
- 检查是否可以启动
- 更新 `running_jobs` 和 `running_job_ids`（或添加到 `queue`）

这三个操作是原子性的，不会出现中间状态被其他请求读取的情况。

### ✅ 自动清理机制

`_cleanup_completed_jobs()` 函数能够正确识别已完成的 job（状态为 `SUCCEEDED` 或 `FAILED`）并自动释放 slot。

## 配置

当前配置：
- `MAX_CONCURRENT_JOBS: 1`（可通过环境变量 `MAX_CONCURRENT_JOBS` 调整）

## 测试命令

```bash
cd backend
python scripts/test_concurrency_control.py
```

## 下一步

1. ✅ 并发控制机制已实现并通过测试
2. ⏳ 部署到生产环境
3. ⏳ 监控生产环境中的并发控制效果
4. ⏳ 根据实际需求调整 `MAX_CONCURRENT_JOBS` 值

## 注意事项

1. **Fail-Open 策略**: 如果事务失败，当前实现采用"fail-open"策略，允许 job 继续执行，避免因系统故障导致所有 job 被阻塞。

2. **队列处理**: 当前实现将 job 加入队列后立即返回。如果需要自动触发队列中的下一个 job，需要额外的机制（例如：定期检查队列的后台任务，或在 job 完成时触发下一个 job）。

3. **清理时机**: 当前在每次获取 slot 前清理已完成的 job。如果需要更及时的清理，可以考虑：
   - 在 job 完成时立即清理（需要修改 worker 代码）
   - 使用定期任务清理（例如：每分钟运行一次）


