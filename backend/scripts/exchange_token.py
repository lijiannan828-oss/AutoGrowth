#!/usr/bin/env python3
"""快速调用 OAuth Exchange 接口的脚本"""

import sys
import os
import json
import requests

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def main():
    if len(sys.argv) < 3:
        print("用法: python3 exchange_token.py <授权码> <认证token>")
        print()
        print("示例:")
        print("  python3 exchange_token.py 4/0AeanS... eyJhbGc...")
        sys.exit(1)
    
    auth_code = sys.argv[1]
    auth_token = sys.argv[2]
    
    redirect_uri = settings.google_oauth_redirect_uri or "http://localhost:8000/api/v1/oauth/exchange"
    scope = ["https://www.googleapis.com/auth/drive.readonly"]
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    
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
    
    print("🔐 正在交换授权码...")
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        token_ref = result.get("token_ref")
        
        print("✅ Token 交换成功!")
        print()
        print("响应内容:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        print("=" * 70)
        print(f"📝 Token Ref: {token_ref}")
        print("=" * 70)
        print()
        print("下一步:")
        print(f"1. 更新环境变量: export PIPELINE_DEFAULT_TOKEN_REF={token_ref}")
        print(f"2. 或更新 .env 文件: echo 'PIPELINE_DEFAULT_TOKEN_REF={token_ref}' >> backend/.env")
        print("3. 更新 GitHub Secret: PIPELINE_DEFAULT_TOKEN_REF")
        print()
        
        return token_ref
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"HTTP 状态码: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                print(f"错误详情: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()

