# 状态不一致问题分析

## 问题描述

**Cloud Run Job**: `drama-processor-job-r97dq`  
**Firestore 任务 ID**: `Fp5HMjddmNCV1tAKczJp`  
**剧集**: `US009P03S01_Good Girl Gone Bad`

### 问题现象

1. **Cloud Run Job 状态**: ✅ 50 个任务正在运行
2. **Firestore 任务状态**: ✅ `PROCESSING`
3. **Firestore 任务进度**: ❌ `等待执行 (Job queued (position=1, running=1/1))`
4. **实际执行情况**: ✅ 有 5 个任务文档在执行，`processed_files=55`

### 状态不一致

- **状态字段**: `PROCESSING` ✅（正确）
- **进度字段**: `等待执行 (Job queued...)` ❌（错误，应该显示实际进度）

## 根本原因

### Worker 初始化逻辑

在 `backend/app/workers/process/main.py` 的 `run()` 方法中：

```python
# Line 472: 更新状态为 PROCESSING
self.job_ref.update({
    "status": "PROCESSING",
    # ... 其他字段
})
```

**问题**: Worker 在启动时只更新了 `status` 字段，**没有更新 `progress` 字段**。

### 进度字段的更新时机

1. **排队时**: Relay Service 或 Service 层设置 `progress = "等待执行 (Job queued...)"`
2. **Worker 启动时**: 只更新 `status = PROCESSING`，**不更新 `progress`**
3. **处理过程中**: Worker 可能在其他地方更新 `progress`，但初始化时没有更新

### 代码位置

**文件**: `backend/app/workers/process/main.py`  
**行号**: 469-480

```python
# Update main job: set total_files if not already set, and update status
self.job_ref.update({
    "status": "PROCESSING",
    "stage": 2,
    "total_files": len(all_pairs),
    "processed_files": 0,
    "failed_files": 0,
    "updated_at": SERVER_TIMESTAMP,
})
```

**缺失**: 没有更新 `progress` 字段。

## 解决方案

### 方案 1: 在 Worker 初始化时更新 progress（推荐）

在 Worker 启动时，将 `progress` 更新为实际的处理状态：

```python
self.job_ref.update({
    "status": "PROCESSING",
    "stage": 2,
    "total_files": len(all_pairs),
    "processed_files": 0,
    "failed_files": 0,
    "progress": f"开始处理（共 {len(all_pairs)} 个文件）",  # 新增
    "updated_at": SERVER_TIMESTAMP,
})
```

### 方案 2: 在任务文档初始化时更新主任务进度

在创建任务文档时，同时更新主任务的 `progress`：

```python
task_ref.set({
    "status": "RUNNING",
    "current_file": None,
    # ...
})

# 同时更新主任务进度
self.job_ref.update({
    "progress": f"任务 {self.task_index}/{self.task_count} 已启动",
})
```

### 方案 3: 定期更新进度

在处理过程中定期更新 `progress`，确保进度信息实时准确。

## 影响范围

### 当前影响

- **用户体验**: 前端显示 "等待执行"，但实际任务正在执行
- **监控**: 无法从 `progress` 字段准确判断任务状态
- **调试**: 需要查看任务文档才能确认实际执行状态

### 潜在影响

- 如果 Worker 崩溃，`progress` 可能永远停留在 "等待执行"
- 无法通过 `progress` 字段快速判断任务是否真正开始执行

## 验证

### 验证步骤

1. ✅ 确认 Cloud Run Job 正在运行（50 个任务）
2. ✅ 确认 Firestore 任务状态是 `PROCESSING`
3. ✅ 确认有任务文档在执行（Task 0, 1, 10, 11, 12 都是 RUNNING）
4. ✅ 确认 `processed_files=55`，说明任务确实在执行
5. ❌ 确认 `progress` 字段显示错误信息

### 结论

**问题确实存在**: Worker 启动时更新了 `status`，但没有更新 `progress`，导致状态不一致。

## 修复建议

**优先级**: 中（不影响功能，但影响用户体验）

**修复方案**: 采用方案 1，在 Worker 初始化时更新 `progress` 字段。

**修复位置**: `backend/app/workers/process/main.py` Line 469-480


