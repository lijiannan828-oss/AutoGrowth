# Token 更新指引

本文档提供详细的 token 更新指引，包括 OAuth Client ID/Secret、Firebase 配置、服务账号密钥等。

## 📋 目录

1. [OAuth Client ID 和 Client Secret 更新](#oauth-client-id-和-client-secret-更新)
2. [Firebase 配置更新](#firebase-配置更新)
3. [OAuth Refresh Token 更新](#oauth-refresh-token-更新)
4. [服务账号密钥更新](#服务账号密钥更新)
5. [GitHub Secrets 更新](#github-secrets-更新)

---

## 1. OAuth Client ID 和 Client Secret 更新

### 1.1 获取新的 OAuth 客户端凭据

1. **访问 Google Cloud Console**:
   - URL: https://console.cloud.google.com/apis/credentials?project=fleet-blend-469520-n7
   - 或者: Google Cloud Console → APIs & Services → Credentials

2. **找到 OAuth 2.0 客户端 ID**:
   - 在"凭据"页面找到你的 OAuth 2.0 客户端 ID
   - 点击进入详情页面

3. **获取 Client ID 和 Client Secret**:
   - **Client ID**: 在详情页面顶部可见（格式：`xxx.apps.googleusercontent.com`）
   - **Client Secret**: 点击"重置密钥"或查看现有密钥（如果已创建）

### 1.2 更新本地环境变量

**后端环境变量** (`backend/.env` 或系统环境变量):

```bash
# OAuth 客户端配置
GOOGLE_OAUTH_CLIENT_ID=你的新ClientID.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=你的新ClientSecret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/oauth/exchange
```

**生产环境** (GitHub Secrets):

1. 访问 GitHub 仓库: https://github.com/你的用户名/AutoGrowth
2. 进入 **Settings → Secrets and variables → Actions**
3. 更新以下 Secrets:
   - `GOOGLE_OAUTH_CLIENT_ID`: 新的 Client ID
   - `GOOGLE_OAUTH_CLIENT_SECRET`: 新的 Client Secret
   - `GOOGLE_OAUTH_REDIRECT_URI`: 重定向 URI（如果需要更新）

### 1.3 验证更新

```bash
# 检查后端配置
cd backend
python3 -c "from app.core.config import settings; print(f'Client ID: {settings.google_oauth_client_id[:20]}...')"
```

---

## 2. Firebase 配置更新

### 2.1 获取 Firebase 配置

1. **访问 Firebase Console**:
   - URL: https://console.firebase.google.com/project/fleet-blend-469520-n7/settings/general
   - 或者: Firebase Console → Project Settings → General

2. **获取 Web App 配置**:
   - 滚动到"Your apps"部分
   - 找到你的 Web App（如果没有，点击"Add app" → Web）
   - 复制配置信息：
     - `apiKey`
     - `authDomain`
     - `projectId`
     - `storageBucket`
     - `messagingSenderId`
     - `appId`

### 2.2 更新前端环境变量

**前端环境变量** (`frontend/.env.local`):

```bash
# Firebase 配置
NEXT_PUBLIC_FIREBASE_API_KEY=你的新API密钥
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=fleet-blend-469520-n7.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=fleet-blend-469520-n7
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=fleet-blend-469520-n7.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=你的新SenderID
NEXT_PUBLIC_FIREBASE_APP_ID=你的新AppID
```

**生产环境** (Firebase Hosting 环境变量):

1. 访问 Firebase Console → Hosting
2. 进入你的站点设置
3. 更新环境变量（如果使用 Firebase Hosting 的环境变量功能）

或者，如果使用 GitHub Actions 部署：

1. 访问 GitHub 仓库 → Settings → Secrets and variables → Actions
2. 更新以下 Secrets（如果存在）:
   - `NEXT_PUBLIC_FIREBASE_API_KEY`
   - `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
   - `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
   - `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
   - `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
   - `NEXT_PUBLIC_FIREBASE_APP_ID`

### 2.3 验证更新

```bash
# 检查前端配置
cd frontend
npm run dev
# 打开浏览器访问 http://localhost:3001
# 检查浏览器控制台是否有 Firebase 初始化错误
```

---

## 3. OAuth Refresh Token 更新

### 3.1 为什么需要更新 Refresh Token？

- Refresh Token 过期或被撤销
- 需要访问新的 Google Drive 文件夹
- 需要更新权限范围

### 3.2 获取新的 Refresh Token

#### 方法1: 通过前端 OAuth 流程（推荐）

1. **启动前端服务**:
   ```bash
   cd frontend
   npm run dev
   ```

2. **访问登录页面**:
   - URL: http://localhost:3001/login
   - 点击"使用 Google 登录"

3. **授权应用**:
   - 选择你的 Google 账号
   - 授予必要的权限（Google Drive 访问等）

4. **Token 自动存储**:
   - 前端登录成功后，token 会自动存储到 `localStorage`
   - 后端会通过 `/api/v1/oauth/exchange` 端点存储 Refresh Token 到 Firestore

#### 方法2: 使用 OAuth Playground（手动）

1. **访问 OAuth Playground**:
   - URL: https://developers.google.com/oauthplayground/

2. **配置 OAuth 客户端**:
   - 点击右上角"设置"（齿轮图标）
   - 勾选"Use your own OAuth credentials"
   - 输入你的 `GOOGLE_OAUTH_CLIENT_ID` 和 `GOOGLE_OAUTH_CLIENT_SECRET`

3. **选择权限范围**:
   - 在左侧选择需要的权限（例如：`https://www.googleapis.com/auth/drive.readonly`）

4. **授权并获取 Token**:
   - 点击"Authorize APIs"
   - 登录并授权
   - 点击"Exchange authorization code for tokens"
   - 复制 `refresh_token` 值

5. **存储 Refresh Token**:
   ```bash
   # 使用后端 API 存储 token
   curl -X POST http://localhost:8000/api/v1/oauth/exchange \
     -H "Content-Type: application/json" \
     -d '{
       "code": "你的授权码",
       "token_ref": "default"
     }'
   ```

### 3.3 验证 Refresh Token

```bash
# 检查 Firestore 中的 token
# 访问 Firestore Console: https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore
# 查看集合: short-drama-resource_oauth_tokens
# 确认 token_ref="default" 的文档存在且包含 refresh_token
```

---

## 4. 服务账号密钥更新

### 4.1 创建新的服务账号密钥

1. **访问 Google Cloud Console**:
   - URL: https://console.cloud.google.com/iam-admin/serviceaccounts?project=fleet-blend-469520-n7
   - 或者: Google Cloud Console → IAM & Admin → Service Accounts

2. **选择服务账号**:
   - 找到你的服务账号（例如：`sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com`）
   - 点击进入详情页面

3. **创建新密钥**:
   - 点击"Keys"标签
   - 点击"Add Key" → "Create new key"
   - 选择"JSON"格式
   - 下载密钥文件

### 4.2 更新本地环境变量

**本地开发环境**:

```bash
# 将下载的密钥文件保存到安全位置
# 例如: backend/secrets/sa-run-prod-key.json

# 设置环境变量
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 或者添加到 .env 文件
echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json" >> backend/.env
```

### 4.3 更新生产环境（Secret Manager）

1. **上传密钥到 Secret Manager**:
   ```bash
   # 设置项目 ID
   export PROJECT_ID=fleet-blend-469520-n7
   export SECRET_NAME=sa-run-prod-key
   
   # 创建或更新 Secret
   gcloud secrets create $SECRET_NAME \
     --project=$PROJECT_ID \
     --data-file=/path/to/service-account-key.json \
     --replication-policy="automatic"
   
   # 或者更新现有 Secret
   gcloud secrets versions add $SECRET_NAME \
     --project=$PROJECT_ID \
     --data-file=/path/to/service-account-key.json
   ```

2. **验证 Secret**:
   ```bash
   # 查看 Secret 版本
   gcloud secrets versions list $SECRET_NAME --project=$PROJECT_ID
   
   # 测试读取 Secret（需要适当的权限）
   gcloud secrets versions access latest --secret=$SECRET_NAME --project=$PROJECT_ID
   ```

3. **确保 Cloud Run 服务可以访问 Secret**:
   ```bash
   # 授予服务账号访问 Secret 的权限
   gcloud secrets add-iam-policy-binding $SECRET_NAME \
     --project=$PROJECT_ID \
     --member="serviceAccount:sa-run-prod@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

### 4.4 验证更新

```bash
# 测试服务账号认证
gcloud auth activate-service-account \
  --key-file=/path/to/service-account-key.json

# 验证权限
gcloud projects get-iam-policy fleet-blend-469520-n7 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:sa-run-prod@fleet-blend-469520-n7.iam.gserviceaccount.com"
```

---

## 5. GitHub Secrets 更新

### 5.1 更新 GitHub Secrets

1. **访问 GitHub 仓库**:
   - URL: https://github.com/你的用户名/AutoGrowth
   - 进入 **Settings → Secrets and variables → Actions**

2. **更新以下 Secrets**（根据需要）:

   | Secret 名称 | 说明 | 更新时机 |
   |------------|------|---------|
   | `GOOGLE_OAUTH_CLIENT_ID` | OAuth Client ID | OAuth 客户端重新创建时 |
   | `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth Client Secret | OAuth 客户端重新创建时 |
   | `GOOGLE_OAUTH_REDIRECT_URI` | OAuth 重定向 URI | 重定向 URI 变更时 |
   | `OAUTH_TOKEN_ENCRYPTION_KEY` | Token 加密密钥 | 密钥泄露或需要轮换时 |
   | `GCP_SA_KEY` | GCP 服务账号密钥（JSON） | 服务账号密钥更新时 |
   | `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase API Key | Firebase 配置更新时 |
   | `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase Auth Domain | Firebase 配置更新时 |
   | `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase Project ID | Firebase 项目变更时 |
   | `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Firebase Storage Bucket | Storage Bucket 变更时 |
   | `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Firebase Messaging Sender ID | Firebase 配置更新时 |
   | `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase App ID | Firebase App 重新创建时 |

3. **更新 Secret**:
   - 点击要更新的 Secret
   - 点击"Update"按钮
   - 输入新值
   - 点击"Update secret"

### 5.2 验证 GitHub Secrets

```bash
# 触发一次部署来验证 Secrets 是否正确
# 推送一个空提交或修改 README
git commit --allow-empty -m "test: verify GitHub secrets"
git push
```

---

## 6. 完整更新检查清单

### ✅ 更新前检查

- [ ] 确认需要更新的 token 类型
- [ ] 备份现有的配置和密钥
- [ ] 确认新的凭据已创建并可用

### ✅ OAuth Client ID/Secret 更新

- [ ] 在 Google Cloud Console 获取新的 Client ID 和 Secret
- [ ] 更新本地 `.env` 文件
- [ ] 更新 GitHub Secrets
- [ ] 重启本地后端服务
- [ ] 验证 OAuth 登录功能

### ✅ Firebase 配置更新

- [ ] 在 Firebase Console 获取新的配置
- [ ] 更新前端 `.env.local` 文件
- [ ] 更新 GitHub Secrets（如果使用）
- [ ] 重启前端服务
- [ ] 验证 Firebase 认证功能

### ✅ OAuth Refresh Token 更新

- [ ] 通过前端 OAuth 流程获取新 token
- [ ] 或使用 OAuth Playground 手动获取
- [ ] 验证 Firestore 中的 token 已更新
- [ ] 测试 Google Drive 访问功能

### ✅ 服务账号密钥更新

- [ ] 创建新的服务账号密钥
- [ ] 更新本地 `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] 上传密钥到 Secret Manager
- [ ] 授予 Cloud Run 服务账号访问权限
- [ ] 验证服务账号权限

### ✅ GitHub Secrets 更新

- [ ] 更新所有相关的 GitHub Secrets
- [ ] 触发一次部署验证
- [ ] 检查部署日志确认无错误

### ✅ 更新后验证

- [ ] 本地环境功能正常
- [ ] 生产环境功能正常
- [ ] OAuth 登录功能正常
- [ ] Google Drive 访问功能正常
- [ ] Firebase 认证功能正常

---

## 7. 常见问题

### Q1: 更新 OAuth Client Secret 后，现有用户需要重新登录吗？

**A**: 不需要。OAuth Client Secret 主要用于服务器端交换授权码，不影响已登录用户的 session。但如果 Refresh Token 过期，用户需要重新授权。

### Q2: 如何知道 Refresh Token 是否过期？

**A**: 当访问 Google Drive API 时返回 `401 Unauthorized` 或 `invalid_grant` 错误，通常表示 Refresh Token 已过期或无效。

### Q3: 服务账号密钥更新后，需要重启 Cloud Run 服务吗？

**A**: 如果使用 Secret Manager 挂载密钥，Cloud Run 会自动读取最新版本。但如果使用环境变量，需要重新部署服务。

### Q4: Firebase 配置更新后，前端需要重新构建吗？

**A**: 是的。前端环境变量在构建时注入，需要重新构建和部署才能生效。

### Q5: 如何安全地轮换密钥？

**A**: 
1. 创建新的密钥
2. 同时配置新旧密钥（如果系统支持）
3. 逐步迁移到新密钥
4. 验证新密钥正常工作
5. 删除旧密钥

---

## 8. 相关文档

- [Google OAuth 2.0 文档](https://developers.google.com/identity/protocols/oauth2)
- [Firebase 配置文档](https://firebase.google.com/docs/web/setup)
- [Google Cloud Secret Manager 文档](https://cloud.google.com/secret-manager/docs)
- [GitHub Secrets 文档](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

---

## 9. 紧急情况处理

如果 token 泄露或需要紧急更新：

1. **立即撤销泄露的凭据**:
   - OAuth Client Secret: 在 Google Cloud Console 中重置
   - 服务账号密钥: 删除旧密钥并创建新密钥
   - Refresh Token: 在 Google Account Settings 中撤销应用访问权限

2. **更新所有相关配置**:
   - 按照上述步骤更新所有 token 和密钥
   - 确保生产环境立即更新

3. **通知相关团队**:
   - 通知团队成员需要重新授权
   - 检查是否有异常访问日志

4. **监控和验证**:
   - 检查应用日志是否有异常
   - 验证所有功能正常工作

---

**最后更新**: 2025-01-24
**维护者**: AutoGrowth Team

