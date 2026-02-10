# Google Drive 授权 Token 更新指引

本文档详细说明如何更新 Google Drive 的授权 token，包括获取授权码、调用 `/api/v1/oauth/exchange` 接口，以及更新 `PIPELINE_DEFAULT_TOKEN_REF` 环境变量。

## 📋 目录

1. [概述](#概述)
2. [前置条件](#前置条件)
3. [步骤1: 获取授权码](#步骤1-获取授权码)
4. [步骤2: 调用 OAuth Exchange 接口](#步骤2-调用-oauth-exchange-接口)
5. [步骤3: 更新 PIPELINE_DEFAULT_TOKEN_REF](#步骤3-更新-pipeline_default_token_ref)
6. [验证更新](#验证更新)
7. [常见问题](#常见问题)

---

## 概述

当 Google Drive 的授权 token 失效时，需要：

1. **获取新的授权码**：通过 Google OAuth 授权流程获取授权码
2. **交换授权码**：使用 `/api/v1/oauth/exchange` 接口将授权码交换为刷新令牌
3. **更新环境变量**：将返回的 `token_ref` 更新到 `PIPELINE_DEFAULT_TOKEN_REF` 环境变量

---

## 前置条件

### 1. 确认 OAuth 配置

确保以下环境变量已正确配置：

```bash
# OAuth 客户端配置
GOOGLE_OAUTH_CLIENT_ID=你的ClientID.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=你的ClientSecret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/oauth/exchange

# Token 加密密钥（用于加密存储 refresh token）
OAUTH_TOKEN_ENCRYPTION_KEY=你的32字节加密密钥

# Firestore 配置
FIRESTORE_PROJECT_ID=fleet-blend-469520-n7
FIRESTORE_NAMESPACE=short-drama-resource
```

### 2. 确认后端服务运行

确保后端服务正在运行：

```bash
cd backend
# 检查服务是否运行
curl http://localhost:8000/health
```

### 3. 确认用户认证

`/api/v1/oauth/exchange` 接口需要用户认证，确保：
- 你已经登录到系统
- 有有效的认证 token（存储在 `localStorage` 中，key: `autogrowth.idToken`）

---

## 步骤1: 获取授权码

### 方法1: 使用浏览器手动获取（推荐）

1. **构建授权 URL**:

   首先，你需要知道你的 OAuth Client ID 和 Redirect URI。然后构建授权 URL：

   ```bash
   # 设置变量
   CLIENT_ID="你的GOOGLE_OAUTH_CLIENT_ID"
   REDIRECT_URI="http://localhost:8000/api/v1/oauth/exchange"  # 或你的实际 redirect URI
   SCOPE="https://www.googleapis.com/auth/drive.readonly"
   
   # 构建授权 URL
   AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPE}&access_type=offline&prompt=consent"
   
   echo "请访问以下 URL 进行授权:"
   echo "${AUTH_URL}"
   ```

2. **访问授权 URL**:
   - 在浏览器中打开上面的 URL
   - 使用你的 Google 账号登录
   - 授予 Google Drive 访问权限
   - **重要**: 确保勾选"离线访问"（offline access），这样才能获取 refresh token

3. **获取授权码**:
   - 授权成功后，浏览器会重定向到 `redirect_uri`
   - URL 中会包含 `code` 参数，例如：
     ```
     http://localhost:8000/api/v1/oauth/exchange?code=4/0AeanS...&scope=...
     ```
   - 复制 `code` 参数的值（这是授权码）

### 方法2: 使用 OAuth Playground（备选）

1. **访问 OAuth Playground**:
   - URL: https://developers.google.com/oauthplayground/

2. **配置 OAuth 客户端**:
   - 点击右上角"设置"（齿轮图标）
   - 勾选"Use your own OAuth credentials"
   - 输入你的 `GOOGLE_OAUTH_CLIENT_ID` 和 `GOOGLE_OAUTH_CLIENT_SECRET`

3. **选择权限范围**:
   - 在左侧找到并勾选: `https://www.googleapis.com/auth/drive.readonly`

4. **授权并获取授权码**:
   - 点击"Authorize APIs"
   - 登录并授权
   - 在右侧会显示授权码（Authorization code）

---

## 步骤2: 调用 OAuth Exchange 接口

### 2.1 准备认证 Token

首先，你需要获取当前用户的认证 token：

```bash
# 方法1: 从浏览器控制台获取（前端已登录）
# 在浏览器控制台执行：
localStorage.getItem('autogrowth.idToken')

# 方法2: 通过登录接口获取（如果未登录）
# 访问 http://localhost:3001/login 进行登录
```

### 2.2 调用 Exchange 接口

使用 `curl` 或 `httpie` 调用接口：

```bash
# 设置变量
AUTH_TOKEN="你的认证token（从localStorage获取）"
AUTHORIZATION_CODE="步骤1获取的授权码"
REDIRECT_URI="http://localhost:8000/api/v1/oauth/exchange"  # 与授权时使用的相同
BACKEND_URL="http://localhost:8000"  # 或你的后端 URL

# 调用接口
curl -X POST "${BACKEND_URL}/api/v1/oauth/exchange" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "code": "'"${AUTHORIZATION_CODE}"'",
    "redirect_uri": "'"${REDIRECT_URI}"'",
    "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
  }'
```

**成功响应示例**:

```json
{
  "token_ref": "token_abc123def456...",
  "expires_in": 3599,
  "scope": ["https://www.googleapis.com/auth/drive.readonly"],
  "token_type": "Bearer"
}
```

**重要**: 保存返回的 `token_ref` 值，这是下一步需要的 `PIPELINE_DEFAULT_TOKEN_REF` 值。

### 2.3 使用 Python 脚本调用（备选）

如果 `curl` 不方便，可以使用 Python 脚本：

```python
#!/usr/bin/env python3
"""调用 OAuth Exchange 接口更新 Google Drive token"""

import requests
import sys

# 配置
BACKEND_URL = "http://localhost:8000"
AUTH_TOKEN = "你的认证token"  # 从 localStorage 获取
AUTHORIZATION_CODE = "你的授权码"  # 从步骤1获取
REDIRECT_URI = "http://localhost:8000/api/v1/oauth/exchange"

def exchange_token():
    url = f"{BACKEND_URL}/api/v1/oauth/exchange"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    payload = {
        "code": AUTHORIZATION_CODE,
        "redirect_uri": REDIRECT_URI,
        "scopes": ["https://www.googleapis.com/auth/drive.readonly"]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Token 交换成功!")
        print(f"Token Ref: {result['token_ref']}")
        print(f"Expires In: {result['expires_in']} 秒")
        print(f"Scope: {result['scope']}")
        return result['token_ref']
    else:
        print(f"❌ 交换失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        return None

if __name__ == "__main__":
    token_ref = exchange_token()
    if token_ref:
        print(f"\n📝 请将以下值更新到 PIPELINE_DEFAULT_TOKEN_REF:")
        print(f"   {token_ref}")
```

---

## 步骤3: 更新 PIPELINE_DEFAULT_TOKEN_REF

### 3.1 更新本地环境变量

**方法1: 更新 `.env` 文件**:

```bash
cd backend

# 编辑 .env 文件
echo "PIPELINE_DEFAULT_TOKEN_REF=你的token_ref值" >> .env

# 或者直接编辑文件
nano .env
# 添加或更新: PIPELINE_DEFAULT_TOKEN_REF=你的token_ref值
```

**方法2: 设置系统环境变量**:

```bash
export PIPELINE_DEFAULT_TOKEN_REF="你的token_ref值"
```

### 3.2 更新生产环境（GitHub Secrets）

1. **访问 GitHub Secrets**:
   - URL: https://github.com/你的用户名/AutoGrowth/settings/secrets/actions

2. **更新 Secret**:
   - 找到 `PIPELINE_DEFAULT_TOKEN_REF` Secret
   - 点击"Update"
   - 输入新的 `token_ref` 值
   - 点击"Update secret"

### 3.3 更新 Cloud Run 环境变量（如果直接部署）

如果 Cloud Run 服务直接使用环境变量（而不是从 Secret Manager 读取），需要更新：

```bash
# 设置变量
PROJECT_ID="fleet-blend-469520-n7"
SERVICE_NAME="drama-processor-relay-service"  # 或你的服务名称
REGION="us-central1"  # 或你的区域
NEW_TOKEN_REF="你的新token_ref值"

# 更新环境变量
gcloud run services update ${SERVICE_NAME} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --update-env-vars PIPELINE_DEFAULT_TOKEN_REF=${NEW_TOKEN_REF}
```

### 3.4 更新 Cloud Run Jobs（如果使用）

如果 `PIPELINE_DEFAULT_TOKEN_REF` 用于 Cloud Run Jobs：

```bash
# 设置变量
PROJECT_ID="fleet-blend-469520-n7"
JOB_NAME="drama-processor-job"  # 或你的 Job 名称
REGION="us-central1"
NEW_TOKEN_REF="你的新token_ref值"

# 更新 Job 环境变量
gcloud run jobs update ${JOB_NAME} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --update-env-vars PIPELINE_DEFAULT_TOKEN_REF=${NEW_TOKEN_REF}
```

---

## 验证更新

### 4.1 验证本地环境

```bash
# 检查环境变量
cd backend
python3 -c "from app.core.config import settings; print(f'Token Ref: {settings.pipeline_default_token_ref}')"

# 测试 Google Drive 访问
python3 << 'EOF'
from app.services.pipeline_status_service import PipelineStatusService
from app.schemas.auth import AuthenticatedUser

# 创建测试用户（使用你的实际用户信息）
user = AuthenticatedUser(
    user_id="test_user",
    email="your-email@example.com",
    is_dev_user=True
)

service = PipelineStatusService(acting_user=user)
drive_service = service._build_drive_service()

if drive_service:
    print("✅ Google Drive 服务初始化成功")
    # 尝试列出文件
    results = drive_service.files().list(pageSize=10).execute()
    print(f"✅ 成功访问 Google Drive，找到 {len(results.get('files', []))} 个文件")
else:
    print("❌ Google Drive 服务初始化失败")
EOF
```

### 4.2 验证生产环境

1. **检查 Firestore**:
   - 访问: https://console.firebase.google.com/project/fleet-blend-469520-n7/firestore
   - 查看集合: `short-drama-resource_oauth_tokens`
   - 确认 `token_ref` 对应的文档存在且包含加密的 `refreshToken`

2. **检查环境变量**:
   ```bash
   # 检查 Cloud Run 服务环境变量
   gcloud run services describe ${SERVICE_NAME} \
     --project=${PROJECT_ID} \
     --region=${REGION} \
     --format="value(spec.template.spec.containers[0].env)"
   ```

3. **测试功能**:
   - 访问前端页面
   - 尝试浏览 Google Drive 文件夹
   - 确认可以正常访问

---

## 常见问题

### Q1: 授权码过期了怎么办？

**A**: 授权码通常只有几分钟的有效期。如果过期，需要重新执行步骤1获取新的授权码。

### Q2: 调用 `/api/v1/oauth/exchange` 返回 401 未授权？

**A**: 
- 确保你已经登录系统
- 检查 `Authorization` header 中的 token 是否正确
- 确认 token 没有过期（从 `localStorage.getItem('autogrowth.idToken')` 获取最新 token）

### Q3: 交换失败，提示"缺少 refresh_token"？

**A**: 
- 确保在授权时勾选了"离线访问"（offline access）
- 在授权 URL 中添加 `&access_type=offline&prompt=consent` 参数
- 如果之前已经授权过，Google 可能不会再次显示同意屏幕，需要撤销之前的授权后重新授权

### Q4: 如何撤销之前的授权？

**A**: 
1. 访问: https://myaccount.google.com/permissions
2. 找到你的应用
3. 点击"移除访问权限"
4. 重新执行授权流程

### Q5: `token_ref` 存储在哪里？

**A**: `token_ref` 是 Firestore 中文档的 ID，存储在集合 `{namespace}_oauth_tokens` 中（通常是 `short-drama-resource_oauth_tokens`）。文档中包含加密的 `refreshToken`。

### Q6: 更新 `PIPELINE_DEFAULT_TOKEN_REF` 后需要重启服务吗？

**A**: 
- **本地开发**: 需要重启后端服务才能读取新的环境变量
- **Cloud Run**: 如果使用环境变量，需要重新部署服务；如果使用 Secret Manager，通常会自动读取最新版本

### Q7: 如何查看当前使用的 token_ref？

**A**: 
```bash
# 检查本地环境变量
echo $PIPELINE_DEFAULT_TOKEN_REF

# 检查 Cloud Run 服务
gcloud run services describe ${SERVICE_NAME} \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --format="value(spec.template.spec.containers[0].env[?(@.name=='PIPELINE_DEFAULT_TOKEN_REF')].value)"
```

### Q8: 可以同时有多个 token_ref 吗？

**A**: 可以。每个用户授权后会生成一个独立的 `token_ref`。`PIPELINE_DEFAULT_TOKEN_REF` 指定系统默认使用的 token。你也可以为不同用户或不同用途使用不同的 token_ref。

---

## 完整示例脚本

以下是一个完整的脚本，自动化整个流程：

```bash
#!/bin/bash
# update_google_drive_token.sh

set -e

# 配置
CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID}"
REDIRECT_URI="http://localhost:8000/api/v1/oauth/exchange"
SCOPE="https://www.googleapis.com/auth/drive.readonly"
BACKEND_URL="http://localhost:8000"

echo "🔐 Google Drive Token 更新脚本"
echo "================================"
echo ""

# 步骤1: 构建授权 URL
AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPE}&access_type=offline&prompt=consent"

echo "📋 步骤1: 获取授权码"
echo "请访问以下 URL 进行授权:"
echo "${AUTH_URL}"
echo ""
echo "授权后，请从重定向 URL 中复制 'code' 参数的值"
read -p "请输入授权码: " AUTHORIZATION_CODE

# 步骤2: 获取认证 token
echo ""
echo "📋 步骤2: 获取认证 token"
echo "请从浏览器控制台执行: localStorage.getItem('autogrowth.idToken')"
read -p "请输入认证 token: " AUTH_TOKEN

# 步骤3: 调用 Exchange 接口
echo ""
echo "📋 步骤3: 交换授权码"
RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/v1/oauth/exchange" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d "{
    \"code\": \"${AUTHORIZATION_CODE}\",
    \"redirect_uri\": \"${REDIRECT_URI}\",
    \"scopes\": [\"${SCOPE}\"]
  }")

TOKEN_REF=$(echo "${RESPONSE}" | grep -o '"token_ref":"[^"]*' | cut -d'"' -f4)

if [ -z "${TOKEN_REF}" ]; then
  echo "❌ 交换失败:"
  echo "${RESPONSE}"
  exit 1
fi

echo "✅ Token 交换成功!"
echo "Token Ref: ${TOKEN_REF}"
echo ""

# 步骤4: 更新环境变量
echo "📋 步骤4: 更新环境变量"
read -p "是否更新本地 .env 文件? (y/n): " UPDATE_ENV

if [ "${UPDATE_ENV}" = "y" ]; then
  # 更新 .env 文件
  if grep -q "PIPELINE_DEFAULT_TOKEN_REF" backend/.env 2>/dev/null; then
    sed -i.bak "s|PIPELINE_DEFAULT_TOKEN_REF=.*|PIPELINE_DEFAULT_TOKEN_REF=${TOKEN_REF}|" backend/.env
  else
    echo "PIPELINE_DEFAULT_TOKEN_REF=${TOKEN_REF}" >> backend/.env
  fi
  echo "✅ 已更新 backend/.env"
fi

read -p "是否更新 GitHub Secret? (y/n): " UPDATE_GITHUB

if [ "${UPDATE_GITHUB}" = "y" ]; then
  echo "请访问以下链接更新 GitHub Secret:"
  echo "https://github.com/你的用户名/AutoGrowth/settings/secrets/actions"
  echo "Secret 名称: PIPELINE_DEFAULT_TOKEN_REF"
  echo "Secret 值: ${TOKEN_REF}"
fi

echo ""
echo "✅ 更新完成!"
echo "请重启后端服务以使新配置生效"
```

---

## 相关文档

- [OAuth 2.0 授权流程](https://developers.google.com/identity/protocols/oauth2)
- [Google Drive API 文档](https://developers.google.com/drive/api)
- [Firestore 文档](https://firebase.google.com/docs/firestore)

---

**最后更新**: 2025-01-24
**维护者**: AutoGrowth Team

