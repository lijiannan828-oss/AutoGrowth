# GitHub Secrets 使用验证

## ✅ 已确认的 GitHub Secrets 使用

### 1. GCP_SA_KEY
**用途**: GCP 服务账号密钥（JSON 格式）

**在 workflow 中的使用**:
- ✅ **第 46 行**: 用于 Google Cloud 认证
  ```yaml
  credentials_json: ${{ secrets.GCP_SA_KEY }}
  ```

- ✅ **第 80 行**: 创建临时服务账号密钥文件
  ```yaml
  echo "${{ secrets.GCP_SA_KEY }}" > /tmp/service-account.json
  ```

- ✅ **第 96-100 行**: 用于创建 Secret Manager secret `gcp-sa-key`
  ```yaml
  gcloud secrets create gcp-sa-key \
    --data-file=/tmp/service-account.json
  ```

### 2. POSTGRES_PASSWORD
**用途**: PostgreSQL 数据库密码

**在 workflow 中的使用**:
- ✅ **第 88-93 行**: 用于创建 Secret Manager secret `postgres-password`
  ```yaml
  echo -n "${{ secrets.POSTGRES_PASSWORD }}" | gcloud secrets create postgres-password
  ```

- ✅ **第 121 行**: 在 Cloud Run 部署时通过 Secret Manager 注入
  ```yaml
  --set-secrets "DATABASE_PASSWORD=postgres-password:latest"
  ```

### 3. 其他 Secrets（可选）

- `GOOGLE_SHEETS_ID` (可选): 已在第 120 行使用
  ```yaml
  GOOGLE_SHEETS_ID=${{ secrets.GOOGLE_SHEETS_ID || '' }}
  ```

## 工作流程说明

### 步骤 1: 认证
使用 `GCP_SA_KEY` 进行 Google Cloud 认证

### 步骤 2: 创建 Secret Manager Secrets
1. 从 `POSTGRES_PASSWORD` 创建 `postgres-password` secret
2. 从 `GCP_SA_KEY` 创建 `gcp-sa-key` secret
3. **自动授予运行时服务账号访问权限**

### 步骤 3: 部署 Cloud Run
- 使用 Secret Manager secrets 注入敏感信息
- 运行时服务账号自动拥有访问权限

## 验证清单

- [x] `GCP_SA_KEY` 在 GitHub Secrets 中已配置
- [x] `POSTGRES_PASSWORD` 在 GitHub Secrets 中已配置
- [x] Workflow 正确读取 `GCP_SA_KEY`
- [x] Workflow 正确读取 `POSTGRES_PASSWORD`
- [x] Workflow 自动创建 Secret Manager secrets
- [x] Workflow 自动授予运行时服务账号访问权限
- [x] Cloud Run 部署时正确使用 Secret Manager secrets

## 注意事项

1. **首次部署**: 
   - Secrets 会自动创建
   - 运行时服务账号访问权限会自动授予

2. **后续部署**:
   - 如果 secrets 已存在，会更新为新版本
   - 访问权限检查会跳过（如果已存在）

3. **安全性**:
   - GitHub Secrets 中的值不会在日志中显示
   - Secret Manager 中的值通过环境变量注入，不会暴露在容器中

## 测试建议

在首次部署前，可以手动验证 secrets 是否正确配置：

```bash
# 检查 GitHub Secrets 是否存在（需要在 GitHub UI 中检查）
# Settings → Secrets and variables → Actions

# 部署后验证 Secret Manager secrets
gcloud secrets list --project=autogrowth-477909

# 验证运行时服务账号访问权限
gcloud secrets get-iam-policy postgres-password --project=autogrowth-477909
gcloud secrets get-iam-policy gcp-sa-key --project=autogrowth-477909
```

