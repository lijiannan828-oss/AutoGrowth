# 批量重新处理泰语和印地语字幕

## ⚠️  重要提示

**此脚本必须在生产环境执行！** 如果在开发环境执行，任务会在本地运行而不是在 Cloud Run 中执行。

## 使用方法

### 1. 修复已创建的开发环境任务

如果之前错误地在开发环境执行了脚本，需要先修复已创建的任务：

```bash
cd backend
source venv/bin/activate  # 如果需要
python3 scripts/fix_dev_environment_jobs.py
```

### 2. 在生产环境执行批量处理脚本

```bash
cd backend
source venv/bin/activate  # 如果需要
APP_ENV=production python3 scripts/batch_reprocess_th_hi_subtitles.py
```

或者直接：

```bash
cd backend && APP_ENV=production python3 scripts/batch_reprocess_th_hi_subtitles.py
```

## 脚本功能

1. 获取所有剧集列表（从 GCS source bucket）
2. 对每个剧集：
   - 选择 `episodes` 目录下的所有文件
   - 选择 `subtitles/final` 下的以下目录（如果存在）：
     - `th_translated`
     - `hi_translated`
     - `th`
     - `hi`
3. 触发手动处理任务（在生产环境 Cloud Run 中执行）
4. 报告结果（包括任务 ID、选择的目录等）

## 输出

脚本会输出：
- 处理的剧集数量
- 每个剧集的任务 ID
- 每个剧集选择的目录
- 成功/跳过/失败的数量
- 详细结果保存到 `backend/scripts/batch_reprocess_results.json`

## 注意事项

- 脚本会自动排队，受并发控制限制（默认最多 1 个并发任务）
- 任务会在 Cloud Run 中执行，不会在本地运行
- 如果某个剧集没有找到目标目录，会跳过该剧集

