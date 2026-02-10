# Artifact Registry 权限问题排查

## 问题描述

GitHub Actions 部署时出现权限错误：
```
PERMISSION_DENIED: Permission 'artifactregistry.repositories.create' denied
```

## 已完成的修复

✅ **权限已授予**：
- 服务账号：`github-actions-deployer@fleet-blend-469520-n7.iam.gserviceaccount.com`
- 角色：`roles/artifactregistry.admin`
- 项目：`autogrowth-477909`

## 可能的原因和解决方案

### 1. IAM 权限传播延迟

IAM 权限更改可能需要 **1-5 分钟** 才能完全生效。

**解决方案**：
- 等待几分钟后重新运行 GitHub Actions workflow
- 或者手动创建仓库（见下方）

### 2. Artifact Registry API 未启用

**检查**：
```bash
gcloud services list --enabled --project=autogrowth-477909 | grep artifactregistry
```

**启用**：
```bash
gcloud services enable artifactregistry.googleapis.com --project=autogrowth-477909
```

### 3. 手动创建仓库（临时方案）

如果权限传播需要时间，可以手动创建仓库：

```bash
gcloud artifacts repositories create autogrowth-docker \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository for AutoGrowth backend" \
  --project=autogrowth-477909
```

创建后，workflow 会检测到仓库已存在并跳过创建步骤。

### 4. 验证权限

```bash
# 检查权限
gcloud projects get-iam-policy autogrowth-477909 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:github-actions-deployer@fleet-blend-469520-n7.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# 应该看到：roles/artifactregistry.admin
```

## 推荐操作

1. **等待 2-3 分钟**让 IAM 权限传播
2. **重新运行 GitHub Actions workflow**
3. 如果仍然失败，**手动创建仓库**（见上方命令）

## 验证

创建成功后，可以验证：

```bash
gcloud artifacts repositories list --location=us-central1 --project=autogrowth-477909
```

应该看到 `autogrowth-docker` 仓库。






