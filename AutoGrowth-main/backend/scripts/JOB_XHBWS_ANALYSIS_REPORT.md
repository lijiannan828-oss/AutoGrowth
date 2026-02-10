# Job drama-processor-job-xhbws 分析报告

## Job 信息

- **Cloud Run Job 执行名称**: `drama-processor-job-xhbws`
- **Firestore Job ID**: `JOTGhe9omCEXXwbzdyvx`
- **剧集名称**: `US044P01S01_Runaway Prince's Secret Vacation`
- **状态**: SUCCEEDED ✅
- **处理语言**: ['hi', 'th']
- **文件统计**: 
  - 总文件数: 108
  - 已处理: 108
  - 失败: 0

## 问题 1: 文件配对数量

### 问题
为什么 50 集显示 108 个文件配对？

### 答案 ✅
**不是 50 集，而是 54 集！**

- **54集 × 2个语言 (th_translated, hi_translated) = 108 个配对** ✅
- 每集有 2 个字幕文件（泰语和印地语）
- 所以总共 108 个配对是正确的

### 详细分析
```
按语言统计:
  hi_translated: 54 个配对
  th_translated: 54 个配对

按集数统计:
  ep000-ep053: 每集 2 个配对 (th, hi)
  
总集数: 54
总配对: 108
```

## 问题 2: 泰语乱码

### 问题
用户反馈：泰语还是乱码

### 配置检查 ✅

#### Dockerfile 配置 ✅
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-noto-cjk \
        fonts-nanum \
        fonts-noto-thai \
        fonts-noto-devanagari \
        fonts-noto-sans \
        fonts-noto-sans-arabic \
        fonts-noto-sans-cyrillic \
        fontconfig && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*
```

- ✅ fonts-noto-thai (泰语字体)
- ✅ fonts-noto-devanagari (印地语字体)
- ✅ fonts-noto-sans (通用字体)
- ✅ fontconfig (字体配置工具)
- ✅ fc-cache -fv (刷新字体缓存)

#### main.py 配置 ✅
```python
LANGUAGE_FONT_PREFERENCES: Dict[str, List[str]] = {
    "th": ["NotoSansThai", "Noto Sans Thai", "Noto Sans"],
    "hi": ["NotoSansDevanagari", "Noto Sans Devanagari", "Noto Sans"],
    ...
}
```

- ✅ LANGUAGE_FONT_PREFERENCES 包含泰语配置
- ✅ normalize_language_key("th_translated") = "th" ✅
- ✅ 字体配置应该能正确匹配

#### 字幕编码配置 ✅
- ✅ normalize_subtitle_encoding 函数存在
- ✅ 优先使用 UTF-8
- ✅ 使用 errors="replace" 避免数据丢失
- ✅ 支持多种编码检测

### 可能原因分析 ⚠️

#### 1. 字体名称问题 ⚠️
**问题**: FFmpeg 可能无法找到 `NotoSansThai` 字体

**原因**:
- 配置中使用: `"NotoSansThai"` (PostScript name)
- 但 FFmpeg 可能需要: `"Noto Sans Thai"` (Full name)
- 或者字体文件系统中的实际名称不同

**验证方法**:
```bash
# 在容器中运行
fc-list | grep -i thai
# 查看实际字体名称
```

#### 2. 字体路径问题 ⚠️
**问题**: `fontsdir` 可能指向错误的路径

**当前配置**:
```python
def detect_fonts_dir() -> str | None:
    candidates = [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        ...
    ]
```

**验证方法**:
```bash
# 在容器中运行
ls -la /usr/share/fonts/truetype/noto/
# 查看字体文件是否存在
```

#### 3. 字幕编码问题 ⚠️
**问题**: 字幕文件可能没有正确转换为 UTF-8

**当前配置**:
```python
def normalize_subtitle_encoding(subtitle_path: Path) -> None:
    # 优先使用 UTF-8
    # 使用 errors="replace" 避免数据丢失
    # 支持多种编码检测
```

**验证方法**:
- 检查日志中的编码转换信息
- 检查字幕文件的实际编码

### 需要检查的日志

#### 1. 字体使用日志
在 GCP Console 中查看：
- Cloud Run Jobs -> drama-processor-job -> Executions -> drama-processor-job-xhbws -> Logs
- 搜索关键字: `"使用字体"`, `"NotoSansThai"`, `"fontsdir"`

**期望看到**:
```
🔤 使用字体 NotoSansThai (fontsdir=/usr/share/fonts)
```

#### 2. FFmpeg 错误日志
搜索关键字: `"ffmpeg"`, `"处理失败"`, `"exit="`, `"error"`

**检查**:
- 是否有字体相关的错误
- 是否有字幕编码相关的错误
- FFmpeg 退出码是否为 0

#### 3. 字幕编码日志
搜索关键字: `"字幕编码"`, `"encoding"`, `"UTF-8"`, `"转换为"`

**期望看到**:
```
✅ 字幕 xxx.th.srt 成功转换为 UTF-8 (原编码: xxx)
```

### 建议的修复方案

#### 方案 1: 验证字体名称
```bash
# 在容器中运行
fc-list | grep -i thai
# 查看实际字体名称，更新 LANGUAGE_FONT_PREFERENCES
```

#### 方案 2: 检查字体路径
```bash
# 在容器中运行
ls -la /usr/share/fonts/truetype/noto/ | grep -i thai
# 确认字体文件存在
```

#### 方案 3: 增强日志记录
在 `build_subtitle_style` 和 `normalize_subtitle_encoding` 中添加更详细的日志：
- 记录实际使用的字体名称
- 记录字体文件路径
- 记录编码转换过程

#### 方案 4: 测试字体加载
创建一个测试脚本，在容器中测试字体是否能正确加载：
```python
from fontconfig import FcConfig, FcPattern, FcFontMatch
# 测试字体是否能找到
```

## 总结

### ✅ 已确认
1. ✅ 文件配对数量正确（54集 × 2语言 = 108个配对）
2. ✅ Dockerfile 配置正确（已安装所有必要字体）
3. ✅ main.py 配置正确（字体偏好和编码转换）
4. ✅ Job 执行成功（108个文件全部处理完成）

### ⚠️  需要验证
1. ⚠️  实际使用的字体名称是否正确
2. ⚠️  字体文件是否能被 FFmpeg 找到
3. ⚠️  字幕编码是否正确转换为 UTF-8
4. ⚠️  输出文件中的泰语字幕是否正确显示

### 📝 下一步行动
1. ⏳ 在 GCP Console 中查看详细日志
2. ⏳ 检查输出文件中的泰语字幕
3. ⏳ 如果仍有问题，验证字体名称和路径
4. ⏳ 必要时更新字体配置或增强日志记录

