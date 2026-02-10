# 部署前检查清单

## ✅ 已完成的配置

### 1. 服务账号权限
- [x] 运行时服务账号 `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com` 权限已配置
- [x] `roles/cloudsql.client` - 已授予
- [x] `roles/secretmanager.secretAccessor` - 已授予

### 2. GitHub Secrets
- [x] `GCP_SA_KEY` - 已配置
- [x] `POSTGRES_PASSWORD` - 已配置
- [x] `CLOUD_SQL_CONN_NAME` - 已配置
- [x] `FIREBASE_AUTOGROWTH_PROJECT_ID` - 已配置（或使用硬编码值）

### 3. 配置文件
- [x] Dockerfile 已优化
- [x] GitHub Actions workflow 已配置
- [x] Cloud Build 配置已创建
- [x] 运行时服务账号已指定
- [x] Secret Manager 策略已更新（不会覆盖已有 secrets）

### 4. 项目配置
- [x] GCP 项目 ID: `autogrowth-477909`
- [x] 区域: `us-central1`
- [x] Artifact Registry: `autogrowth-docker`
- [x] Cloud Run 服务: `autogrowth-backend`
- [x] Cloud SQL 连接: `fleet-blend-469520-n7:us-central1:yvideo-factory-db-prod`

## 📋 部署步骤

### 步骤 1: 初始化 Git 仓库（如果还没有）

```bash
cd /Users/mac/AutoGrowth

# 检查是否已初始化
if [ ! -d .git ]; then
  git init
  git branch -M main
fi

# 检查远程仓库
git remote -v
```

### 步骤 2: 添加远程仓库（如果还没有）

```bash
# 如果还没有远程仓库，添加 GitHub 仓库
git remote add origin https://github.com/lijiannan828/AutoGrowth.git

# 或者使用 SSH
# git remote add origin git@github.com:lijiannan828/AutoGrowth.git
```

### 步骤 3: 提交所有更改

```bash
# 添加所有文件
git add .

# 提交
git commit -m "feat: Add Cloud Run deployment configuration

- Configure GitHub Actions workflow for automatic deployment
- Add Dockerfile with multi-stage build
- Configure Secret Manager integration
- Set up runtime service account
- Add deployment documentation"
```

### 步骤 4: 推送到 GitHub

```bash
# 推送到 main 分支
git push -u origin main
```

### 步骤 5: 监控部署

1. 访问 GitHub 仓库
2. 点击 "Actions" 标签
3. 查看 "Backend Deploy to Cloud Run" workflow
4. 等待部署完成（约 5-10 分钟）

### 步骤 6: 验证部署

部署完成后，验证服务是否正常运行：

```bash
# 获取服务 URL
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)'

# 测试健康检查
curl https://your-service-url/health
```

## ⚠️ 注意事项

1. **首次部署**:
   - Artifact Registry 仓库会自动创建
   - Secret Manager secrets 会自动创建（如果不存在）
   - 运行时服务账号访问权限会自动授予

2. **Secret Manager**:
   - 如果 secrets 已存在，不会覆盖
   - 只会在不存在时创建

3. **部署时间**:
   - 首次部署可能需要 5-10 分钟
   - 后续部署通常更快（2-5 分钟）

4. **监控**:
   - 查看 GitHub Actions 日志了解部署进度
   - 查看 Cloud Run 日志了解服务状态

## 🔍 故障排查

如果部署失败，检查：

1. **GitHub Secrets** 是否正确配置
2. **服务账号权限** 是否足够
3. **Cloud SQL 连接** 是否允许 Cloud Run 访问
4. **Docker 镜像构建** 是否成功
5. **Secret Manager secrets** 是否存在且可访问

## 📞 支持

如果遇到问题，请提供：
- GitHub Actions 日志
- Cloud Run 服务日志
- 错误信息详情

