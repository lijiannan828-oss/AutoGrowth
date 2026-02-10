# "压制字幕"功能 500 错误分析与排查指南

## 问题描述

在生产环境点击"压制字幕"按钮时出现 500 错误，开发环境正常。

## 功能流程分析

### 1. 前端调用流程
```
前端点击"压制字幕"按钮
  ↓
调用 triggerManualProcess() API
  ↓
POST /api/pipeline/process-manual
  ↓
后端 PipelineProcessService.trigger_manual_process_job()
```

### 2. 后端执行流程
```python
# backend/app/services/pipeline_process_service.py
def trigger_manual_process_job():
    1. 验证输入参数（drama_name, file_paths）
    2. 创建 Firestore 文档（pipeline_jobs 集合）
    3. 调用 _trigger_process_worker() 触发 Cloud Run Job
       - 如果 app_env == "development": 本地启动 subprocess
       - 否则: 调用 Cloud Run Jobs API 触发 Job
```

## 可能导致 500 错误的原因

### 🔴 原因 1: PROCESSOR_JOB_NAME 环境变量未配置或变量名不匹配 ⚠️ **已发现并修复**

**问题位置**: `backend/app/services/pipeline_process_service.py:157`

```python
if not self._process_job_name:
    raise RuntimeError("PROCESSOR_JOB_NAME 未配置，无法触发 Cloud Run Job")
```

**问题原因**:
- 部署配置中使用的是 `PROCESSOR_JOB_NAME`（`.github/workflows/backend-deploy.yaml:220,334`）
- 代码中期望的是 `PROCESS_JOB_NAME`（`backend/app/core/config.py:83`）
- **变量名不一致导致环境变量读取失败**

**已修复**:
- ✅ 已将代码中的 `PROCESS_JOB_NAME` 统一改为 `PROCESSOR_JOB_NAME`
- ✅ 部署配置中已正确设置 `PROCESSOR_JOB_NAME: "projects/${PROJECT_ID}/locations/${REGION}/jobs/${PROCESSOR_JOB_NAME}"`

**检查方法**:
```bash
# 检查 Cloud Run 服务的环境变量
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="value(spec.template.spec.containers[0].env)" | grep PROCESSOR_JOB_NAME

# 或者查看所有环境变量
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="yaml(spec.template.spec.containers[0].env)"
```

### 🔴 原因 2: Cloud Run Jobs API 权限不足

**问题位置**: `backend/app/services/pipeline_process_service.py:173`

```python
operation = self._jobs_client.run_job(request=request)
```

**需要的权限**:
运行时服务账号 `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 需要：
- `roles/run.invoker` - 调用 Cloud Run Jobs
- 或者 `roles/run.developer` - 更广泛的 Cloud Run 权限

**检查方法**:
```bash
# 检查服务账号的 IAM 角色
gcloud projects get-iam-policy autogrowth-477909 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# 检查是否有 run.invoker 或 run.developer 角色
```

**修复方法**:
```bash
# 授予 Cloud Run Invoker 角色
gcloud projects add-iam-policy-binding autogrowth-477909 \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# 或者授予 Cloud Run Developer 角色（权限更广）
gcloud projects add-iam-policy-binding autogrowth-477909 \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/run.developer"
```

### 🔴 原因 3: Cloud Run Job 不存在或名称错误

**问题位置**: `backend/app/services/pipeline_process_service.py:168`

```python
request = run_v2.RunJobRequest(
    name=self._process_job_name,  # 如果 Job 不存在，会返回 404
    overrides=overrides,
)
```

**检查方法**:
```bash
# 列出所有 Cloud Run Jobs
gcloud run jobs list \
  --region us-central1 \
  --project autogrowth-477909

# 检查特定的 Job 是否存在
gcloud run jobs describe process-worker \
  --region us-central1 \
  --project autogrowth-477909

# 如果 Job 存在，获取完整名称
gcloud run jobs describe process-worker \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="value(name)"
```

**修复方法**:
1. 如果 Job 不存在，需要先创建 Cloud Run Job
2. 如果 Job 存在但名称不匹配，更新 `PROCESS_JOB_NAME` 环境变量

### 🔴 原因 4: Firestore 写入权限不足

**问题位置**: `backend/app/services/pipeline_process_service.py:112-134`

```python
job_ref = self._firestore.collection(self._jobs_collection).document()
doc_body = {...}
job_ref.set(doc_body)  # 如果权限不足，会抛出异常
```

**检查方法**:
```bash
# 检查服务账号是否有 Firestore 写入权限
# Firestore 使用 Cloud Datastore API，需要以下角色之一：
# - roles/datastore.user (推荐)
# - roles/datastore.owner (权限更广)
```

**修复方法**:
```bash
# 授予 Datastore User 角色
gcloud projects add-iam-policy-binding autogrowth-477909 \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### 🔴 原因 5: 服务账号认证失败

**问题位置**: `backend/app/services/pipeline_process_service.py:35`

```python
self._jobs_client = run_v2.JobsClient()
# 如果 GOOGLE_APPLICATION_CREDENTIALS 未正确配置，会认证失败
```

**检查方法**:
```bash
# 检查 Cloud Run 服务是否正确配置了服务账号
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="value(spec.template.spec.serviceAccountName)"

# 应该返回: sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com

# 检查 GOOGLE_APPLICATION_CREDENTIALS secret 是否存在
gcloud secrets describe gcp-sa-key \
  --project autogrowth-477909
```

## 排查步骤（按优先级）

### 步骤 1: 检查 Cloud Run 日志

```bash
# 查看最近的错误日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=autogrowth-backend AND severity>=ERROR" \
  --limit 50 \
  --project autogrowth-477909 \
  --format json

# 或者查看特定时间段的日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=autogrowth-backend AND timestamp>=\"2025-01-15T00:00:00Z\"" \
  --limit 100 \
  --project autogrowth-477909
```

### 步骤 2: 检查环境变量配置

```bash
# 检查 PROCESS_JOB_NAME 是否配置
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="value(spec.template.spec.containers[0].env)" | grep PROCESS_JOB_NAME
```

### 步骤 3: 检查服务账号权限

```bash
# 运行权限验证脚本
./infra/verify_service_account_permissions.sh

# 检查是否有 Cloud Run Jobs 相关权限
gcloud projects get-iam-policy autogrowth-477909 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com AND bindings.role:roles/run.*" \
  --format="table(bindings.role)"
```

### 步骤 4: 检查 Cloud Run Job 是否存在

```bash
# 列出所有 Jobs
gcloud run jobs list --region us-central1 --project autogrowth-477909

# 如果 Job 不存在，需要创建（参考 infra/ 目录下的部署脚本）
```

### 步骤 5: 测试 API 端点

```bash
# 获取 Cloud Run 服务 URL
SERVICE_URL=$(gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)')

# 测试健康检查端点
curl ${SERVICE_URL}/health

# 测试压制字幕端点（需要认证 token）
# 注意：这需要有效的认证 token
curl -X POST ${SERVICE_URL}/api/pipeline/process-manual \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"drama_name": "TEST", "file_paths": ["test/path"]}'
```

## 快速修复脚本

创建 `infra/fix_manual_process_permissions.sh`:

```bash
#!/bin/bash

PROJECT_ID="autogrowth-477909"
SERVICE_ACCOUNT="sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"
REGION="us-central1"

echo "=========================================="
echo "修复压制字幕功能权限"
echo "=========================================="

# 1. 授予 Cloud Run Invoker 权限
echo "1. 授予 Cloud Run Invoker 权限..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/run.invoker" \
  --condition=None

# 2. 授予 Datastore User 权限（Firestore 写入）
echo "2. 授予 Datastore User 权限..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/datastore.user" \
  --condition=None

# 3. 检查 Cloud Run Job 是否存在
echo "3. 检查 Cloud Run Job..."
JOB_NAME="process-worker"
if gcloud run jobs describe ${JOB_NAME} --region ${REGION} --project ${PROJECT_ID} > /dev/null 2>&1; then
    echo "   ✅ Job '${JOB_NAME}' 存在"
    FULL_JOB_NAME=$(gcloud run jobs describe ${JOB_NAME} --region ${REGION} --project ${PROJECT_ID} --format="value(name)")
    echo "   完整名称: ${FULL_JOB_NAME}"
    echo ""
    echo "   请确保 Cloud Run 服务配置了以下环境变量:"
    echo "   PROCESS_JOB_NAME=${FULL_JOB_NAME}"
else
    echo "   ❌ Job '${JOB_NAME}' 不存在"
    echo "   需要先创建 Cloud Run Job"
fi

echo ""
echo "✅ 权限修复完成"
```

## 部署配置检查清单

### GitHub Actions Workflow (`infra/github/workflows/backend-deploy.yaml`)

确保以下环境变量已配置：
- [ ] `PROCESS_JOB_NAME` - Cloud Run Job 的完整名称
- [ ] `TRANSFER_JOB_NAME` - 传输 Job 名称（如果使用）
- [ ] `ZIP_JOB_NAME` - ZIP Job 名称（如果使用）

### Cloud Run 服务账号权限

确保 `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 有以下角色：
- [ ] `roles/cloudsql.client` - Cloud SQL 连接
- [ ] `roles/secretmanager.secretAccessor` - Secret Manager 访问
- [ ] `roles/datastore.user` - Firestore 读写
- [ ] `roles/run.invoker` - Cloud Run Jobs 调用
- [ ] `roles/storage.objectViewer` - GCS 读取（如果需要）

### Cloud Run Job 配置

- [ ] Process Worker Job 已创建
- [ ] Job 名称与 `PROCESS_JOB_NAME` 环境变量匹配
- [ ] Job 的服务账号有必要的权限

## 常见错误消息及解决方案

### 错误 1: "PROCESSOR_JOB_NAME 未配置，无法触发 Cloud Run Job"
**解决方案**: 
- ✅ **已修复**：代码已统一使用 `PROCESSOR_JOB_NAME`
- 确保部署配置中设置了 `PROCESSOR_JOB_NAME` 环境变量（已在 `.github/workflows/backend-deploy.yaml` 中配置）

### 错误 2: "触发 Process Cloud Run Job 失败: Permission denied"
**解决方案**: 授予服务账号 `roles/run.invoker` 角色

### 错误 3: "触发 Process Cloud Run Job 失败: Job not found"
**解决方案**: 
1. 检查 Job 是否存在（Job 名称：`drama-processor-job`）
2. 检查 `PROCESSOR_JOB_NAME` 是否正确（完整路径格式：`projects/PROJECT_ID/locations/REGION/jobs/drama-processor-job`）

### 错误 4: "Firestore 写入失败: Permission denied"
**解决方案**: 授予服务账号 `roles/datastore.user` 角色

## 验证修复

修复后，通过以下方式验证：

1. **检查日志**:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=autogrowth-backend AND textPayload:\"触发 Process Cloud Run Job\"" \
  --limit 10 \
  --project autogrowth-477909
```

2. **测试 API**:
在生产环境前端测试"压制字幕"功能，确认不再出现 500 错误

3. **检查 Firestore**:
确认 `pipeline_jobs` 集合中创建了新的文档

4. **检查 Cloud Run Job**:
确认 Process Worker Job 被成功触发并执行

