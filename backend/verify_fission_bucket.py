"""验证 vigloo-fission-outputs 存储桶是否创建成功"""

import os
from google.cloud import storage

# 设置凭证路径
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"d:\AutoGrowth-main (1)\AutoGrowth-main\backend\fleet-blend-469520-n7-23b7c649292b.json"

def verify_fission_bucket():
    """验证 vigloo-fission-outputs 存储桶"""
    try:
        client = storage.Client(project="fleet-blend-469520-n7")
        bucket_name = "vigloo-fission-outputs"
        
        print("=" * 80)
        print(f"验证存储桶: {bucket_name}")
        print("=" * 80)
        print()
        
        # 尝试获取存储桶
        bucket = client.get_bucket(bucket_name)
        
        print(f"✅ 存储桶 '{bucket_name}' 已存在！")
        print()
        print(f"📦 存储桶详情:")
        print(f"   名称: {bucket.name}")
        print(f"   位置: {bucket.location}")
        print(f"   存储类别: {bucket.storage_class}")
        print(f"   创建时间: {bucket.time_created}")
        print(f"   URL: gs://{bucket.name}")
        print()
        
        # 测试写入权限
        print("🔍 测试写入权限...")
        test_blob = bucket.blob("test/.test_file")
        test_blob.upload_from_string("test content")
        print("✅ 写入权限正常")
        
        # 清理测试文件
        test_blob.delete()
        print("✅ 删除权限正常")
        print()
        
        print("=" * 80)
        print("✅ 存储桶配置完成，可以正常使用！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print()
        print("请检查：")
        print("1. 存储桶是否已在 Google Cloud Console 中创建")
        print("2. 存储桶名称是否为: vigloo-fission-outputs")
        print("3. Service Account 是否有访问权限")
        print()
        print("创建命令：")
        print("gsutil mb -p fleet-blend-469520-n7 -c STANDARD -l us-central1 gs://vigloo-fission-outputs")
        return False

if __name__ == "__main__":
    verify_fission_bucket()

