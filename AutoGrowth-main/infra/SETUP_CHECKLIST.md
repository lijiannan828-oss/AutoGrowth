# Cloud Run 部署配置检查清单

## 需要确认的信息

请提供以下信息以完成配置：

### 1. GCP 项目信息
- [ ] **GCP 项目 ID**: `FIREBASE_AUTOGROWTH_PROJECT_ID` 的值
  - 已在 GitHub Secrets 中配置，但需要确认用于更新配置文件

### 2. 区域配置
- [ ] **Cloud Run 区域**: 例如 `us-central1`, `asia-east1`, `europe-west1`
  - 建议：选择离用户最近的区域
- [ ] **Artifact Registry 区域**: 通常与 Cloud Run 区域相同

### 3. 服务命名
- [ ] **Artifact Registry 仓库名称**: 例如 `autogrowth-docker`
  - 如果不存在，GitHub Actions 会自动创建
- [ ] **Cloud Run 服务名称**: 例如 `autogrowth-backend`

### 4. 数据库连接
- [ ] **Cloud SQL 连接名称**: `CLOUD_SQL_CONN_NAME` 的值
  - 格式：`project-id:region:instance-name`
  - 已在 GitHub Secrets 中配置

### 5. 其他配置
- [ ] **Google Sheets ID**: 如果已配置在 GitHub Secrets 中，请确认
- [ ] **数据库用户名**: 当前配置为 `appdev`，如需修改请告知

## 已完成的配置

✅ **Dockerfile**: 已优化为多阶段构建，包含健康检查
✅ **Cloud Build 配置**: `infra/cloudbuild.yaml` 已创建
✅ **GitHub Actions Workflow**: `infra/github/workflows/backend-deploy.yaml` 已创建
✅ **部署文档**: `infra/DEPLOYMENT_SETUP.md` 已创建

## 下一步操作

1. **提供上述信息**（如果与默认值不同）
2. **更新配置文件**（如果需要调整区域、服务名称等）
3. **创建 Artifact Registry 仓库**（如果不存在，GitHub Actions 会自动创建）
4. **测试部署**（推送到 GitHub 或手动触发）

## 默认配置

如果不需要修改，将使用以下默认值：

- **区域**: `us-central1`
- **Artifact Registry 仓库**: `autogrowth-docker`
- **Cloud Run 服务**: `autogrowth-backend`
- **数据库用户**: `appdev`
- **数据库名称**: `auto_growth`

## 注意事项

1. **Secret Manager vs GitHub Secrets**:
   - 当前配置使用 GitHub Secrets 直接注入环境变量
   - 如果希望使用 Secret Manager，需要额外配置

2. **服务账号权限**:
   - 确保 GitHub Actions 使用的服务账号具有足够权限
   - 需要：Cloud Run Admin, Artifact Registry Writer, Cloud SQL Client

3. **首次部署**:
   - Artifact Registry 仓库会在首次部署时自动创建
   - 如果创建失败，请手动创建或检查权限

