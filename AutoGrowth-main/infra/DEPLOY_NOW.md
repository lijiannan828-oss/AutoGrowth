# 🚀 立即部署指南

## ✅ 当前状态

- [x] Git 仓库已初始化
- [x] 代码已提交到本地仓库
- [x] 所有配置文件已就绪
- [x] 服务账号权限已配置
- [x] GitHub Secrets 已配置

## 📋 部署步骤

### 步骤 1: 在 GitHub 创建仓库

1. 访问 https://github.com/new
2. 仓库名称: `AutoGrowth` (或你喜欢的名称)
3. 设置为 Private 或 Public（根据需求）
4. **不要**初始化 README、.gitignore 或 license
5. 点击 "Create repository"

### 步骤 2: 添加远程仓库并推送

```bash
cd /Users/mac/AutoGrowth

# 添加远程仓库（替换为你的 GitHub 用户名和仓库名）
git remote add origin https://github.com/lijiannan828/AutoGrowth.git

# 或者使用 SSH（如果已配置 SSH 密钥）
# git remote add origin git@github.com:lijiannan828/AutoGrowth.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

### 步骤 3: 监控部署

1. 访问 GitHub 仓库: https://github.com/lijiannan828/AutoGrowth
2. 点击 "Actions" 标签
3. 查看 "Backend Deploy to Cloud Run" workflow
4. 等待部署完成（约 5-10 分钟）

### 步骤 4: 验证部署

部署完成后，运行以下命令获取服务 URL：

```bash
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)'
```

然后测试健康检查：

```bash
# 替换 YOUR_SERVICE_URL 为上面获取的 URL
curl https://YOUR_SERVICE_URL/health
```

预期响应：
```json
{"status": "ok"}
```

## ⚠️ 重要提示

### GitHub Secrets 检查清单

确保以下 Secrets 已在 GitHub 仓库中配置：

- [x] `GCP_SA_KEY` - GCP 服务账号 JSON 密钥
- [x] `POSTGRES_PASSWORD` - 数据库密码
- [x] `CLOUD_SQL_CONN_NAME` - Cloud SQL 连接名称
- [x] `FIREBASE_AUTOGROWTH_PROJECT_ID` - GCP 项目 ID（可选，已在 workflow 中硬编码）
- [ ] `GOOGLE_SHEETS_ID` - Google Sheets ID（可选）

### 首次部署预期行为

1. **Artifact Registry 仓库创建**:
   - 仓库名称: `autogrowth-docker`
   - 位置: `us-central1`
   - 如果创建失败，检查部署服务账号权限

2. **Secret Manager Secrets 创建**:
   - `postgres-password` - 从 GitHub Secret 创建（如果不存在）
   - `gcp-sa-key` - 从 GitHub Secret 创建（如果不存在）
   - 如果 secrets 已存在，**不会覆盖**

3. **运行时服务账号权限**:
   - 自动授予访问 Secret Manager secrets 的权限

4. **Cloud Run 服务部署**:
   - 服务名称: `autogrowth-backend`
   - 区域: `us-central1`
   - 运行时服务账号: `sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`

## 🔍 故障排查

### 问题 1: 推送失败

**症状**: `git push` 失败

**解决**:
- 检查 GitHub 仓库是否存在
- 检查是否有推送权限
- 如果使用 HTTPS，可能需要输入 GitHub 用户名和 Personal Access Token

### 问题 2: GitHub Actions 失败

**症状**: Workflow 执行失败

**检查**:
1. GitHub Secrets 是否正确配置
2. 服务账号权限是否足够
3. 查看 Actions 日志了解具体错误

### 问题 3: 部署失败

**症状**: Cloud Run 部署失败

**检查**:
1. Artifact Registry 仓库是否创建成功
2. Secret Manager secrets 是否存在
3. 运行时服务账号是否有访问权限
4. Cloud SQL 连接是否允许 Cloud Run 访问

### 问题 4: 服务无法启动

**症状**: 服务部署成功但无法访问

**检查**:
1. 查看 Cloud Run 日志
2. 检查环境变量和 secrets 是否正确
3. 检查数据库连接配置

## 📞 获取帮助

如果遇到问题，请提供：
- GitHub Actions 日志链接
- Cloud Run 服务日志
- 具体错误信息

## 🎉 部署成功后

1. ✅ 获取 Cloud Run 服务 URL
2. ✅ 测试健康检查端点
3. ✅ 测试 API 端点
4. ✅ 配置前端 API URL（如果需要）
5. ✅ 设置监控和告警（可选）

