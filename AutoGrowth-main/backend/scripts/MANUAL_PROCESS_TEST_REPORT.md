# 压制字幕功能代码审查与测试报告

## 一、代码逻辑审查

### 1. 任务独立性 ✅

**代码位置**: `backend/app/services/pipeline_process_service.py:100-136`

**关键逻辑**:
- `trigger_manual_process_job` 创建任务时设置：
  - `transfer_completed: True` - 标记传输已完成
  - `stage: 1` - 直接进入压制阶段
  - `type: "manual"` - 标记为手动任务
- 任务直接触发 `process_worker`，不依赖传输流程

**结论**: ✅ 任务独立，不依赖前置传输流程

### 2. 存储规范 ✅

**代码位置**: `backend/app/workers/process/main.py:620`

**输出路径格式**:
```python
dest_path = f"{self.drama_name}/{safe_lang}/ep{pair.episode}.mp4"
```

**存储位置**: `vigloo_processed` bucket

**命名规则**:
- 格式: `{drama_name}/{language}/ep{episode}.mp4`
- 示例: `KR051P07S01_김대표의 엽기적인 부인/en/ep000.mp4`

**结论**: ✅ 符合 vigloo_processed 存储规范

### 3. 覆盖逻辑 ✅

**代码位置**: `backend/app/workers/process/main.py:621-622`

**关键代码**:
```python
output_blob = processed_bucket.blob(dest_path)
output_blob.upload_from_filename(output_path)
```

**行为**: `upload_from_filename` 会直接覆盖已存在的文件

**结论**: ✅ 新压制的视频会覆盖旧视频

### 4. 文件配对逻辑 ✅

**代码位置**: `backend/app/workers/process/main.py:459-484`

**配对逻辑**:
1. 遍历 `manual_file_paths`
2. 如果是目录，添加 "/" 后缀，列出所有文件
3. 如果是文件，直接使用
4. 调用 `_register_media_blob` 注册 mp4 和 srt 文件
5. 调用 `_finalize_pairs` 进行配对（基于 episode 编号和 language）

**配对规则**:
- 从文件名提取 episode 编号（如 `episode000` → `000`）
- 从路径检测 language（如 `Subtitles/en/` → `en`）
- 相同 episode 和 language 的 mp4 和 srt 配对

**结论**: ✅ 配对逻辑正确

## 二、潜在问题

### 问题 1: 前端路径处理

**代码位置**: `frontend/src/app/pipeline/library/page.tsx:533-539`

**当前逻辑**:
```typescript
const prefix = `${selectedPendingDrama}/`;
const filePaths = pendingSelectedNodes
  .map((node) => {
    if (!node?.path) return "";
    return node.path.startsWith(prefix) ? node.path.slice(prefix.length) : node.path;
  })
```

**问题**: 
- 如果 `node.path` 是完整路径（如 `KR051P07S01_김대표의 엽기적인 부인/Episodes/episode000.mp4`），会被截断为 `Episodes/episode000.mp4`
- 后端 `_build_manual_pairs` 会拼接 `drama_name`，所以应该能正常工作
- 但如果选择的是子目录（如 `Episodes`），后端会正确列出所有文件

**结论**: ⚠️ 需要验证路径处理是否正确

## 三、测试结果

### 测试步骤
1. ✅ 选择资源 `KR051P07S01_김대표의 엽기적인 부인`
2. ✅ 展开 Episodes 和 Subtitles/en 目录
3. ✅ 勾选 Episodes 文件夹和 Subtitles/en 文件夹（共 99+ 项）
4. ✅ 点击"压制字幕"按钮
5. ⏳ 检查任务监控页面是否显示新任务

### 测试发现
- ✅ 路径显示正确：`gs://vigloo_source/KR051P07S01_김대표의 엽기적인 부인/Episodes`
- ✅ 文件夹选择功能正常：选择文件夹会自动选中所有子文件
- ✅ "压制字幕"按钮可用且未禁用

### 测试结果总结

**代码审查结果**：
1. ✅ **任务独立性**：代码设置 `transfer_completed=True, stage=1`，任务直接进入压制阶段，不依赖传输流程
2. ✅ **存储规范**：输出路径格式为 `{drama_name}/{safe_lang}/ep{episode}.mp4`，符合 vigloo_processed 规范
3. ✅ **覆盖逻辑**：`upload_from_filename()` 会直接覆盖已存在的文件
4. ✅ **文件配对**：后端会自动列出文件夹下的所有文件，并根据 episode 和 language 进行配对

**前端测试结果**：
- ✅ 路径显示正确：完整路径包含一级目录
- ✅ 文件夹选择功能正常：选择文件夹会自动选中所有子文件
- ✅ "压制字幕"按钮可用且未禁用
- ⚠️ **API 调用问题**：点击"压制字幕"按钮后，未发现 API 调用记录，可能的原因：
  1. 后端服务未运行
  2. API 调用被错误处理拦截
  3. 需要检查 `manualProcessMutation` 的成功/失败回调

**待验证**：
- ⏳ 任务是否成功创建并在任务监控页面显示
- ⏳ 任务类型是否为 "manual"
- ⏳ 任务状态是否为 "stage=1, transfer_completed=True"
- ⏳ 任务完成后，输出文件路径是否符合规范
- ⏳ 如果已存在相同文件，是否会被覆盖

**建议**：
1. 检查后端服务是否正在运行
2. 检查 `manualProcessMutation` 的错误处理逻辑
3. 添加成功提示，确认任务创建成功
4. 检查浏览器网络请求，确认 API 调用是否成功

