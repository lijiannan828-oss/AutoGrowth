# 快速修复"压制字幕"500错误

## 🔴 最可能的原因（按优先级）

### 1. PROCESSOR_JOB_NAME 环境变量未配置或变量名不匹配 ⚠️ **已发现并修复**

**问题**: 
- 部署配置中使用 `PROCESSOR_JOB_NAME`
- 代码中期望 `PROCESS_JOB_NAME`
- **变量名不一致导致环境变量读取失败**

**已修复**:
- ✅ 代码已统一使用 `PROCESSOR_JOB_NAME`
- ✅ 部署配置中已正确设置（`.github/workflows/backend-deploy.yaml:220,334`）

**快速检查**:
```bash
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format="value(spec.template.spec.containers[0].env)" | grep PROCESSOR_JOB_NAME
```

**验证 Job 是否存在**:
```bash
# Job 名称应该是: drama-processor-job
gcloud run jobs list --region us-central1 --project autogrowth-477909 | grep drama-processor-job
```

### 2. Cloud Run Jobs API 权限不足 ⚠️ **很可能**

**问题**: 服务账号缺少 `roles/run.invoker` 权限

**快速修复**:
```bash
gcloud projects add-iam-policy-binding autogrowth-477909 \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### 3. Firestore 写入权限不足 ⚠️ **可能**

**问题**: 服务账号缺少 `roles/datastore.user` 权限

**快速修复**:
```bash
gcloud projects add-iam-policy-binding autogrowth-477909 \
  --member="serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### 4. Cloud Run Job 不存在 ⚠️ **需要确认**

**检查**:
```bash
gcloud run jobs list --region us-central1 --project autogrowth-477909
```

**如果不存在，需要创建 Job**（参考 `backend/app/workers/process/Dockerfile`）

## 🚀 一键修复脚本

运行以下脚本自动修复所有权限问题:

```bash
./infra/fix_manual_process_permissions.sh
```

## 📋 部署配置更新

**注意**: 部署配置中已正确设置 `PROCESSOR_JOB_NAME`（`.github/workflows/backend-deploy.yaml:220,334`）：
```yaml
PROCESSOR_JOB_NAME: "projects/${PROJECT_ID}/locations/${REGION}/jobs/${PROCESSOR_JOB_NAME}"
```

Job 名称：`drama-processor-job`

## 🔍 查看错误日志

```bash
# 查看最近的错误日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=autogrowth-backend AND severity>=ERROR" \
  --limit 20 \
  --project autogrowth-477909 \
  --format json | jq '.[] | {timestamp: .timestamp, textPayload: .textPayload}'
```

