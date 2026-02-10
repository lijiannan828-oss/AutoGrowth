#!/usr/bin/env python3
"""诊断生产环境目录树无法展开的问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.pipeline_status_service import PipelineStatusService
from app.schemas.auth import AuthenticatedUser

def main():
    print("="*70)
    print("🔍 生产环境目录树问题诊断")
    print("="*70)
    print()
    
    # 1. 检查配置
    print("1️⃣  检查配置:")
    print("-" * 70)
    print(f"   APP_ENV: {settings.app_env}")
    print(f"   PIPELINE_DEFAULT_TOKEN_REF: {settings.pipeline_default_token_ref}")
    print(f"   FIRESTORE_PROJECT_ID: {settings.firestore_project_id}")
    print(f"   FIRESTORE_NAMESPACE: {settings.firestore_namespace}")
    print(f"   GOOGLE_OAUTH_CLIENT_ID: {settings.google_oauth_client_id[:30] if settings.google_oauth_client_id else '未设置'}...")
    print()
    
    # 2. 检查 Token Ref
    if not settings.pipeline_default_token_ref:
        print("❌ PIPELINE_DEFAULT_TOKEN_REF 未设置！")
        print("   这是导致目录树无法展开的主要原因。")
        print()
        print("   解决方案:")
        print("   1. 更新 GitHub Secret: PIPELINE_DEFAULT_TOKEN_REF")
        print("   2. 或更新 Cloud Run 环境变量")
        print("   3. 重新部署服务")
        return 1
    
    print(f"✅ PIPELINE_DEFAULT_TOKEN_REF 已设置: {settings.pipeline_default_token_ref}")
    print()
    
    # 3. 测试 Token 访问
    print("2️⃣  测试 Token 访问:")
    print("-" * 70)
    
    # 创建测试用户（模拟生产环境的用户）
    test_user = AuthenticatedUser(
        email="test@example.com",
        email_prefix="test",
        name="Test User",
        picture=None,
        user_id="test-user",
        is_dev_user=False,  # 生产环境不是开发用户
        auth_token="test-token",
    )
    
    try:
        service = PipelineStatusService(acting_user=test_user)
        token_ref = service._resolve_token_ref()
        
        if not token_ref:
            print("❌ 无法解析 token_ref")
            return 1
        
        print(f"✅ Token Ref 解析成功: {token_ref}")
        
        # 测试 Google Drive 访问
        drive_service = service._build_drive_service()
        
        if not drive_service:
            print("❌ Google Drive 服务初始化失败")
            print()
            print("   可能的原因:")
            print("   1. Token Ref 对应的 refresh token 不存在或无效")
            print("   2. Google OAuth Client ID/Secret 未配置")
            print("   3. Firestore 连接问题")
            return 1
        
        print("✅ Google Drive 服务初始化成功")
        
        # 尝试列出根目录
        try:
            results = drive_service.files().list(
                q="'root' in parents and trashed=false",
                pageSize=5
            ).execute()
            files = results.get('files', [])
            print(f"✅ 成功访问 Google Drive，找到 {len(files)} 个文件/文件夹")
        except Exception as e:
            print(f"❌ Google Drive 访问失败: {e}")
            return 1
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print("3️⃣  检查 API 端点:")
    print("-" * 70)
    print("   后端 API 端点: /api/pipeline/gdrive-browse")
    print("   需要参数: drive_folder_id")
    print("   需要认证: Authorization Bearer token")
    print()
    print("   检查点:")
    print("   1. 后端服务是否正常运行")
    print("   2. API 端点是否可访问")
    print("   3. 认证 token 是否正确传递")
    print()
    
    print("="*70)
    print("✅ 诊断完成")
    print("="*70)
    print()
    print("📋 如果问题仍然存在，请检查:")
    print("   1. 生产环境的 PIPELINE_DEFAULT_TOKEN_REF 是否已更新")
    print("   2. 前端代码是否已部署到生产环境")
    print("   3. 浏览器控制台的错误信息")
    print("   4. 网络请求的响应状态码")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

