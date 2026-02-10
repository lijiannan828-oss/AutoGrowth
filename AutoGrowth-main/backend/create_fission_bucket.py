"""创建 vigloo-fission-outputs 存储桶"""

import os
from google.cloud import storage

# 设置凭证路径
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"d:\AutoGrowth-main (1)\AutoGrowth-main\backend\fleet-blend-469520-n7-23b7c649292b.json"

def create_fission_bucket():
    """创建 vigloo-fission-outputs 存储桶"""
    try:
        client = storage.Client(project="fleet-blend-469520-n7")
        bucket_name = "vigloo-fission-outputs"
        
        print("=" * 80)
        print(f"创建存储桶: {bucket_name}")
        print("=" * 80)
        print()
        
        # 创建存储桶
        bucket = client.bucket(bucket_name)
        bucket.storage_class = "STANDARD"
        new_bucket = client.create_bucket(bucket, location="us-central1")
        
        print(f"✅ 存储桶 '{bucket_name}' 创建成功！")
        print()
        print(f"📦 存储桶详情:")
        print(f"   名称: {new_bucket.name}")
        print(f"   位置: {new_bucket.location}")
        print(f"   存储类别: {new_bucket.storage_class}")
        print(f"   创建时间: {new_bucket.time_created}")
        print()
        print(f"🔗 访问地址:")
        print(f"   GCS URI: gs://{new_bucket.name}")
        print(f"   HTTP URL: https://storage.googleapis.com/{new_bucket.name}/")
        print(f"   Console: https://console.cloud.google.com/storage/browser/{new_bucket.name}?project=fleet-blend-469520-n7")
        print()
        
        # 测试写入权限
        print("🔍 测试写入权限...")
        test_blob = new_bucket.blob("test/.test_file")
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
        print("可能的原因：")
        print("1. 存储桶名称已被占用（全局唯一）")
        print("2. Service Account 没有创建存储桶的权限")
        print("3. 项目配额已满")
        print()
        print("建议：在 Google Cloud Console 手动创建")
        print("https://console.cloud.google.com/storage/create-bucket?project=fleet-blend-469520-n7")
        return False

if __name__ == "__main__":
    create_fission_bucket()

