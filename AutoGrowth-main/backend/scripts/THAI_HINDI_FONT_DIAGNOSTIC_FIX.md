# 泰语和印地语字体乱码诊断性修复

## 📋 问题描述

泰语 (th) 和印地语 (hi) 字幕在压制后出现乱码（方框），即使 Dockerfile 已安装 `fonts-noto`，问题仍未解决。可能是字体名称匹配失败或缓存问题。

## 🛠️ 修复方案

### 1. 增加字体诊断日志

在 `DramaProcessWorker.__init__` 中增加了 `_diagnose_fonts()` 方法：

- 执行 `fc-list :lang=th` 和 `fc-list :lang=hi`
- 将输出结果打印到日志
- 提取并显示字体 Family Names（去重后）
- 目的：在 Cloud Logging 中明确看到系统里泰语/印地语字体的真实 Family Name

**实现位置**: `DramaProcessWorker._diagnose_fonts()`

**日志输出示例**:
```
🔍 开始字体诊断...
📋 系统可用的 TH 字体 (共 15 个):
   1. /usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf: Noto Sans Thai:style=Regular
   2. ...
📝 TH 字体 Family Names (去重后):
   - Noto Sans Thai
   - NotoSansThai
   ...
✅ 字体诊断完成
```

### 2. 扩展字体匹配列表 (Fuzzy Match)

修改了 `LANGUAGE_FONT_PREFERENCES` 字典，为 `th` 和 `hi` 增加了多种变体：

**泰语 (th)**:
```python
"th": [
    "NotoSansThai",  # No space variant (PostScript name)
    "Noto Sans Thai",  # With space (full name)
    "Noto Sans Thai UI",  # UI variant
    "NotoSansThai-Regular",  # Regular variant
    "NotoSansThai",  # Base name
    "Noto Sans",  # Fallback
],
```

**印地语 (hi)**:
```python
"hi": [
    "NotoSansDevanagari",  # No space variant (PostScript name)
    "Noto Sans Devanagari",  # With space (full name)
    "Noto Sans Devanagari UI",  # UI variant
    "NotoSansDevanagari-Regular",  # Regular variant
    "Noto Sans",  # Fallback
],
```

### 3. 优化样式构建逻辑

修改了 `build_subtitle_style` 函数，增加了字体验证和 fallback 机制：

#### 3.1 新增 `_check_font_available()` 函数

- 使用 `fc-list` 验证字体是否可用
- 如果提供了 `fonts_dir`，检查字体文件是否存在
- 返回字体是否可用的布尔值

#### 3.2 优化 `build_subtitle_style()` 函数

**关键改进**:

1. **字体验证**: 对于复杂脚本（th, hi, ar, ru, ko, ja, zh），验证字体是否可用
2. **Fallback 机制**: 如果字体验证失败，对于泰语和印地语，使用通用字体名 `Sans`
3. **Fontconfig 集成**: 使用 `Sans` 字体名让 Fontconfig 的 fallback 机制生效

**逻辑流程**:
```
1. 获取语言对应的字体偏好列表
2. 如果是复杂脚本（th, hi等）:
   a. 遍历字体偏好列表，验证每个字体是否可用
   b. 如果找到可用字体，使用该字体
   c. 如果所有字体都不可用，且提供了 fonts_dir:
      - 对于 th/hi，使用通用字体 "Sans" 以启用 Fontconfig fallback
3. 构建样式字符串
```

**关键代码**:
```python
# For complex scripts, verify font availability
if lang_key in complex_scripts:
    # Try to verify each preference in order
    for candidate_font in preferences:
        if _check_font_available(candidate_font, fonts_dir):
            font_name = candidate_font
            font_verified = True
            break
    
    # If no font verified, use Fontconfig fallback
    if not font_verified and fonts_dir:
        if lang_key in {"th", "hi"}:
            font_name = "Sans"  # Let Fontconfig handle fallback
```

## 📝 修改的文件

- `backend/app/workers/process/main.py`
  - 扩展 `LANGUAGE_FONT_PREFERENCES` 字典
  - 添加 `_diagnose_fonts()` 方法
  - 添加 `_check_font_available()` 函数
  - 优化 `build_subtitle_style()` 函数

## 🔍 诊断信息

修复后，日志中将包含以下诊断信息：

1. **字体可用性检查**: 显示系统可用的泰语/印地语字体列表
2. **字体 Family Names**: 显示去重后的字体名称（帮助识别正确的字体名格式）
3. **字体验证结果**: 显示是否成功验证到可用字体
4. **Fallback 策略**: 如果使用 Fontconfig fallback，会明确记录

## 🎯 预期效果

1. **诊断信息**: 在 Cloud Logging 中可以看到系统实际可用的字体名称
2. **更好的匹配**: 通过多种字体名称变体，提高字体匹配成功率
3. **Fallback 机制**: 如果直接匹配失败，使用 Fontconfig 的 fallback 机制自动选择合适的字体

## 📋 下一步

1. ✅ 代码修改完成
2. ⏳ 部署到生产环境
3. ⏳ 查看 Cloud Logging 中的字体诊断信息
4. ⏳ 验证泰语和印地语字幕是否正常显示
5. ⏳ 根据诊断信息进一步优化字体匹配逻辑（如需要）

## 🔧 技术细节

### Fontconfig Fallback 机制

当使用 `FontName=Sans` 时，FFmpeg 的 subtitles filter 会：
1. 通过 Fontconfig 查找 "Sans" 字体
2. Fontconfig 会根据语言自动选择合适的字体
3. 对于泰语，Fontconfig 会优先选择支持泰语字符的字体（如 Noto Sans Thai）
4. 对于印地语，Fontconfig 会优先选择支持 Devanagari 脚本的字体（如 Noto Sans Devanagari）

这种方式比硬编码字体名称更灵活，能够自动适应不同的系统配置。

