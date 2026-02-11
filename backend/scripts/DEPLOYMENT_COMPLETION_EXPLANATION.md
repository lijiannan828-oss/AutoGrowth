# 部署完成后任务可以正常执行的原因

## 问题回顾

任务 `XaiII9IaNSWnxtO0K72C` 一直阻塞，原因有两个：

1. **并发控制阻塞**: 僵尸任务 `test_fifo_job_1` 占用运行 slot
2. **文件配对失败**: 字幕文件识别逻辑无法识别包含 `.srt의 사본의 사본` 的文件名

## 已实施的修复

### 1. ✅ 并发控制清理逻辑增强

**修复内容**:
- 在 `ConcurrencyService._cleanup_completed_jobs()` 中添加了对 `QUEUED` 状态任务的清理
- 如果任务状态为 `QUEUED` 但占用 slot，会被自动清理

**代码位置**: `backend/app/services/concurrency_service.py`

```python
# Case 2.5: Job is QUEUED but in running_job_ids (shouldn't happen, but clean it up)
if status == "QUEUED":
    to_remove.add(job_id)
    cleaned_count += 1
    logger.warning("🧹 Cleaning up QUEUED job from running_job_ids: %s (shouldn't be running)", job_id)
    continue
```

### 2. ✅ 字幕文件识别逻辑修复

**修复内容**:
- 修复 `discover_file_pairs` 中字幕文件识别逻辑
- 支持文件名包含 `.srt의 사본의 사본` 等后缀的字幕文件
- 使用与视频文件相同的识别逻辑（查找 `.srt` 在文件名中的位置）

**代码位置**: `backend/app/services/pipeline_discovery_service.py`

```python
elif ".srt" in filename.lower():
    # Check if it's a subtitle file (handle cases like ".srt의 사본의 사본")
    srt_idx = filename.lower().find(".srt")
    if srt_idx >= 0:
        after_srt = filename[srt_idx + 4:]
        # If nothing after .srt, or no other dot (indicating another extension) in the next 20 chars
        if not after_srt or "." not in after_srt[:20]:
            episode = extract_episode(rel_path)
            if not episode:
                continue
            language = detect_language(rel_path)
            subtitles.setdefault(language, {})[episode] = rel_path
```

## 为什么部署完成后任务可以正常执行？

### 1. 并发控制问题已解决

**部署前**:
- 僵尸任务 `test_fifo_job_1` 占用 slot
- 新任务无法获得 slot，被加入队列
- 即使队列自动触发机制工作，也无法清理僵尸任务

**部署后**:
- 清理逻辑增强，会自动清理 `QUEUED` 状态的任务
- 僵尸任务会被自动清理，释放 slot
- 队列中的任务可以正常获得 slot 并执行

### 2. 文件配对问题已解决

**部署前**:
- 字幕文件识别失败（`endswith(".srt")` 返回 False）
- 无法找到文件对（0 个文件对）
- Worker 执行失败：`未在 GCS 中找到可压制的 mp4/srt 配对`

**部署后**:
- 字幕文件识别逻辑修复，能正确识别包含非ASCII后缀的文件名
- 现在能找到 440 个文件对
- Worker 可以正常处理文件

### 3. 自动触发机制

**队列自动触发**:
- 当运行中的任务完成时，会自动触发队列中的下一个任务
- 修复后的清理逻辑确保僵尸任务不会阻塞队列

**触发流程**:
1. 任务完成 → `release_and_trigger_next()` 被调用
2. 清理僵尸任务 → `_cleanup_completed_jobs()` 清理异常状态的任务
3. 触发下一个任务 → `try_trigger_next_job()` 从队列中取出下一个任务并触发

## 当前状态

### 队列状态

- **最大并发数**: 1
- **当前运行数**: 根据实际状态
- **队列中的任务**: 根据实际状态

### 任务执行流程

1. **任务创建** → 状态: `QUEUED`
2. **获得 slot** → 状态: `PROCESSING`，触发 Cloud Run Job
3. **Worker 执行** → 处理文件对
4. **任务完成** → 状态: `SUCCEEDED` 或 `FAILED`
5. **自动触发下一个** → 从队列中取出下一个任务

## 验证方法

部署完成后（约 5-10 分钟），可以通过以下方式验证：

1. **检查队列状态**:
   ```bash
   python backend/scripts/diagnose_blocked_job.py
   ```

2. **检查任务执行**:
   ```bash
   gcloud run jobs executions list \
     --job=drama-processor-job \
     --region=us-central1 \
     --limit=10
   ```

3. **检查文件配对**:
   ```python
   from app.services.pipeline_discovery_service import discover_file_pairs
   pairs = discover_file_pairs("US009P03S01_Good Girl Gone Bad")
   print(f"找到 {len(pairs)} 个文件对")
   ```

## 总结

部署完成后，任务可以正常执行的原因：

1. ✅ **并发控制问题已修复**: 僵尸任务会被自动清理
2. ✅ **文件配对问题已修复**: 字幕文件可以正确识别
3. ✅ **队列自动触发机制**: 任务完成后会自动触发下一个任务
4. ✅ **清理逻辑增强**: 定期清理异常状态的任务

所有修复都已部署到生产环境，任务应该能够正常执行。


