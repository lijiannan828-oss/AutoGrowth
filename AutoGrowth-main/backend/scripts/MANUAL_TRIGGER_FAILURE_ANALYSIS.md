# 手动触发任务失败原因分析

## 问题描述

手动触发任务 `VPtMHaYiw61PkiCGniYw` 失败，错误信息：**"未在 GCS 中找到可压制的 mp4/srt 配对"**

## 关键发现

### 1. Service 层 vs Worker 层逻辑不一致

**Service 层** (`trigger_manual_process_job`):
- 使用 `discover_file_pairs()` 搜索整个 `drama_name` 前缀
- 找到了 **440 个文件对**
- 设置了 `total_files: 440`

**Worker 层** (`_build_manual_pairs`):
- 当 `manual_paths` 存在时，使用 `_build_manual_pairs(manual_paths)` 而不是 `discover_file_pairs()`
- `manual_paths` 是 `['episodes', 'subtitles']`
- 搜索路径：
  - `{drama_name}/episodes/` 
  - `{drama_name}/subtitles/`
- **实际文件位置**：
  - `{drama_name}/episodes/final/` ✅
  - `{drama_name}/subtitles/final/` ✅

### 2. 路径不匹配导致找不到文件

**问题根源**:
- `_build_manual_pairs` 搜索 `episodes/` 和 `subtitles/` 目录
- 但实际文件在 `episodes/final/` 和 `subtitles/final/` 子目录下
- 因此找不到任何文件对

### 3. 代码逻辑

```python
# Worker 代码 (main.py:351-355)
elif manual_paths:
    # Manual jobs: For now, keep existing logic for manual_paths
    # TODO: Consider refactoring manual_paths to use discovery service
    # Note: manual_paths are specific paths, not full drama discovery
    all_pairs = self._build_manual_pairs(manual_paths)
else:
    # Standard jobs: Use shared discovery service
    file_pairs = discover_file_pairs(...)
```

**问题**: 
- 手动触发任务使用了不同的文件发现逻辑
- `_build_manual_pairs` 不支持递归搜索子目录
- 导致路径不匹配时找不到文件

## 失败原因总结

### ❌ 不是 OOM 问题

**证据**:
1. 执行状态：50 个任务失败，50 个运行中（不是 OOM 导致的全部失败）
2. 错误信息：明确的 "未在 GCS 中找到可压制的 mp4/srt 配对"
3. 没有 `exit=-9` 或其他 OOM 相关错误

### ✅ 是文件发现逻辑问题

**根本原因**:
1. **Service 层和 Worker 层使用了不同的文件发现逻辑**
2. **`_build_manual_pairs` 不支持递归搜索子目录**
3. **`manual_paths` 格式不匹配实际文件结构**

## 解决方案

### 方案 1: 统一使用 `discover_file_pairs`（推荐）

**修改 Worker 代码**，让手动触发任务也使用 `discover_file_pairs`:

```python
# 修改 main.py:351-355
elif manual_paths:
    # Manual jobs: Use shared discovery service for consistency
    # This ensures Service and Worker use the same file discovery logic
    file_pairs = discover_file_pairs(
        drama_name=self.drama_name,
        source_bucket=self.source_bucket,
        allowed_languages=self.allowed_languages if self.allowed_languages else None,
        max_pairs_per_language=self.max_pairs_per_language,
        max_pairs_total=self.max_pairs_total,
    )
    # Convert FilePairInfo to SubtitlePair with Blob objects
    all_pairs = self._convert_file_pairs_to_subtitle_pairs(file_pairs)
else:
    # Standard jobs: Use shared discovery service
    file_pairs = discover_file_pairs(...)
```

**优点**:
- ✅ 统一逻辑，Service 和 Worker 使用相同的文件发现方法
- ✅ 自动支持递归搜索，能找到子目录中的文件
- ✅ 代码更简洁，减少维护成本

### 方案 2: 修改 `manual_paths` 格式

**修改 Service 代码**，传递完整路径：

```python
# 修改 pipeline_process_service.py
# 如果用户传入 ['episodes', 'subtitles']，自动扩展为完整路径
if cleaned_paths:
    expanded_paths = []
    for path in cleaned_paths:
        # 检查是否存在 final 子目录
        # 如果存在，使用完整路径
        expanded_paths.append(f"{path}/final" if needs_expansion else path)
    cleaned_paths = expanded_paths
```

**缺点**:
- ⚠️ 需要硬编码路径结构
- ⚠️ 不够灵活，如果路径结构变化需要修改代码

### 方案 3: 增强 `_build_manual_pairs` 支持递归搜索

**修改 `_build_manual_pairs`**，支持递归搜索：

```python
def _build_manual_pairs(self, manual_paths: List[str]) -> List[SubtitlePair]:
    # 递归搜索所有子目录
    # 使用 list_blobs 的 prefix 参数，它会自动递归搜索
    ...
```

**缺点**:
- ⚠️ 仍然与 Service 层逻辑不一致
- ⚠️ 代码重复，维护成本高

## 推荐方案

**采用方案 1：统一使用 `discover_file_pairs`**

**理由**:
1. ✅ 解决根本问题：统一 Service 和 Worker 的文件发现逻辑
2. ✅ 代码更简洁：减少重复代码
3. ✅ 更可靠：使用经过验证的 `discover_file_pairs` 逻辑
4. ✅ 符合现有架构：标准任务已经使用 `discover_file_pairs`

## 实施步骤

1. **修改 Worker 代码** (`backend/app/workers/process/main.py`):
   - 将手动触发任务的文件发现逻辑改为使用 `discover_file_pairs`
   - 移除对 `_build_manual_pairs` 的依赖（或保留作为备用）

2. **测试验证**:
   - 手动触发一个任务，验证能找到文件对
   - 确认任务能正常执行

3. **部署**:
   - 提交代码并部署
   - 监控任务执行情况

## 关于并发控制

### ✅ 并发控制正常工作

**证据**:
1. 自动触发任务正确获得了 slot
2. 手动触发任务虽然启动了，但很快失败并被清理
3. 两个任务没有同时运行（手动触发任务失败后，自动触发任务才启动）

**结论**: 并发控制逻辑正常，失败不是由于并发控制问题导致的。


