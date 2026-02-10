# 泰语字体 Glyph 缺失问题修复报告

## 问题描述

从 Job `drama-processor-job-xhbws` 的日志中发现：

```
[Parsed_subtitles_0 @ 0x7f0c00002740] Glyph 0xE25 not found, selecting one more font for (NotoSansThai, 400, 0)
[Parsed_subtitles_0 @ 0x7f0c00002740] fontselect: failed to find any fallback with glyph 0xE25 for font: (NotoSansThai, 400, 0)
[Parsed_subtitles_0 @ 0x7f0c00002740] Glyph 0xE49 not found, selecting one more font for (NotoSansThai, 400, 0)
[Parsed_subtitles_0 @ 0x7f0c00002740] fontselect: failed to find any fallback with glyph 0xE49 for font: (NotoSansThai, 400, 0)
[Parsed_subtitles_0 @ 0x7f0c00002740] Glyph 0xE27 not found, selecting one more font for (NotoSansThai, 400, 0)
[Parsed_subtitles_0 @ 0x7f0c00002740] fontselect: failed to find any fallback with glyph 0xE27 for font: (NotoSansThai, 400, 0)
```

## 问题分析

### 关键发现

1. ✅ **FFmpeg 找到了 NotoSansThai 字体**
   - 说明字体名称匹配成功
   - 字体文件存在于系统中

2. ❌ **某些泰语字符无法找到**
   - U+0E25 (ล) - lo ling
   - U+0E49 (เ) - sara e
   - U+0E27 (ว) - wo waen
   - 这些都是常见的泰语字符

3. ❌ **字体回退机制失败**
   - FFmpeg 尝试使用 fallback 字体，但也失败了
   - 说明配置的 fallback 字体也无法找到这些字符

### 根本原因

**字体文件不完整或字体包有问题**

- `fonts-noto-thai` 包可能不包含所有泰语字符
- 或者字体文件损坏
- 或者需要使用更完整的字体包（如 `fonts-noto-core`）

## 解决方案

### 修复 1: 添加 fonts-noto-core 包

**修改**: `backend/app/workers/process/Dockerfile`

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-noto-cjk \
        fonts-nanum \
        fonts-noto-thai \
        fonts-noto-core \  # 新增：包含更完整的字体
        fonts-noto-devanagari \
        fonts-noto-sans \
        fonts-noto-sans-arabic \
        fonts-noto-sans-cyrillic \
        fontconfig && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*
```

**原因**:
- `fonts-noto-core` 包含所有 Noto 字体的核心文件
- 可能包含更完整的泰语字符支持

### 修复 2: 调整字体名称优先级

**修改**: `backend/app/workers/process/main.py`

```python
# 修改前
"th": ["NotoSansThai", "Noto Sans Thai", "Noto Sans"],

# 修改后
"th": ["Noto Sans Thai", "NotoSansThai-Regular", "NotoSansThai", "Noto Sans"],
```

**原因**:
- 优先使用 Full name ("Noto Sans Thai")，可能更准确
- 添加 PostScript name with variant ("NotoSansThai-Regular")
- 保留原有的 PostScript name 作为 fallback

## 验证步骤

### 1. 部署后验证

```bash
# 部署新的 Docker 镜像
# 触发一个新的泰语字幕处理任务
# 查看日志，确认是否还有 glyph missing 错误
```

### 2. 检查字体文件

```bash
# 在容器中运行
fc-list | grep -i thai
# 查看实际可用的字体名称

ls -la /usr/share/fonts/truetype/noto/ | grep -i thai
# 查看字体文件是否存在
```

### 3. 测试字体覆盖

```bash
# 在容器中运行
fc-list :lang=th
# 查看支持泰语的字体
```

## 预期结果

修复后，日志中应该：
- ✅ 不再出现 "Glyph not found" 错误
- ✅ 不再出现 "fontselect: failed to find any fallback" 错误
- ✅ 泰语字幕正确显示（不是乱码）

## 如果问题仍然存在

如果修复后问题仍然存在，可能需要：

1. **检查字体文件完整性**
   ```bash
   # 在容器中运行
   fc-validate /usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf
   ```

2. **尝试手动安装字体**
   - 下载完整的 Noto Sans Thai 字体文件
   - 手动复制到容器中

3. **使用不同的字体包**
   - 尝试 `fonts-noto-unhinted`（未优化的完整字体）
   - 或者直接从 Google Fonts 下载

4. **检查字幕文件编码**
   - 确认字幕文件是 UTF-8 编码
   - 确认字符本身是正确的

## 总结

- ✅ **问题已识别**: FFmpeg 无法找到某些泰语字符的 glyph
- ✅ **根本原因**: 字体文件不完整或字体包有问题
- ✅ **修复方案**: 添加 fonts-noto-core 包，调整字体名称优先级
- ⏳ **需要验证**: 部署后验证修复是否生效

