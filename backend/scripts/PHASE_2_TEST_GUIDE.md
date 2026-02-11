# 第二阶段测试指南：本地集成测试 (Local Integration Testing)

## 测试目标
在本地模拟真实 Worker 运行，验证：
1. **分片逻辑正确**：多个 Task 分别处理不同的文件
2. **Firestore 交互**：Task 文档和主文档正确更新
3. **GCS 下载/上传**：文件正确处理和上传
4. **状态追踪准确**：细粒度进度和汇总进度一致

## 前置条件

### 1. 环境准备
- ✅ 已安装 FFmpeg：`brew install ffmpeg`
- ✅ 已设置 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量
- ✅ Python 虚拟环境已激活
- ✅ 已安装所有依赖：`pip install -r requirements.txt`

### 2. GCS 测试数据准备
- ✅ GCS bucket `vigloo_source` 中存在测试剧集
- ✅ 测试剧集包含少量文件（建议 4-10 个视频文件）
- ✅ 每个视频文件都有对应的字幕文件（.srt）

**推荐测试剧集名称**：`TEST_SHARDING_001`

## 测试步骤

### Step 1: 创建测试 Job

```bash
cd /Users/mac/AutoGrowth/backend
source venv/bin/activate
python scripts/setup_phase2_test_job.py TEST_SHARDING_001
```

**输出示例**：
```
✅ Created test job:
   Job ID: abc123xyz
   Drama Name: TEST_SHARDING_001
   Status: QUEUED
```

**记录 Job ID**：`<JOB_ID>`（后续步骤需要使用）

### Step 2: 启动 Task 0（终端 1）

打开第一个终端窗口：

```bash
cd /Users/mac/AutoGrowth/backend
source venv/bin/activate
./scripts/run_process_worker_local.sh <JOB_ID> 0 2
```

**预期输出**：
- Worker 启动日志
- `📊 Task 0/2: Claimed X of Y episodes`
- `📝 Task 0/2: Initialized Firestore task document`
- 处理文件日志（例如：`✅ US01 ep001 完成`）

### Step 3: 启动 Task 1（终端 2）

打开第二个终端窗口（**同时运行**）：

```bash
cd /Users/mac/AutoGrowth/backend
source venv/bin/activate
./scripts/run_process_worker_local.sh <JOB_ID> 1 2
```

**预期输出**：
- Worker 启动日志
- `📊 Task 1/2: Claimed X of Y episodes`
- `📝 Task 1/2: Initialized Firestore task document`
- 处理文件日志（**应该处理不同的文件**）

### Step 4: 观察日志输出

**关键观察点**：

1. **分片验证**：
   - Task 0 和 Task 1 应该处理**不同的文件**
   - 例如：Task 0 处理 ep000, ep002, ep004...，Task 1 处理 ep001, ep003, ep005...
   - 日志中应显示：`Task 0/2: Claimed X episodes` 和 `Task 1/2: Claimed Y episodes`

2. **Firestore 更新**：
   - 每个 Task 应该创建自己的 Task 文档
   - 主文档的 `processed_files` 应该递增
   - Task 文档的 `success_files` 应该包含已处理的文件

3. **处理完成**：
   - 两个 Task 都应该完成处理
   - 主文档状态应该变为 `SUCCEEDED`
   - Task 文档状态应该变为 `COMPLETED`

### Step 5: 验证结果

运行验证脚本：

```bash
cd /Users/mac/AutoGrowth/backend
source venv/bin/activate
python scripts/verify_phase2_results.py <JOB_ID> 2
```

**预期输出**：
```
✅ All verifications passed!
  ✅ Task documents count: 2 (expected: 2)
  ✅ Completed tasks: 2/2
  ✅ Main job status: SUCCEEDED
  ✅ Processed files match
  ✅ No duplicate files across tasks
```

## 手动验证（可选）

### 1. 检查 Firestore 主文档

访问 Firestore Console：
```
https://console.cloud.google.com/firestore/databases/-default-/data/~2Fpipeline_jobs~2F<JOB_ID>
```

**验证点**：
- `status`: `SUCCEEDED`
- `processed_files`: 应该等于总文件数
- `failed_files`: 应该为 0（如果没有失败）
- `total_files`: 应该等于实际文件数

### 2. 检查 Task 文档

访问 Firestore Console：
```
https://console.cloud.google.com/firestore/databases/-default-/data/~2Fpipeline_jobs~2F<JOB_ID>~2Ftasks~2F0
https://console.cloud.google.com/firestore/databases/-default-/data/~2Fpipeline_jobs~2F<JOB_ID>~2Ftasks~2F1
```

**验证点**：
- `status`: `COMPLETED`
- `success_files`: 应该包含该 Task 处理的所有文件
- `progress_count`: 应该等于 `total_count`
- `failed_files`: 应该为空（如果没有失败）

### 3. 检查 GCS 输出

访问 GCS Console：
```
https://console.cloud.google.com/storage/browser/vigloo_processed
```

**验证点**：
- 处理后的文件应该上传到 `vigloo_processed` bucket
- 文件路径应该正确（例如：`TEST_SHARDING_001/US01/ep001.mp4`）

## 常见问题排查

### 问题 1: Task 0 和 Task 1 处理相同的文件

**原因**：环境变量未正确设置

**解决**：
- 确保两个终端都设置了正确的 `CLOUD_RUN_TASK_INDEX` 和 `CLOUD_RUN_TASK_COUNT`
- 检查脚本是否正确传递参数

### 问题 2: Firestore 文档未创建

**原因**：Firestore 权限或连接问题

**解决**：
- 检查 `GOOGLE_APPLICATION_CREDENTIALS` 是否正确设置
- 检查 Firestore 项目 ID 是否正确
- 查看 Worker 日志中的错误信息

### 问题 3: 文件处理失败

**原因**：GCS 文件不存在或 FFmpeg 错误

**解决**：
- 检查 GCS bucket 中是否存在测试文件
- 检查文件路径是否正确
- 查看 Worker 日志中的详细错误信息

## 测试成功标准

✅ **所有以下条件必须满足**：

1. ✅ Task 0 和 Task 1 处理了**不同的文件**（无重复）
2. ✅ 所有文件都被处理（无遗漏）
3. ✅ Firestore 中创建了 2 个 Task 文档（tasks/0 和 tasks/1）
4. ✅ 两个 Task 文档状态都是 `COMPLETED`
5. ✅ 主文档 `processed_files` 等于总文件数
6. ✅ 主文档 `status` 是 `SUCCEEDED`
7. ✅ 处理后的文件成功上传到 GCS `vigloo_processed` bucket

## 测试报告模板

测试完成后，请记录以下信息：

```
## Phase 2 测试结果

**测试时间**：YYYY-MM-DD HH:MM:SS
**Job ID**：<JOB_ID>
**测试剧集**：TEST_SHARDING_001
**总文件数**：X

### Task 分配
- Task 0/2: X 个文件
- Task 1/2: Y 个文件
- 总计：X + Y = Z 个文件

### Firestore 验证
- ✅ Task 文档数量：2
- ✅ Task 0 状态：COMPLETED
- ✅ Task 1 状态：COMPLETED
- ✅ 主文档状态：SUCCEEDED
- ✅ 主文档 processed_files：Z

### 文件处理验证
- ✅ 无重复文件
- ✅ 无遗漏文件
- ✅ GCS 上传成功

### 测试结论
✅ **PASSED** / ❌ **FAILED**

### 备注
（记录任何异常或问题）
```

---

**准备就绪后，请按照上述步骤执行测试。**


