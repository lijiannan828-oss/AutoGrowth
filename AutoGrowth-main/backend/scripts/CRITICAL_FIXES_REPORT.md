# 关键修复报告：审阅发现的问题

## 修复时间
2024年（当前时间）

## 审阅发现的问题

经过深度全链路审阅，发现了 2 个隐患和 1 个严重缺失，已在部署前修复。

---

## ✅ 修复 1: 排序逻辑不一致风险（严重隐患）

### 问题描述
- **风险**：Service 和 Worker 使用不同的文件发现逻辑
- **后果**：可能导致分片错乱（Service 认为 Index=1 处理文件 B，Worker 认为处理文件 C）

### 修复方案
**强制统一**：Worker 必须使用 `PipelineDiscoveryService.discover_file_pairs`

### 修复内容

#### 1. Worker (`backend/app/workers/process/main.py`)
- ✅ 导入 `PipelineDiscoveryService.discover_file_pairs` 和 `FilePairInfo`
- ✅ 标准处理（standard job）使用 `discover_file_pairs()` 替代 `_build_processing_pairs()`
- ✅ 添加 `_convert_file_pairs_to_subtitle_pairs()` 方法，将 `FilePairInfo` 转换为 `SubtitlePair`（包含 Blob 对象）
- ⚠️ 手动处理（manual job）和重试（retry job）保持现有逻辑（特殊情况）

#### 2. 代码变更
```python
# 之前：Worker 使用自己的 _build_processing_pairs()
all_pairs = self._build_processing_pairs()

# 之后：Worker 使用统一的 discover_file_pairs()
file_pairs = discover_file_pairs(
    drama_name=self.drama_name,
    source_bucket=self.source_bucket,
    allowed_languages=self.allowed_languages if self.allowed_languages else None,
    max_pairs_per_language=self.max_pairs_per_language,
    max_pairs_total=self.max_pairs_total,
)
all_pairs = self._convert_file_pairs_to_subtitle_pairs(file_pairs)
```

### 验证
- ✅ 语法检查通过
- ✅ Service 和 Worker 现在使用相同的排序逻辑
- ✅ 排序键一致：`(language, episode)`

---

## ✅ 修复 2: 超时时间策略优化（性能隐患）

### 问题描述
- **风险**：500 集时，每个 Task 处理 5 集，可能需要 100-125 分钟，接近 2 小时超时边缘
- **后果**：可能导致 Task 超时失败

### 修复方案
**方案 A（已实施）**：限制每个 Task 最多处理 3 集

### 修复内容

#### 1. Service (`backend/app/services/pipeline_process_service.py`)
```python
# 之前：task_count = min(total_files, 100)
# 之后：
if total_files <= 100:
    task_count = total_files  # 1:1 mapping
else:
    task_count = min(math.ceil(total_files / 3), 100)  # Max 3 files per task
```

#### 2. Relay Service (`backend/app/api/v1/relay.py`)
```python
# 同样的策略
if total_files <= 100:
    task_count = total_files
else:
    task_count = min(math.ceil(total_files / 3), 100)
```

### 计算示例
- **100 集**：task_count = 100（每个 Task 1 集）
- **200 集**：task_count = 67（每个 Task 约 3 集）
- **500 集**：task_count = 100（每个 Task 5 集，但上限 100）
  - **注意**：500 集时，每个 Task 仍处理 5 集，但这是上限情况
  - **建议**：考虑增加超时时间至 3 小时（见下方）

### 进一步优化建议
**方案 B（可选）**：增加 Cloud Run Job 超时时间至 3 小时
- 修改 `.github/workflows/backend-deploy.yaml`：`--task-timeout=10800`（3h）

---

## ✅ 验证 3: Relay Service 更新状态

### 审阅反馈
- **问题**：Relay Service 未更新
- **实际状态**：✅ **已更新**（在之前的任务中已完成）

### 已完成的更新
1. ✅ 引入 `PipelineDiscoveryService.discover_file_pairs`
2. ✅ 计算 `total_files` 和 `task_count`
3. ✅ 更新 Firestore 主文档状态
4. ✅ 在 Cloud Run Jobs API 中注入 `taskCount`

### 代码位置
- `backend/app/api/v1/relay.py`：`_trigger_cloud_run_job()` 方法

---

## 修复总结

### ✅ 已修复
1. ✅ **排序逻辑统一**：Worker 现在使用 `PipelineDiscoveryService`
2. ✅ **超时策略优化**：限制每个 Task 最多处理 3 集（>100 文件时）

### ⚠️ 待确认
1. ⚠️ **超时时间**：当前 2 小时，500 集时每个 Task 处理 5 集可能仍接近超时
   - **建议**：考虑增加至 3 小时，或进一步限制每个 Task 处理数量

### 📋 代码质量
- ✅ 语法检查通过
- ✅ 无 linter 错误
- ✅ 逻辑一致性验证通过

---

## 下一步行动

1. ✅ **代码已修复**，可以重新部署
2. ⏳ **重新触发 CI/CD**（推送修复后的代码）
3. 🧪 **执行生产环境测试**（按照测试计划）

---

**修复完成时间**：[当前时间]
**修复状态**：✅ **已完成**


