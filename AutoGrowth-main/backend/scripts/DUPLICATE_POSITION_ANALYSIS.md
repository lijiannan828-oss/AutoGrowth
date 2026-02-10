# 重复位置问题分析

## 问题描述

用户发现两个任务显示相同的位置（position=2）：

1. **GoejsG0SNFSF453fOCF4**
   - 状态: `QUEUED`
   - 进度: `等待执行 (Job queued (position=2, running=1/1))`
   - 创建时间: 2025-11-23 14:27:24

2. **984LkYy2nTFEFLHpqCRt**
   - 状态: `QUEUED`
   - 进度: `等待执行 (Job queued (position=2, running=1/1))`
   - 创建时间: 2025-11-23 12:47:34

## 问题分析

### 实际情况

**并发控制状态**:
- 运行中的任务: `['Fp5HMjddmNCV1tAKczJp']`
- 队列中的任务: `['9coW3RXB9WHhQKa1FioF', 'GoejsG0SNFSF453fOCF4']`

**队列位置**:
- `GoejsG0SNFSF453fOCF4`: 位置 2 ✅（正确）
- `984LkYy2nTFEFLHpqCRt`: **不在队列中** ❌

### 根本原因

1. **984LkYy2nTFEFLHpqCRt** 的历史：
   - 创建于 12:47:34
   - 13:29:32 时在 `running_job_ids` 中（日志显示）
   - 后来被清理或移除了
   - **但 `progress` 字段没有被更新**，仍然显示旧的排队信息（position=2）

2. **GoejsG0SNFSF453fOCF4** 的情况：
   - 创建于 14:27:24
   - 被加入队列，实际位置是 2（正确）
   - `progress` 字段正确显示 position=2

### 问题根源

**任务清理时没有更新 `progress` 字段**：

1. 当任务被清理（超时、错误、或其他原因）时：
   - 从 `running_job_ids` 或 `queue` 中移除 ✅
   - 但 **没有更新 Firestore 任务文档的 `progress` 字段** ❌

2. 导致：
   - 任务状态是 `QUEUED`，但实际不在队列中
   - `progress` 显示旧的排队信息
   - 前端显示错误的排队位置

## 代码位置

### 清理逻辑

**文件**: `backend/app/services/concurrency_service.py`

**方法**: `_cleanup_completed_jobs()`

**问题**: 清理时只更新并发控制文档，不更新任务文档的 `progress` 字段

```python
# Line 104-108: 只更新并发控制文档
self.control_ref.update({
    "running_jobs": len(running_job_ids),
    "running_job_ids": list(running_job_ids),
    "updated_at": SERVER_TIMESTAMP,
})
# ❌ 没有更新任务文档的 progress 字段
```

### 排队逻辑

**文件**: `backend/app/services/pipeline_process_service.py`

**方法**: `_trigger_process_worker()`

**代码**: Line 178-182

```python
if not can_start:
    # Job is queued
    job_ref.update({
        "status": "QUEUED",
        "progress": f"等待执行 ({slot_message})",  # ✅ 设置 progress
        "updated_at": SERVER_TIMESTAMP,
    })
```

**问题**: 当任务被清理时，这个 `progress` 没有被清除或更新

## 解决方案

### 方案 1: 清理时更新任务文档（推荐）

在 `_cleanup_completed_jobs()` 中，清理任务时同时更新任务文档：

```python
def _cleanup_completed_jobs(self) -> int:
    # ... existing cleanup logic ...
    
    if to_remove:
        # Update control document
        self.control_ref.update({...})
        
        # ✅ NEW: Update job documents
        firestore_client = get_firestore_client()
        for job_id in to_remove:
            job_ref = firestore_client.collection('pipeline_jobs').document(job_id)
            job_ref.update({
                "status": "FAILED",  # or keep QUEUED but update progress
                "progress": "任务已超时或被清理",
                "updated_at": SERVER_TIMESTAMP,
            })
```

### 方案 2: 定期清理过期的排队信息

添加一个定期任务，清理状态为 `QUEUED` 但不在队列中的任务：

```python
def cleanup_stale_queued_jobs(self):
    """Clean up jobs that are QUEUED but not in the queue."""
    control_snapshot = self.control_ref.get()
    if not control_snapshot.exists:
        return
    
    data = control_snapshot.to_dict() or {}
    queue = set(data.get("queue", []))
    running_job_ids = set(data.get("running_job_ids", []))
    
    # Find QUEUED jobs not in queue or running
    firestore_client = get_firestore_client()
    queued_jobs = firestore_client.collection('pipeline_jobs').where('status', '==', 'QUEUED').stream()
    
    for doc in queued_jobs:
        job_id = doc.id
        if job_id not in queue and job_id not in running_job_ids:
            # Update progress
            doc.reference.update({
                "progress": "排队状态已过期，请重新触发",
                "updated_at": SERVER_TIMESTAMP,
            })
```

### 方案 3: 在 `acquire_job_slot` 时检查并更新

在 `acquire_job_slot` 中，如果任务不在队列中但状态是 `QUEUED`，更新 `progress`：

```python
if job_id not in queue and job_id not in running_job_ids:
    # Task is QUEUED but not in queue, update progress
    firestore_client = get_firestore_client()
    job_ref = firestore_client.collection('pipeline_jobs').document(job_id)
    job_ref.update({
        "progress": "排队状态已过期，请重新触发",
        "updated_at": SERVER_TIMESTAMP,
    })
```

## 推荐方案

**采用方案 1 + 方案 3**：

1. **方案 1**: 清理时更新任务文档，确保清理的任务有正确的状态
2. **方案 3**: 在 `acquire_job_slot` 时检查并更新，处理遗留的过期状态

这样可以：
- ✅ 清理时立即更新状态
- ✅ 处理遗留的过期状态
- ✅ 确保前端显示正确的信息

## 影响范围

### 当前影响

- **用户体验**: 前端显示错误的排队位置
- **监控**: 无法准确判断任务的真实状态
- **调试**: 需要检查并发控制文档才能确认真实状态

### 潜在影响

- 如果多个任务都有这个问题，会导致大量混乱的显示
- 用户可能认为任务在排队，但实际上已经被清理

## 修复优先级

**优先级**: 中（不影响功能，但影响用户体验和监控）

**建议**: 尽快修复，确保状态一致性


