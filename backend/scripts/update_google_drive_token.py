#!/usr/bin/env python3
"""Google Drive Token 更新脚本（Python 版本）"""

import sys
import os
import json
import requests
from urllib.parse import urlencode

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def build_auth_url():
    """构建 Google OAuth 授权 URL"""
    client_id = settings.google_oauth_client_id
    redirect_uri = settings.google_oauth_redirect_uri or "http://localhost:8000/api/v1/oauth/exchange"
    scope = "https://www.googleapis.com/auth/drive.readonly"
    
    if not client_id:
        print("❌ 错误: GOOGLE_OAUTH_CLIENT_ID 未配置")
        return None
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return auth_url

def exchange_token(auth_code: str, auth_token: str, backend_url: str = "http://localhost:8000"):
    """调用 OAuth Exchange 接口"""
    redirect_uri = settings.google_oauth_redirect_uri or "http://localhost:8000/api/v1/oauth/exchange"
    scope = ["https://www.googleapis.com/auth/drive.readonly"]
    
    url = f"{backend_url}/api/v1/oauth/exchange"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    payload = {
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "scopes": scope
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e.response, 'text'):
            print(f"错误详情: {e.response.text}")
        return None

def update_env_file(token_ref: str, env_file: str = "backend/.env"):
    """更新 .env 文件"""
    import shutil
    from datetime import datetime
    
    if not os.path.exists(env_file):
        print(f"⚠️  {env_file} 文件不存在，将创建新文件")
        os.makedirs(os.path.dirname(env_file), exist_ok=True)
    
    # 备份原文件
    if os.path.exists(env_file):
        backup_file = f"{env_file}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(env_file, backup_file)
        print(f"✅ 已备份原文件到: {backup_file}")
    
    # 读取现有内容
    lines = []
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # 更新或添加 PIPELINE_DEFAULT_TOKEN_REF
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("PIPELINE_DEFAULT_TOKEN_REF="):
            new_lines.append(f"PIPELINE_DEFAULT_TOKEN_REF={token_ref}\n")
            updated = True
        else:
            new_lines.append(line)
    
    if not updated:
        new_lines.append(f"PIPELINE_DEFAULT_TOKEN_REF={token_ref}\n")
    
    # 写入文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✅ 已更新 {env_file}")

def main():
    print("🔐 Google Drive Token 更新脚本 (Python)")
    print("=" * 50)
    print()
    
    # 步骤1: 显示授权 URL
    auth_url = build_auth_url()
    if not auth_url:
        return 1
    
    print("📋 步骤1: 获取授权码")
    print("请访问以下 URL 进行授权:")
    print(f"   {auth_url}")
    print()
    print("⚠️  重要提示:")
    print("   1. 确保勾选'离线访问'（offline access）")
    print("   2. 授权后，浏览器会重定向到 redirect_uri")
    print("   3. 从重定向 URL 中复制 'code' 参数的值")
    print()
    
    auth_code = input("请输入授权码: ").strip()
    if not auth_code:
        print("❌ 错误: 授权码不能为空")
        return 1
    
    # 步骤2: 获取认证 token
    print()
    print("📋 步骤2: 获取认证 token")
    print("请从浏览器控制台执行以下命令获取认证 token:")
    print("   localStorage.getItem('autogrowth.idToken')")
    print()
    
    auth_token = input("请输入认证 token: ").strip()
    if not auth_token:
        print("❌ 错误: 认证 token 不能为空")
        return 1
    
    # 步骤3: 调用 Exchange 接口
    print()
    print("📋 步骤3: 交换授权码")
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    print(f"正在调用 {backend_url}/api/v1/oauth/exchange...")
    print()
    
    result = exchange_token(auth_code, auth_token, backend_url)
    if not result:
        return 1
    
    token_ref = result.get("token_ref")
    if not token_ref:
        print("❌ 错误: 响应中缺少 token_ref")
        print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return 1
    
    print("✅ Token 交换成功!")
    print(f"响应内容:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print(f"Token Ref: {token_ref}")
    print()
    
    # 步骤4: 更新环境变量
    print("📋 步骤4: 更新环境变量")
    update_env = input("是否更新本地 .env 文件? (y/n): ").strip().lower()
    
    if update_env == "y":
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        update_env_file(token_ref, env_file)
        print()
    
    print("是否更新 GitHub Secret? (y/n): ", end="")
    update_github = input().strip().lower()
    
    if update_github == "y":
        print()
        print("📋 GitHub Secret 更新指引:")
        print("1. 访问: https://github.com/你的用户名/AutoGrowth/settings/secrets/actions")
        print("2. 找到或创建 Secret: PIPELINE_DEFAULT_TOKEN_REF")
        print(f"3. 设置值为: {token_ref}")
        print()
    
    print("✅ 更新完成!")
    print()
    print("📝 下一步:")
    print("   1. 如果更新了本地 .env 文件，请重启后端服务")
    print("   2. 如果更新了 GitHub Secret，下次部署时会自动使用新值")
    print("   3. 验证 Google Drive 访问功能是否正常")
    print()
    print(f"当前 Token Ref: {token_ref}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

