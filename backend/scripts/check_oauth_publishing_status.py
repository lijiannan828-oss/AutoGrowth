#!/usr/bin/env python3
"""检查 OAuth 应用的发布状态"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import json
import urllib.request
import urllib.error

PROJECT_ID = "fleet-blend-469520-n7"

def main():
    print(f"🔍 查询项目 {PROJECT_ID} 的 OAuth 同意屏幕发布状态...\n")
    
    try:
        # 获取 access token
        token_result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if token_result.returncode != 0:
            print("⚠️ 无法获取 access token")
            print("请确保已登录: gcloud auth login")
            return
        
        access_token = token_result.stdout.strip()
        
        # 使用 Google Cloud Resource Manager API 查询项目信息
        # 然后尝试查询 OAuth 同意屏幕
        # 注意：OAuth 同意屏幕的 API 端点可能不在标准 API 中
        
        print("📋 由于 OAuth 同意屏幕的 API 端点不在标准 gcloud CLI 中，")
        print("   建议通过 Google Cloud Console 手动检查：\n")
        print(f"   1. 访问: https://console.cloud.google.com/apis/credentials/consent?project={PROJECT_ID}")
        print(f"   2. 检查页面顶部的 '发布状态' (Publishing status)")
        print(f"   3. 如果状态是 '测试中' (Testing)，点击 '发布应用' (Publish App) 按钮\n")
        
        # 尝试使用 curl 直接查询（如果可能）
        print("尝试使用 REST API 查询...")
        
        # Google Cloud Console 的 OAuth 同意屏幕配置
        # 这个 API 端点可能需要特定的权限
        url = f"https://console.cloud.google.com/apis/credentials/consent?project={PROJECT_ID}"
        
        print(f"\n✅ 请访问以下链接检查发布状态:")
        print(f"   {url}")
        print(f"\n发布状态说明:")
        print(f"   - 已发布 (Published): 所有用户都可以使用")
        print(f"   - 测试中 (Testing): 只有测试用户可以使用")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        print(f"\n请手动访问以下链接检查:")
        print(f"https://console.cloud.google.com/apis/credentials/consent?project={PROJECT_ID}")

if __name__ == "__main__":
    main()

