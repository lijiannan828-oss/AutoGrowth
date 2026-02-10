# 配对问题修复报告

## 问题描述

压制任务无法手动触发，提示"找不到有效配对"。日志显示：
```
❌ Worker 执行失败：未在 GCS 中找到可压制的 mp4/srt 配对
```

## 诊断结果

使用诊断脚本 `diagnose_pairing_issue.py` 检查后发现两个问题：

### 问题 1: 视频文件无法识别

**根本原因：** 视频文件扩展名是 `.mp4의 사본`（韩语，意思是"mp4的副本"），而不是 `.mp4`。

**文件示例：**
- `episodes/final/[k29]runawayprincessecretvacation_episode000.mp4의 사본`
- `episodes/final/[k29]runawayprincessecretvacation_episode001.mp4의 사본`

**原因：** 文件在 Google Drive 中被复制时，系统自动添加了"의 사본"后缀。

**修复前：**
```python
if lower.endswith(".mp4"):  # ❌ 无法识别 .mp4의 사본
```

**修复后：**
```python
# 检查文件名是否包含 .mp4，且后面没有其他扩展名
if ".mp4" in filename:
    mp4_idx = filename.find(".mp4")
    if mp4_idx >= 0:
        after_mp4 = filename[mp4_idx + 4:]
        if not after_mp4 or "." not in after_mp4[:20]:
            is_video = True  # ✅ 识别 .mp4의 사본 为视频文件
```

### 问题 2: 集数提取错误

**根本原因：** `extract_episode` 函数使用 `EPISODE_REGEX.search()` 只返回第一个匹配，而文件名 `[k29]runawayprincessecretvacation_episode000` 中有两个数字：
1. `29` 来自 `[k29]`（文件名前缀）
2. `000` 来自 `episode000`（实际集数）

函数错误地返回了 `29` 而不是 `000`。

**修复前：**
```python
def extract_episode(source: str) -> str | None:
    filename = Path(source).stem
    match = EPISODE_REGEX.search(filename)  # ❌ 返回第一个匹配（29）
    if not match:
        return None
    return f"{int(match.group(1)):03d}"  # 返回 EP029
```

**修复后：**
```python
def extract_episode(source: str) -> str | None:
    filename = Path(source).stem
    
    # 优先匹配 "episode" 后面的数字
    episode_pattern = re.compile(r"episode[-_\s]*(\d{1,3})", re.IGNORECASE)
    match = episode_pattern.search(filename)  # ✅ 匹配 episode000 -> 000
    if match:
        return f"{int(match.group(1)):03d}"  # 返回 EP000
    
    # 回退到通用模式
    match = EPISODE_REGEX.search(filename)
    if not match:
        return None
    return f"{int(match.group(1)):03d}"
```

## 修复验证

### 修复前
- 视频文件: 0 个
- 字幕文件: 540 个
- 成功配对: 0 个

### 修复后
- 视频文件: 54 个 ✅
- 字幕文件: 540 个 ✅
- 成功配对: 540 个 ✅

### 测试用例

**视频文件识别：**
```
✅ [k29]runawayprincessecretvacation_episode000.mp4의 사본 -> 识别为视频
✅ [k29]runawayprincessecretvacation_episode001.mp4 -> 识别为视频
❌ test.mp4.backup -> 不识别为视频（有另一个扩展名）
```

**集数提取：**
```
✅ [k29]runawayprincessecretvacation_episode000.mp4의 사본 -> EP000
✅ [k29]runawayprincessecretvacation_episode001.mp4의 사본 -> EP001
✅ [k29]runawayprincessecretvacation_episode053.mp4의 사본 -> EP053
```

## 修复的文件

1. `backend/app/workers/process/main.py`
   - 修复 `_register_media_blob` 方法：识别包含 `.mp4` 的文件（如 `.mp4의 사본`）
   - 修复 `extract_episode` 函数：优先匹配 `episode` 后面的数字

2. `backend/scripts/diagnose_pairing_issue.py`
   - 更新诊断脚本以使用修复后的逻辑

## 影响范围

### 受影响的情况
- 文件名包含 `.mp4의 사본` 或类似后缀的视频文件
- 文件名包含其他数字前缀（如 `[k29]`）的视频文件

### 不受影响的情况
- 标准 `.mp4` 扩展名的视频文件
- 文件名格式为 `ep001.mp4` 或 `episode_002.mp4` 的文件

## 部署步骤

1. **部署修复后的代码**
   ```bash
   git push origin main  # 触发 CI/CD
   ```

2. **等待 CI/CD 完成**
   - 确认 `drama-processor-job` 已更新

3. **验证修复**
   - 手动触发一个压制任务
   - 确认能够找到配对并开始处理
   - 检查 process job 日志，确认配对成功

## 相关文件

- `backend/app/workers/process/main.py` - 配对逻辑实现（已修复）
- `backend/scripts/diagnose_pairing_issue.py` - 诊断脚本
- `backend/scripts/PAIRING_FIX_REPORT.md` - 本报告

## 总结

✅ **问题已修复**：
1. 视频文件识别逻辑现在可以识别包含 `.mp4` 的文件（如 `.mp4의 사본`）
2. 集数提取逻辑现在优先匹配 `episode` 后面的数字，避免被文件名中的其他数字干扰

✅ **测试通过**：诊断脚本验证了修复后的逻辑能够正确识别 54 个视频文件并创建 540 个配对。

⚠️ **待部署**：需要在生产环境部署修复后的代码。

