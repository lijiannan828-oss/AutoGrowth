# 🚀 快速部署命令

## 一键部署脚本

执行以下命令完成部署：

```bash
cd /Users/mac/AutoGrowth

# 1. 添加远程仓库（如果还没有）
git remote add origin https://github.com/lijiannan828/AutoGrowth.git

# 2. 推送到 GitHub（触发自动部署）
git push -u origin main
```

## 部署后验证

```bash
# 等待 5-10 分钟后，获取服务 URL
gcloud run services describe autogrowth-backend \
  --region us-central1 \
  --project autogrowth-477909 \
  --format 'value(status.url)'

# 测试健康检查
curl https://YOUR_SERVICE_URL/health
```

## 监控部署

访问: https://github.com/lijiannan828/AutoGrowth/actions

查看 "Backend Deploy to Cloud Run" workflow 执行情况。

