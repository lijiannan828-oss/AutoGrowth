# 泰语和印地语字幕乱码问题诊断

## 问题描述
压制后的成片中，泰语和印地语字幕显示为乱码。

## 排查步骤

### 1. Google Drive 传输到 GCS 阶段

**检查点**:
- Rclone 传输时是否保持文件编码
- 传输过程中是否有编码转换

**代码位置**: `backend/app/workers/transfer/main.py`
- Rclone 使用二进制模式传输，应该不会改变文件内容
- 但需要确认传输后的文件编码是否正确

### 2. GCS 上的文件解析阶段

**检查点**:
- GCS 上的字幕文件编码是否正确
- 下载时是否保持了原始编码

**代码位置**: `backend/app/workers/process/main.py`
- `download_with_progress` (line 52-68): 使用二进制模式下载 (`"rb"` 和 `"wb"`)
- 应该保持原始文件内容不变

### 3. 压制时 FFmpeg 处理阶段

**检查点**:
- 字幕编码转换是否正确
- FFmpeg 的 subtitles filter 是否支持泰语和印地语
- 字体是否支持泰语和印地语字符

**代码位置**: `backend/app/workers/process/main.py`

#### 3.1 编码转换 (`normalize_subtitle_encoding`, line 149-156)

```python
def normalize_subtitle_encoding(subtitle_path: Path) -> None:
    raw = subtitle_path.read_bytes()
    detection = chardet.detect(raw)
    encoding = (detection.get("encoding") or "utf-8").lower()
    if encoding == "utf-8":
        return
    text = raw.decode(encoding, errors="ignore")  # ⚠️ 问题：errors="ignore" 可能丢失字符
    subtitle_path.write_text(text, encoding="utf-8")
```

**潜在问题**:
1. `chardet` 可能无法准确检测泰语和印地语的编码
2. `errors="ignore"` 会在遇到无法解码的字符时忽略，导致字符丢失
3. 如果源文件是 UTF-8 但包含 BOM，`chardet` 可能检测为其他编码

#### 3.2 字体配置 (`LANGUAGE_FONT_PREFERENCES`, line 168-175)

```python
LANGUAGE_FONT_PREFERENCES: Dict[str, List[str]] = {
    "ko": ["NanumMyeongjo", "Noto Serif CJK KR", "AppleMyungjo", "Batang"],
    "ja": ["Noto Sans CJK JP", "Hiragino Sans", "Yu Gothic", "Noto Sans"],
    "zh": ["Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "Noto Sans"],
    "en": ["Noto Sans", "Helvetica", "Arial"],
    "es": ["Noto Sans", "Helvetica", "Arial"],
    "_default": ["Noto Sans CJK SC", "Noto Sans", "Arial"],
}
```

**问题**: 
- ❌ **没有配置泰语 (`th`) 和印地语 (`hi`) 的字体**
- 会使用 `_default` 字体，可能不支持泰语和印地语字符

#### 3.3 Dockerfile 字体安装

```dockerfile
apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk fonts-nanum
```

**问题**:
- ✅ 安装了 `fonts-noto-cjk` (支持中日韩)
- ❌ **没有安装 `fonts-noto-thai` (泰语) 和 `fonts-noto-devanagari` (印地语)**

## 可能的原因

### 原因 1: 字体不支持（最可能）
- FFmpeg 的 subtitles filter 需要系统字体支持泰语和印地语字符
- 当前 Dockerfile 只安装了中日韩字体，没有安装泰语和印地语字体
- 即使字幕编码正确，字体不支持也会显示为乱码或方块

### 原因 2: 编码检测不准确
- `chardet` 可能无法准确检测泰语和印地语的编码
- 如果检测错误，转换时可能丢失字符

### 原因 3: 编码转换时字符丢失
- `errors="ignore"` 会在遇到无法解码的字符时忽略
- 如果源文件编码检测错误，转换时会丢失字符

## 诊断步骤

1. **检查 GCS 上的原始文件编码**
   ```bash
   gsutil cat gs://vigloo_source/{drama_name}/th_translated/ep001.srt | file -
   gsutil cat gs://vigloo_source/{drama_name}/hi_translated/ep001.srt | file -
   ```

2. **检查压制日志中的字幕预览**
   - 查看日志中 "字幕文件内容预览" 部分
   - 确认下载后的字幕内容是否正确

3. **检查字体支持**
   - 确认 Docker 容器中是否安装了泰语和印地语字体
   - 检查 FFmpeg 是否能找到合适的字体

4. **测试编码转换**
   - 手动测试 `normalize_subtitle_encoding` 函数
   - 确认编码检测和转换是否正确

## 建议的修复方案

1. **安装泰语和印地语字体**
   - 在 Dockerfile 中添加 `fonts-noto-thai` 和 `fonts-noto-devanagari`

2. **改进编码检测**
   - 优先尝试 UTF-8（带或不带 BOM）
   - 改进 `chardet` 的使用方式
   - 使用 `errors="replace"` 而不是 `errors="ignore"`

3. **添加字体配置**
   - 在 `LANGUAGE_FONT_PREFERENCES` 中添加泰语和印地语的字体配置


