#!/bin/bash
# update_google_drive_token.sh
# Google Drive Token 更新脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 Google Drive Token 更新脚本${NC}"
echo "================================"
echo ""

# 检查必要的环境变量
if [ -z "${GOOGLE_OAUTH_CLIENT_ID}" ]; then
  echo -e "${RED}❌ 错误: GOOGLE_OAUTH_CLIENT_ID 未设置${NC}"
  echo "请设置环境变量或从 backend/.env 文件加载"
  exit 1
fi

# 配置
CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID}"
REDIRECT_URI="${GOOGLE_OAUTH_REDIRECT_URI:-http://localhost:8000/api/v1/oauth/exchange}"
SCOPE="https://www.googleapis.com/auth/drive.readonly"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# 步骤1: 构建授权 URL
AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPE}&access_type=offline&prompt=consent"

echo -e "${YELLOW}📋 步骤1: 获取授权码${NC}"
echo "请访问以下 URL 进行授权:"
echo -e "${GREEN}${AUTH_URL}${NC}"
echo ""
echo "⚠️  重要提示:"
echo "   1. 确保勾选'离线访问'（offline access）"
echo "   2. 授权后，浏览器会重定向到 redirect_uri"
echo "   3. 从重定向 URL 中复制 'code' 参数的值"
echo ""
read -p "请输入授权码: " AUTHORIZATION_CODE

if [ -z "${AUTHORIZATION_CODE}" ]; then
  echo -e "${RED}❌ 错误: 授权码不能为空${NC}"
  exit 1
fi

# 步骤2: 获取认证 token
echo ""
echo -e "${YELLOW}📋 步骤2: 获取认证 token${NC}"
echo "请从浏览器控制台执行以下命令获取认证 token:"
echo -e "${GREEN}localStorage.getItem('autogrowth.idToken')${NC}"
echo ""
echo "或者，如果你已经登录到前端应用，token 会自动存储在 localStorage 中"
read -p "请输入认证 token: " AUTH_TOKEN

if [ -z "${AUTH_TOKEN}" ]; then
  echo -e "${RED}❌ 错误: 认证 token 不能为空${NC}"
  exit 1
fi

# 步骤3: 调用 Exchange 接口
echo ""
echo -e "${YELLOW}📋 步骤3: 交换授权码${NC}"
echo "正在调用 ${BACKEND_URL}/api/v1/oauth/exchange..."
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BACKEND_URL}/api/v1/oauth/exchange" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d "{
    \"code\": \"${AUTHORIZATION_CODE}\",
    \"redirect_uri\": \"${REDIRECT_URI}\",
    \"scopes\": [\"${SCOPE}\"]
  }")

HTTP_CODE=$(echo "${RESPONSE}" | tail -n1)
BODY=$(echo "${RESPONSE}" | sed '$d')

if [ "${HTTP_CODE}" != "200" ]; then
  echo -e "${RED}❌ 交换失败 (HTTP ${HTTP_CODE}):${NC}"
  echo "${BODY}"
  exit 1
fi

# 解析响应
TOKEN_REF=$(echo "${BODY}" | grep -o '"token_ref":"[^"]*' | cut -d'"' -f4 || echo "")

if [ -z "${TOKEN_REF}" ]; then
  echo -e "${RED}❌ 无法解析响应中的 token_ref${NC}"
  echo "响应内容:"
  echo "${BODY}"
  exit 1
fi

echo -e "${GREEN}✅ Token 交换成功!${NC}"
echo "响应内容:"
echo "${BODY}" | python3 -m json.tool 2>/dev/null || echo "${BODY}"
echo ""
echo -e "${GREEN}Token Ref: ${TOKEN_REF}${NC}"
echo ""

# 步骤4: 更新环境变量
echo -e "${YELLOW}📋 步骤4: 更新环境变量${NC}"

# 检查 .env 文件是否存在
ENV_FILE="backend/.env"
if [ ! -f "${ENV_FILE}" ]; then
  echo "⚠️  ${ENV_FILE} 文件不存在，将创建新文件"
fi

read -p "是否更新本地 .env 文件? (y/n): " UPDATE_ENV

if [ "${UPDATE_ENV}" = "y" ] || [ "${UPDATE_ENV}" = "Y" ]; then
  # 备份原文件
  if [ -f "${ENV_FILE}" ]; then
    cp "${ENV_FILE}" "${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 已备份原文件"
  fi
  
  # 更新或添加 PIPELINE_DEFAULT_TOKEN_REF
  if grep -q "^PIPELINE_DEFAULT_TOKEN_REF=" "${ENV_FILE}" 2>/dev/null; then
    # 更新现有值
    if [[ "$OSTYPE" == "darwin"* ]]; then
      # macOS
      sed -i '' "s|^PIPELINE_DEFAULT_TOKEN_REF=.*|PIPELINE_DEFAULT_TOKEN_REF=${TOKEN_REF}|" "${ENV_FILE}"
    else
      # Linux
      sed -i "s|^PIPELINE_DEFAULT_TOKEN_REF=.*|PIPELINE_DEFAULT_TOKEN_REF=${TOKEN_REF}|" "${ENV_FILE}"
    fi
    echo -e "${GREEN}✅ 已更新 ${ENV_FILE} 中的 PIPELINE_DEFAULT_TOKEN_REF${NC}"
  else
    # 添加新行
    echo "PIPELINE_DEFAULT_TOKEN_REF=${TOKEN_REF}" >> "${ENV_FILE}"
    echo -e "${GREEN}✅ 已添加 PIPELINE_DEFAULT_TOKEN_REF 到 ${ENV_FILE}${NC}"
  fi
fi

echo ""
read -p "是否更新 GitHub Secret? (y/n): " UPDATE_GITHUB

if [ "${UPDATE_GITHUB}" = "y" ] || [ "${UPDATE_GITHUB}" = "Y" ]; then
  echo ""
  echo -e "${YELLOW}📋 GitHub Secret 更新指引:${NC}"
  echo "1. 访问: https://github.com/你的用户名/AutoGrowth/settings/secrets/actions"
  echo "2. 找到或创建 Secret: PIPELINE_DEFAULT_TOKEN_REF"
  echo "3. 设置值为: ${TOKEN_REF}"
  echo ""
fi

echo ""
echo -e "${GREEN}✅ 更新完成!${NC}"
echo ""
echo "📝 下一步:"
echo "   1. 如果更新了本地 .env 文件，请重启后端服务"
echo "   2. 如果更新了 GitHub Secret，下次部署时会自动使用新值"
echo "   3. 验证 Google Drive 访问功能是否正常"
echo ""
echo -e "${YELLOW}当前 Token Ref: ${TOKEN_REF}${NC}"

