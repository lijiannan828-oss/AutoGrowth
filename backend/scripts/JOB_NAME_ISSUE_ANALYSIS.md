# PROCESSOR_JOB_NAME 未获取到的根本原因分析

## 问题现象
- `_check_cloud_run_execution_status` 无法检查 Cloud Run 执行状态
- 清理逻辑无法正常工作，导致锁无法释放
- 但实际上 `PROCESSOR_JOB_NAME` 环境变量在生产环境中**是存在的**，值是完整路径

## 根本原因

### 1. GitHub Actions Workflow 变量作用域问题

**Workflow 级别定义** (第22-31行):
```yaml
env:
  PROJECT_ID: fleet-blend-469520-n7
  REGION: us-central1
  PROCESSOR_JOB_NAME: drama-processor-job  # ✅ 定义在这里
```

**Step 级别使用** (第297-340行):
```yaml
- name: Prepare environment variables file
  env:
    PIPELINE_GDRIVE_ROOTS: ${{ secrets.PIPELINE_GDRIVE_ROOTS }}
    # ❌ PROCESSOR_JOB_NAME 不在这个 env 块中！
  run: |
    cat <<ENV > /tmp/backend-env.yaml
    PROCESSOR_JOB_NAME: "projects/${PROJECT_ID}/locations/${REGION}/jobs/${PROCESSOR_JOB_NAME}"
    # ❌ ${PROCESSOR_JOB_NAME} 在 shell 脚本中是空的！
    ENV
```

### 2. 问题分析

在 GitHub Actions 中：
- Workflow 级别的 `env:` 变量在整个 workflow 中可用
- 但在 step 的 `run:` 脚本中，如果 step 有自己的 `env:` 块，**只有 env 块中的变量会在 shell 中可用**
- `PROCESSOR_JOB_NAME` 定义在 workflow 级别，但没有在 step 的 `env:` 块中
- 所以在 shell 脚本中 `${PROCESSOR_JOB_NAME}` 是**空的**

### 3. 结果

环境变量文件 `/tmp/backend-env.yaml` 中的值变成：
```yaml
PROCESSOR_JOB_NAME: "projects/fleet-blend-469520-n7/locations/us-central1/jobs/"
#                                                                              ^^^ 这里缺少 job name！
```

或者可能是：
```yaml
PROCESSOR_JOB_NAME: ""  # 完全为空
```

### 4. 真正的问题：环境变量格式不匹配

**实际情况**（通过检查 Cloud Run 服务确认）：
- ✅ `PROCESSOR_JOB_NAME` 环境变量**确实存在**
- ✅ 值：`projects/fleet-blend-469520-n7/locations/us-central1/jobs/drama-processor-job`
- ❌ **但这是完整路径格式，不是 job name**

**问题分析**：
1. `_check_cloud_run_execution_status` 需要的是 job name：`drama-processor-job`
2. 但环境变量的值是完整路径：`projects/.../jobs/drama-processor-job`
3. 之前的代码直接使用完整路径构建 API 路径：
   ```python
   parent = f"projects/{project_id}/locations/{region}/jobs/{job_name}"
   # 如果 job_name 是完整路径，结果变成：
   # projects/.../jobs/projects/.../jobs/drama-processor-job  ❌ 错误！
   ```
4. 导致 API 调用失败，函数返回 `None`
5. 清理逻辑无法检查 Cloud Run 执行状态

**为什么之前测试时读取到的是空值**：
- 可能是在本地测试时（没有这个环境变量）
- 或者在某些特定的服务实例中环境变量确实为空
- 但主要问题是**格式不匹配**，而不是环境变量不存在

## 解决方案

### 方案 1: 修复 Workflow（推荐）

在 step 的 `env:` 块中添加 `PROCESSOR_JOB_NAME`:

```yaml
- name: Prepare environment variables file
  env:
    PIPELINE_GDRIVE_ROOTS: ${{ secrets.PIPELINE_GDRIVE_ROOTS }}
    PROCESSOR_JOB_NAME: ${{ env.PROCESSOR_JOB_NAME }}  # ✅ 添加这一行
    PROJECT_ID: ${{ env.PROJECT_ID }}  # ✅ 添加这一行
    REGION: ${{ env.REGION }}  # ✅ 添加这一行
  run: |
    cat <<ENV > /tmp/backend-env.yaml
    PROCESSOR_JOB_NAME: "projects/${PROJECT_ID}/locations/${REGION}/jobs/${PROCESSOR_JOB_NAME}"
    ENV
```

### 方案 2: 使用 GitHub Actions 表达式（更可靠）

直接在 heredoc 中使用 GitHub Actions 表达式：

```yaml
- name: Prepare environment variables file
  run: |
    cat <<ENV > /tmp/backend-env.yaml
    PROCESSOR_JOB_NAME: "projects/${{ env.PROJECT_ID }}/locations/${{ env.REGION }}/jobs/${{ env.PROCESSOR_JOB_NAME }}"
    ENV
```

### 方案 3: 代码层面的修复（已实施）

- ✅ 添加 fallback: `'drama-processor-job'`
- ✅ 支持从完整路径中提取 job name
- ✅ 即使环境变量为空，也能正常工作

## 当前状态

- ✅ **代码修复已完成**: 支持 fallback 和路径提取
- ⚠️ **Workflow 修复待实施**: 建议修复 workflow 以确保环境变量正确传递

## 建议

1. **立即**: 代码修复已部署，可以正常工作
2. **后续**: 修复 workflow，确保环境变量正确传递（避免依赖 fallback）
