# Job 错误分析报告

## Job 信息

- **Job ID**: `WoakR4Uo4HaskBtxRvuC`
- **Drama Name**: `KR064P01S01_헤이트 메리지`
- **Total Files**: 500
- **Processed Files**: 1
- **Failed Files**: 170
- **Status**: PROCESSING

## 错误分析

### 🔴 核心问题：FFmpeg 处理失败 (exit=-9)

**错误信息**:
```
RuntimeError: FFmpeg 处理失败 (exit=-9)，请检查日志
```

**错误位置**: `backend/app/workers/process/main.py:913`

### 📊 错误统计

- **总文件数**: 500
- **成功**: 1 (0.2%)
- **失败**: 170 (34%)
- **Task 文档**: 50 个
- **失败模式**: 所有失败都是 `exit=-9`

### 🔍 错误原因分析

#### exit=-9 的含义

**exit=-9** 表示进程被 **SIGKILL** 信号强制终止，常见原因：

1. **Out of Memory (OOM)** ⚠️ **最可能的原因**
   - 进程内存使用超过限制
   - 系统 OOM Killer 强制终止进程
   - Cloud Run 容器内存不足

2. **资源限制**
   - CPU 使用率过高
   - 磁盘空间不足
   - 文件描述符耗尽

3. **系统级问题**
   - 容器被强制终止
   - 超时终止

#### 为什么会出现 OOM？

**当前配置**:
- Cloud Run Job: `--memory=4Gi`, `--cpu=2`
- 每个 Task 处理 5 个文件（根据 sharding 逻辑）
- FFmpeg 参数: `threads=min(cpu_count, 4)`, `preset=veryfast`

**可能原因**:

1. **视频文件过大**
   - `.mov` 文件可能很大
   - 处理高分辨率视频需要更多内存
   - FFmpeg 在处理时需要将视频加载到内存

2. **并发处理**
   - 虽然每个 Task 串行处理，但 FFmpeg 内部可能使用多线程
   - 多个文件同时处理可能导致内存累积

3. **临时文件**
   - FFmpeg 处理时创建临时文件
   - `/tmp` 目录可能空间不足
   - 临时文件未及时清理

4. **内存泄漏**
   - FFmpeg 进程可能泄漏内存
   - Python 进程内存未及时释放

### 📋 失败文件模式

**观察到的失败模式**:
- 大部分失败集中在 `ar_translated`, `es_translated`, `id_translated` 等翻译版本
- 原始语言版本（如 `ko`）也有失败
- 失败是随机的，不是特定文件

**失败示例**:
- `ar_translated/ep001.mp4`
- `es_translated/ep001.mp4`
- `id_translated/ep001.mp4`
- `zh-Hans_translated/ep002.mp4`

### 🔧 解决方案

#### 方案 1: 增加内存限制 ⚠️ **短期方案**

**修改 Cloud Run Job 配置**:
```yaml
--memory=8Gi  # 从 4Gi 增加到 8Gi
```

**优点**:
- 快速实施
- 可能解决 OOM 问题

**缺点**:
- 增加成本
- 不能根本解决问题

#### 方案 2: 减少每个 Task 的文件数 ⚠️ **中期方案**

**修改 sharding 逻辑**:
```python
# 当前: task_count = min(ceil(total_files / 3), 100)
# 修改为: task_count = min(ceil(total_files / 1), 100)  # 每个 Task 只处理 1 个文件
```

**优点**:
- 减少内存压力
- 更好的资源隔离

**缺点**:
- 增加 Task 数量
- 可能增加成本

#### 方案 3: 优化 FFmpeg 参数 ⚠️ **长期方案**

**降低内存使用**:
```python
# 减少线程数
threads = min(cpu_count, 2)  # 从 4 改为 2

# 使用更快的 preset（但可能降低质量）
preset = "ultrafast"  # 从 "veryfast" 改为 "ultrafast"

# 限制内存使用
"-max_muxing_queue_size", "1024"
```

**优点**:
- 降低内存使用
- 保持质量

**缺点**:
- 可能降低处理速度
- 需要测试

#### 方案 4: 增加临时文件清理 ⚠️ **立即实施**

**确保及时清理**:
```python
# 在处理每个文件后立即清理
_cleanup_temp_files()
gc.collect()
```

**优点**:
- 立即实施
- 减少内存占用

**缺点**:
- 可能不够解决根本问题

### 🎯 推荐方案

**立即实施**:
1. ✅ 增加临时文件清理频率
2. ✅ 减少每个 Task 的文件数（从 5 个改为 1-2 个）

**短期实施**:
3. ⏳ 增加内存限制（从 4Gi 增加到 8Gi）
4. ⏳ 优化 FFmpeg 参数（减少线程数）

**长期实施**:
5. ⏳ 监控内存使用情况
6. ⏳ 根据实际情况调整参数

## 详细日志分析

### 失败文件列表（部分）

从 Task 文档中可以看到，几乎所有 Task 都有失败：

- Task 1: 4/5 失败
- Task 2: 4/5 失败
- Task 3: 3/5 失败
- Task 14: 4/5 失败
- Task 15: 5/5 失败（全部失败）
- Task 17: 4/5 失败
- ...

### 失败模式

1. **随机失败**: 不是特定文件或特定语言
2. **高失败率**: 约 34% 的文件失败
3. **统一错误**: 所有失败都是 `exit=-9`

## 下一步行动

1. **立即检查**:
   - 查看 Cloud Run Job 的内存使用情况
   - 检查是否有 OOM 日志

2. **短期修复**:
   - 增加内存限制
   - 减少每个 Task 的文件数

3. **长期优化**:
   - 优化 FFmpeg 参数
   - 监控内存使用
   - 根据实际情况调整

## 相关文件

- `backend/app/workers/process/main.py` - Worker 代码
- `.github/workflows/backend-deploy.yaml` - 部署配置
- `backend/scripts/JOB_ERROR_ANALYSIS_REPORT.md` - 本报告


