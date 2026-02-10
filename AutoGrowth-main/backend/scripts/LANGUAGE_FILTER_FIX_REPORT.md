# 语言筛选功能修复报告

## 问题描述

用户在前端页面选择单一语种（例如只选择了泰语 `th`）时，触发的压制任务却执行了所有字幕的压制，而不是只压制选中的语种。

**Job ID**: `drama-processor-job-rnfsf`

## 问题诊断

### 1. 前端请求流程

前端 `handleManualProcess` 函数：
```typescript
const handleManualProcess = async () => {
  // ...
  const filePaths = pendingSelectedNodes
    .map((node) => {
      if (!node?.path) return "";
      return node.path.startsWith(prefix) ? node.path.slice(prefix.length) : node.path;
    })
    .filter((path) => !!path);
  
  await manualProcessMutation.mutateAsync({
    drama_name: selectedPendingDrama,
    file_paths: filePaths,  // 例如: ["subtitles/final/th_translated/ep001.srt", ...]
  });
};
```

**前端发送的数据**:
- `drama_name`: `"KR000P05S01_로맨틱아일랜드"`
- `file_paths`: `["subtitles/final/th_translated/ep001.srt", "subtitles/final/th_translated/ep002.srt", ...]`

### 2. 后端处理流程

**问题所在**: `backend/app/services/pipeline_process_service.py` 的 `trigger_manual_process_job` 方法：

```python
def trigger_manual_process_job(
    self,
    drama_name: str,
    file_paths: List[str],
    current_user: AuthenticatedUser | None = None,
) -> str:
    cleaned_paths = [path.strip().lstrip("/") for path in file_paths if path and path.strip()]
    # ...
    doc_body = {
        "drama_name": drama_name.strip(),
        "manual_file_paths": cleaned_paths,
        # ❌ 缺少 process_languages 字段
        # ...
    }
```

**问题**:
1. ❌ 后端只保存了 `file_paths`，但没有从路径中提取语言信息
2. ❌ 没有设置 `process_languages` 字段
3. ❌ Worker 读取 `process_languages` 为空，所以 `allowed_languages` 为空
4. ❌ `discover_file_pairs` 中的语言过滤逻辑：`if allowed and lang_key not in allowed: continue`，当 `allowed` 为空时，不会过滤任何语言

### 3. Worker 处理流程

Worker (`backend/app/workers/process/main.py`):
```python
raw_languages = self.job_data.get("process_languages") or []
self.allowed_languages = {
    str(lang).strip().lower() for lang in raw_languages if str(lang).strip()
}
# ...
file_pairs = discover_file_pairs(
    drama_name=self.drama_name,
    source_bucket=self.source_bucket,
    allowed_languages=self.allowed_languages if self.allowed_languages else None,  # 为空时不过滤
    # ...
)
```

**问题**: 当 `process_languages` 为空时，`allowed_languages` 为空，`discover_file_pairs` 不会过滤任何语言。

## 修复方案

### 修复 1: 从 file_paths 中提取语言代码

**修改文件**: `backend/app/services/pipeline_process_service.py`

**修改内容**:
1. 导入 `detect_language` 函数
2. 从 `file_paths` 中提取语言代码
3. 标准化语言代码（`th_translated` -> `th`）
4. 设置 `process_languages` 字段
5. 在 `discover_file_pairs` 中传递 `allowed_languages` 进行过滤

**修改后的代码**:
```python
from app.services.pipeline_discovery_service import discover_file_pairs, detect_language

def trigger_manual_process_job(
    self,
    drama_name: str,
    file_paths: List[str],
    current_user: AuthenticatedUser | None = None,
) -> str:
    cleaned_paths = [path.strip().lstrip("/") for path in file_paths if path and path.strip()]
    # ...
    
    # Extract language codes from file paths
    # This allows filtering by selected languages when user selects specific language folders
    detected_languages = set()
    for path in cleaned_paths:
        lang = detect_language(path)
        if lang and lang != "unknown":
            # Normalize language key (e.g., "th_translated" -> "th")
            normalized_lang = lang.split("_")[0].split("-")[0].lower()
            detected_languages.add(normalized_lang)
    
    process_languages = sorted(detected_languages) if detected_languages else []
    if process_languages:
        print(f"📋 Extracted languages from file_paths: {process_languages}")
    
    # Discover file pairs with language filtering
    try:
        pairs = discover_file_pairs(
            drama_name=drama_name.strip(),
            source_bucket=settings.pipeline_gcs_source_bucket,
            allowed_languages=detected_languages if detected_languages else None,
        )
        total_files = len(pairs)
        print(f"📊 Discovered {total_files} file pairs for drama={drama_name} (languages: {process_languages or 'all'})")
    except Exception as exc:
        print(f"⚠️ Failed to discover file pairs: {exc}, worker will set total_files")
        total_files = None
    
    doc_body = {
        "drama_name": drama_name.strip(),
        "manual_file_paths": cleaned_paths,
        "process_languages": process_languages,  # ✅ 设置提取的语言
        # ...
    }
```

## 语言提取逻辑

### 示例

**输入路径**:
```
subtitles/final/th_translated/ep001.srt
subtitles/final/th_translated/ep002.srt
subtitles/final/zh_translated/ep001.srt
```

**提取过程**:
1. `detect_language("subtitles/final/th_translated/ep001.srt")` -> `"th_translated"`
2. `normalized_lang = "th_translated".split("_")[0].lower()` -> `"th"`
3. `detected_languages = {"th", "zh"}`

**结果**:
- `process_languages = ["th", "zh"]`
- Worker 只会处理泰语和中文的字幕文件

## 验证步骤

1. **部署修复后的代码**
2. **触发测试任务**:
   - 在前端选择单一语种（例如只选择 `th_translated` 文件夹）
   - 触发压制任务
3. **检查 Job 文档**:
   ```bash
   gcloud firestore documents get pipeline_jobs/{job_id} --format=json
   ```
   - 确认 `process_languages` 字段包含正确的语言代码
4. **检查 Worker 日志**:
   ```bash
   gcloud logging read 'resource.type=cloud_run_job AND textPayload=~"allowed_languages\|Extracted languages"' --limit=20
   ```
   - 确认 Worker 正确读取了 `process_languages`
   - 确认只处理了选中的语言

## 预期效果

- ✅ 前端选择单一语种时，只压制该语种的字幕
- ✅ `process_languages` 字段正确设置
- ✅ Worker 正确过滤文件，只处理选中的语言
- ✅ 不再出现全量压制的问题

## 相关文件

- `backend/app/services/pipeline_process_service.py` - 修复语言提取逻辑
- `backend/app/services/pipeline_discovery_service.py` - 语言检测函数（已存在）
- `backend/app/workers/process/main.py` - Worker 语言过滤逻辑（已存在，无需修改）


