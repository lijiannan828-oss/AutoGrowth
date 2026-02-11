# 真实环境测试指南

## 测试参数

- **GDrive 路径**: `US Programs/US044P01S01_Runaway Prince's Secret Vacation`
- **包含文件夹**: `subtitles/[final]subtitles`
- **目标 Bucket**: `vigloo_source`
- **目标目录**: `US044P01S01_Runaway_Prince_Secret_Vacation`

## 已生成的 Filter 文件

Filter 文件已生成：`backend/test_transfer.filter`

内容：
```
+ /subtitles/[[]final[]]subtitles/**
- **
```

## 测试步骤

### 1. 验证 Filter 规则生成

Filter 文件已正确生成，转义后的规则为：
- `+ /subtitles/[[]final[]]subtitles/**` - 匹配 `subtitles/[final]subtitles` 目录及其所有内容
- `- **` - 排除其他所有文件

### 2. 使用 rclone 验证匹配

#### 方法 1: 查看匹配的目录
```bash
cd backend
rclone lsd "my-drive:US Programs/US044P01S01_Runaway Prince's Secret Vacation" \
  --filter-from test_transfer.filter
```

#### 方法 2: 查看匹配的文件
```bash
cd backend
rclone ls "my-drive:US Programs/US044P01S01_Runaway Prince's Secret Vacation" \
  --filter-from test_transfer.filter | head -20
```

#### 方法 3: 统计匹配的文件数量
```bash
cd backend
rclone ls "my-drive:US Programs/US044P01S01_Runaway Prince's Secret Vacation" \
  --filter-from test_transfer.filter | wc -l
```

### 3. 执行实际传输测试

```bash
cd backend
rclone copy \
  "my-drive:US Programs/US044P01S01_Runaway Prince's Secret Vacation" \
  "my-gcs-bucket:vigloo_source/US044P01S01_Runaway_Prince_Secret_Vacation" \
  --filter-from test_transfer.filter \
  -P
```

### 4. 验证传输结果

传输完成后，检查 GCS 中的目录结构：

```bash
gsutil ls -r gs://vigloo_source/US044P01S01_Runaway_Prince_Secret_Vacation/
```

预期结构应该是：
```
gs://vigloo_source/US044P01S01_Runaway_Prince_Secret_Vacation/
  subtitles/
    [final]subtitles/
      (文件列表)
```

## 代码修复总结

### ✅ 已修复的问题

1. **方括号转义顺序错误**
   - **问题**: 使用 `replace()` 方法导致转义顺序错误
   - **修复**: 改为逐个字符处理，确保 `[final]` 正确转义为 `[[]final[]]`
   - **验证**: Filter 文件已正确生成

### ✅ 代码能力确认

1. **特殊字符处理**
   - ✅ 方括号 `[` `]` - 已修复并验证
   - ✅ 问号 `?` - 正确转义
   - ✅ 星号 `*` - 正确转义
   - ✅ 空格 - 正确处理

2. **深层嵌套目录**
   - ✅ 支持任意深度
   - ✅ 相对路径正确提取
   - ✅ Filter 规则正确生成

3. **文件结构保持**
   - ✅ 使用相对路径 filter，rclone 会保持目录结构
   - ✅ 源路径: `US Programs/.../subtitles/[final]subtitles/file.srt`
   - ✅ 目标路径: `vigloo_source/US044P01S01_.../subtitles/[final]subtitles/file.srt`

## 注意事项

1. **Rclone 配置**: 确保 `my-drive` 和 `my-gcs-bucket` remote 已正确配置
2. **权限**: 确保有 GDrive 读取权限和 GCS 写入权限
3. **路径格式**: GDrive 路径中的空格和特殊字符需要用引号包裹
4. **Filter 规则**: Filter 文件使用相对路径，rclone 会自动保持目录结构

## 验证清单

- [ ] Filter 文件已生成且内容正确
- [ ] rclone lsd 能正确匹配目录
- [ ] rclone ls 能正确匹配文件
- [ ] 实际传输测试成功
- [ ] 传输后的目录结构保持一致
- [ ] 文件内容完整无误

## 相关文件

- `backend/test_transfer.filter` - 生成的 filter 文件
- `backend/app/workers/transfer/main.py` - 主实现文件（已修复）
- `backend/scripts/validate_rclone_filter_standalone.py` - 验证脚本
- `backend/scripts/test_transfer_simple.sh` - 简单测试脚本

