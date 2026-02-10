# 泰语和印尼语字幕乱码问题修复报告

## 问题描述

用户报告：`KR000P05S01_로맨틱아일랜드` 的泰语（th）和印尼语（id）字幕压制后仍然出现乱码。

## 问题诊断

### 1. 检查部署状态
- ✅ Docker 镜像已更新到 `e7f79f8`
- ✅ Dockerfile 中已安装 `fonts-noto-thai` 和 `fonts-noto-sans`
- ✅ `LANGUAGE_FONT_PREFERENCES` 中已配置 `th` 和 `id`

### 2. 检查日志
- ✅ FFmpeg 命令正确使用了 `FontName=Noto Sans Thai`
- ✅ `fontsdir=/usr/share/fonts` 已设置
- ❌ **问题**: libass 可能无法找到字体

### 3. 根本原因

**问题 1: 字体名称格式不匹配**
- libass/FFmpeg 的 subtitles filter 可能期望 PostScript 字体名称格式（无空格）
- 代码中使用的是 `"Noto Sans Thai"`（带空格）
- 实际系统中可能注册为 `"NotoSansThai"`（无空格）

**问题 2: 字体缓存未刷新**
- Dockerfile 中安装了字体包，但没有刷新字体缓存
- 新安装的字体需要运行 `fc-cache -fv` 才能被系统识别

## 修复方案

### 修复 1: Dockerfile 添加字体缓存刷新

**修改前**:
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
        fonts-noto-sans-cyrillic && \
    rm -rf /var/lib/apt/lists/*
```

**修改后**:
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

**效果**:
- 添加 `fontconfig` 包（确保 fc-cache 命令可用）
- 运行 `fc-cache -fv` 刷新字体缓存
- 确保新安装的字体被系统识别

### 修复 2: 添加字体名称变体（PostScript 格式）

**修改前**:
```python
# Southeast Asian languages
"th": ["Noto Sans Thai", "Noto Sans"],
"hi": ["Noto Sans Devanagari", "Noto Sans"],
"id": ["Noto Sans", "Arial"],
"vi": ["Noto Sans", "Arial"],
```

**修改后**:
```python
# Southeast Asian languages
"th": ["NotoSansThai", "Noto Sans Thai", "Noto Sans"],
"hi": ["NotoSansDevanagari", "Noto Sans Devanagari", "Noto Sans"],
"id": ["NotoSans", "Noto Sans", "Arial"],
"vi": ["NotoSans", "Noto Sans", "Arial"],
```

**效果**:
- 优先使用 PostScript 格式的字体名称（无空格）
- 如果 PostScript 格式找不到，回退到带空格的格式
- 最后回退到通用字体

## 技术细节

### libass 字体查找机制

libass（FFmpeg subtitles filter 使用的库）查找字体的顺序：
1. 使用 `FontName` 指定的字体名称
2. 在 `fontsdir` 指定的目录中查找
3. 使用 fontconfig 查找系统字体
4. 如果找不到，使用默认字体或回退字体

### PostScript 字体名称格式

PostScript 字体名称通常：
- 无空格
- 驼峰命名（CamelCase）
- 例如：`NotoSansThai` 而不是 `Noto Sans Thai`

### 字体缓存刷新

`fc-cache -fv` 命令：
- `-f`: 强制刷新
- `-v`: 详细输出
- 重新扫描字体目录并更新字体缓存
- 确保新安装的字体被 fontconfig 识别

## 验证步骤

部署后，验证修复是否生效：

1. **检查字体缓存刷新**:
   ```bash
   # 在容器中运行
   fc-list | grep -i "noto.*thai\|noto.*sans"
   ```

2. **检查字体名称匹配**:
   ```bash
   # 检查日志中的字体选择
   gcloud logging read 'resource.type=cloud_run_job AND textPayload=~"使用字体.*th"' --limit=10
   ```

3. **测试压制任务**:
   - 触发一个包含泰语或印尼语的压制任务
   - 检查压制后的视频字幕是否正常显示

## 预期效果

- ✅ 泰语字幕使用 `NotoSansThai` 或 `Noto Sans Thai` 字体
- ✅ 印尼语字幕使用 `NotoSans` 或 `Noto Sans` 字体
- ✅ 字体被正确识别和加载
- ✅ 字幕正常显示，不再出现乱码

## 相关文件

- `backend/app/workers/process/Dockerfile` - 字体安装和缓存刷新
- `backend/app/workers/process/main.py` - 字体名称配置


