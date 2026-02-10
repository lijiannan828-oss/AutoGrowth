# Scheduler 功能分析报告

## 文件位置

`backend/app/core/scheduler.py`

## 主要功能

### 核心作用

**`scheduler.py` 主要负责定期同步 Program Info 从 Google Sheets 到数据库**。

### 具体逻辑

#### 1. 调度器初始化

**函数**: `init_scheduler()`
- 创建 `AsyncIOScheduler` 实例
- 时区设置为 `Asia/Shanghai`（北京时间）
- 注册定时任务

#### 2. 注册定时任务

**函数**: `_register_jobs()`

**注册的任务**:
- **任务名称**: `sync_program_info`
- **功能**: 从 Google Sheets 同步 Program Info 到数据库
- **执行时间**: 
  - 早上 9:00 (北京时间)
  - 中午 12:00 (北京时间)
  - 晚上 18:00 (北京时间)

**任务逻辑**:
```python
async def sync_program_info():
    """Scheduled task to sync Program Info from Google Sheets to database."""
    sync_service = ProgramSyncService()
    async with get_session() as db:
        result = await sync_service.sync_from_sheets(db)
        # 记录同步结果：created, updated, total
```

#### 3. 生命周期管理

**启动**: `start_scheduler()`
- 在 FastAPI 应用启动时调用
- 启动调度器，开始执行定时任务

**关闭**: `shutdown_scheduler()`
- 在 FastAPI 应用关闭时调用
- 停止调度器，等待任务完成

## 在应用中的使用

### 集成位置

**文件**: `backend/app/main.py`

**启动流程**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start scheduler
    await start_scheduler()
    
    yield
    
    # Shutdown: Stop scheduler
    await shutdown_scheduler()
```

### 执行时机

1. **应用启动时**: 调度器自动启动
2. **定时触发**: 每天 3 次（9:00, 12:00, 18:00 北京时间）
3. **应用关闭时**: 调度器自动停止

## 与视频处理流程的关系

### ⚠️ 重要说明

**`scheduler.py` 与视频处理流程（transfer/process）没有直接关系**:

1. **不同的业务逻辑**:
   - `scheduler.py`: 负责同步 Program Info（节目信息）
   - 视频处理: 由 Eventarc + Relay Service 触发

2. **不同的触发方式**:
   - `scheduler.py`: 定时任务（Cron）
   - 视频处理: 事件驱动（Eventarc）

3. **不同的服务**:
   - `scheduler.py`: 运行在 Cloud Run Service 中
   - 视频处理: 运行在 Cloud Run Jobs 中

### 当前架构

**视频处理流程**:
1. Transfer Job 完成 → 创建 `_PROCESS_NOW.txt`
2. Eventarc 捕获事件 → 发送到 Relay Service
3. Relay Service → 触发 Process Job

**Program Info 同步流程**:
1. Scheduler 定时触发（9:00, 12:00, 18:00）
2. 调用 `ProgramSyncService.sync_from_sheets()`
3. 同步 Google Sheets 数据到数据库

## 总结

### 主要功能

**`scheduler.py` 主要负责**:
- ✅ 定期同步 Program Info 从 Google Sheets 到数据库
- ✅ 每天执行 3 次（9:00, 12:00, 18:00 北京时间）
- ✅ 在 Cloud Run Service 中运行

### 与视频处理的关系

**没有直接关系**:
- ❌ 不负责视频处理任务的调度
- ❌ 不负责并发控制
- ❌ 不负责内存管理

**视频处理由以下组件负责**:
- Eventarc: 事件捕获
- Relay Service: 事件处理和 Job 触发
- Cloud Run Jobs: 实际处理任务

### 如果需要实现并发控制

**应该在以下位置实现**:
1. **Relay Service** (`backend/app/api/v1/relay.py`):
   - 在触发 job 前检查并发数
   - 实现排队逻辑

2. **Cloud Tasks** (推荐):
   - 使用 Cloud Tasks 作为队列
   - 设置并发限制

3. **不在 `scheduler.py` 中**:
   - `scheduler.py` 只负责 Program Info 同步
   - 不应该修改它来实现并发控制


