# 推送到 GitHub 指南

## 当前状态

- ✅ Git 仓库已初始化
- ✅ 代码已提交（3 个提交）
- ✅ 远程仓库已配置: `https://github.com/lijiannan828/AutoGrowth.git`
- ⏳ 等待推送到 GitHub

## 推送方法

### 方法 1: 使用 SSH（推荐）

如果你已经配置了 SSH 密钥：

```bash
cd /Users/mac/AutoGrowth

# 切换到 SSH URL
git remote set-url origin git@github.com:lijiannan828/AutoGrowth.git

# 推送
git push -u origin main
```

### 方法 2: 使用 HTTPS + Personal Access Token

1. **创建 Personal Access Token**:
   - 访问: https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限: `repo` (完整仓库访问权限)
   - 生成并复制 token

2. **推送代码**:
   ```bash
   cd /Users/mac/AutoGrowth
   git push -u origin main
   ```
   - 用户名: `lijiannan828`
   - 密码: 输入你的 Personal Access Token（不是 GitHub 密码）

### 方法 3: 使用 GitHub CLI

如果你安装了 GitHub CLI:

```bash
cd /Users/mac/AutoGrowth

# 登录（如果还没有）
gh auth login

# 推送
git push -u origin main
```

## 推送后

推送成功后，GitHub Actions 会自动触发部署：

1. **监控部署**:
   - 访问: https://github.com/lijiannan828/AutoGrowth/actions
   - 查看 "Backend Deploy to Cloud Run" workflow

2. **部署时间**: 约 5-10 分钟

3. **验证部署**:
   ```bash
   # 获取服务 URL
   gcloud run services describe autogrowth-backend \
     --region us-central1 \
     --project autogrowth-477909 \
     --format 'value(status.url)'
   
   # 测试健康检查
   curl https://YOUR_SERVICE_URL/health
   ```

## 故障排查

### 问题: 认证失败

**解决方案**:
- 检查 Personal Access Token 是否有效
- 确认 token 有 `repo` 权限
- 如果使用 SSH，检查 SSH 密钥是否添加到 GitHub

### 问题: 推送被拒绝

**可能原因**:
- 远程仓库有内容（README、.gitignore 等）
- 需要先拉取: `git pull origin main --allow-unrelated-histories`

## 下一步

推送成功后，等待 GitHub Actions 完成部署，然后验证服务是否正常运行。






