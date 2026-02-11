# Relay Service 逻辑说明

## 用户需求

**所有传输成功的 job 就可以自动触发压制**

## 当前实现逻辑

### 1. 触发流程

```
Eventarc 事件 (_PROCESS_NOW.txt 创建)
  ↓
Relay Service 接收事件
  ↓
提取 drama_name
  ↓
调用 _find_latest_ready_job(drama_name)
  ↓
找到 ready job → 触发压制
找不到 → 忽略
```

### 2. `_find_latest_ready_job` 的筛选条件

```python
def _find_latest_ready_job(drama_name: str):
    # 查询该 drama_name 的所有 jobs
    query = collection.where("drama_name", "==", drama_name)
    
    # 筛选条件：
    candidates = []
    for job in query.stream():
        if job.transfer_completed == True:  # ✅ 传输已完成
            if job.stage == 1 or job.stage is None:  # ✅ 是传输阶段
                candidates.append(job)
    
    # 按 updated_at 排序，返回最新的一个
    candidates.sort(key=lambda x: x.updated_at, reverse=True)
    return candidates[0]  # ⚠️ 只返回最新的一个
```

### 3. Transfer Worker 完成时的字段设置

从 `backend/app/workers/transfer/main.py` 的 `_finalize_success` 函数：

```python
doc_ref.update({
    "status": "COMPLETE",           # ✅ 状态为完成
    "stage": 1,                      # ✅ 阶段为 1（传输阶段）
    "transfer_completed": True,      # ✅ 传输完成标记
    "updated_at": SERVER_TIMESTAMP,  # ✅ 更新时间
})
```

## 逻辑分析

### ✅ 符合需求的部分

1. **筛选条件正确**：
   - `transfer_completed == True` ✅ 确保传输已完成
   - `stage == 1` ✅ 确保是传输任务（不是压制任务）

2. **自动触发机制**：
   - Eventarc 监听 `_PROCESS_NOW.txt` 创建
   - Relay Service 自动查找 ready job
   - 自动触发压制任务

### ⚠️ 需要注意的部分

**只返回最新的一个 job**：

- 如果同一个 `drama_name` 有多个传输任务都完成了，只会选择**最新的一个**（按 `updated_at` 排序）
- 例如：
  - Job A: `drama_name="KR071P01S01_타임 리프 조선"`, `updated_at=2025-11-22 15:00:00`
  - Job B: `drama_name="KR071P01S01_타임 리프 조선"`, `updated_at=2025-11-22 16:00:00`
  - 结果：只返回 Job B，Job A 不会被触发

### 业务场景分析

**场景 1：正常情况（一个 drama 一个传输任务）**
- ✅ 符合需求：传输完成后自动触发压制

**场景 2：重新传输（同一个 drama 传输了两次）**
- ⚠️ 行为：只触发最新的传输任务
- 问题：如果第一次传输已经触发过压制，第二次传输会再次触发压制
- 影响：可能导致重复压制

**场景 3：多个不同的传输任务（不同的 drama_name）**
- ✅ 符合需求：每个 drama 独立处理

## 潜在问题

### 问题 1：重复触发压制

如果同一个 drama 传输了多次，每次都会触发新的压制任务。

**解决方案选项**：
1. **检查是否已有压制任务**：在触发前检查是否已有 `stage=2` 的 job
2. **标记已触发**：在传输 job 中添加 `processing_triggered=True` 标记
3. **保持现状**：允许重新压制（如果用户需要）

### 问题 2：只选择最新的

如果用户希望**所有**传输成功的 job 都触发压制，当前逻辑不符合。

**解决方案**：
- 修改逻辑，返回所有符合条件的 jobs
- 为每个 job 触发独立的压制任务

## 建议

### 当前逻辑评估

**是否符合"所有传输成功的 job 就可以自动触发压制"？**

- ✅ **部分符合**：所有传输成功的 job **都可以**被触发（满足筛选条件）
- ⚠️ **不完全符合**：但**只触发最新的一个**（不是所有）

### 推荐方案

**方案 A：保持现状（推荐）**
- 理由：通常一个 drama 只需要压制一次
- 行为：选择最新的传输任务触发压制
- 适用：正常业务流程

**方案 B：检查是否已触发**
- 添加检查：如果已有 `stage=2` 的 job，不重复触发
- 适用：避免重复压制

**方案 C：触发所有**
- 修改逻辑：返回所有符合条件的 jobs，全部触发
- 适用：需要多次压制的场景

## 代码位置

- **Relay Service**: `backend/app/api/v1/relay.py`
- **Transfer Worker**: `backend/app/workers/transfer/main.py`
- **筛选逻辑**: `_find_latest_ready_job()` 函数


