# 服务账号权限验证完成

## ✅ 验证结果

### 服务账号信息
- **服务账号**: `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`
- **项目 ID**: `autogrowth-477909`

### 已授予的 IAM 角色

1. ✅ **roles/cloudsql.client**
   - 用途: 允许服务账号连接到 Cloud SQL 实例
   - 状态: 已授予

2. ✅ **roles/secretmanager.secretAccessor**
   - 用途: 允许服务账号读取 Secret Manager 中的 secrets
   - 状态: 已授予

### Secret Manager Secrets

以下 secrets 将在首次部署时自动创建：
- `postgres-password` - 数据库密码
- `gcp-sa-key` - GCP 服务账号密钥

**注意**: 首次部署后，需要确保这些 secrets 的 IAM 策略允许 `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 访问。

### Cloud SQL 连接

- ✅ Cloud SQL 实例存在: `yvideo-factory-db-prod`
- ℹ️  确保 Cloud SQL 实例允许 Cloud Run 连接
- ℹ️  如果使用私有 IP，需要配置 VPC 连接器

### Artifact Registry

- ℹ️  Artifact Registry 仓库将在首次部署时自动创建: `autogrowth-docker`

## 下一步操作

1. ✅ 服务账号权限已配置完成
2. ⏳ 准备 GitHub 仓库并推送代码
3. ⏳ 配置 GitHub Secrets
4. ⏳ 触发首次部署

## 验证命令

如果需要再次验证权限，可以运行：

```bash
./infra/verify_service_account_permissions.sh
```

如果需要修复权限，可以运行：

```bash
./infra/fix_service_account_permissions.sh
```

## 注意事项

1. **Secret Manager Secrets 访问权限**: 
   - 首次部署后，secrets 会被创建
   - 需要确保 secrets 的 IAM 策略允许运行时服务账号访问
   - GitHub Actions workflow 会自动处理此配置

2. **Cloud SQL 连接**:
   - 确保 Cloud SQL 实例允许 Cloud Run 连接
   - 如果使用私有 IP，需要配置 VPC 连接器

3. **Artifact Registry**:
   - 仓库将在首次部署时自动创建
   - 确保部署服务账号有 `roles/artifactregistry.writer` 权限

