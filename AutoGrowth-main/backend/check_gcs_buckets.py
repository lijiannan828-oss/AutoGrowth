"""检查 GCP 项目中已有的存储桶"""

import os
from google.cloud import storage

# 设置凭证路径
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"d:\AutoGrowth-main (1)\AutoGrowth-main\backend\fleet-blend-469520-n7-23b7c649292b.json"

def check_buckets():
    """列出项目中所有的存储桶"""
    try:
        client = storage.Client(project="fleet-blend-469520-n7")
        
        print("=" * 80)
        print("GCP 项目中的存储桶列表")
        print("=" * 80)
        
        buckets = list(client.list_buckets())
        
        if not buckets:
            print("❌ 未找到任何存储桶")
            return
        
        print(f"\n找到 {len(buckets)} 个存储桶：\n")
        
        # 定义代码中使用的存储桶
        required_buckets = {
            "vigloo_source": "Pipeline 源文件存储（从 Google Drive 传输的原始文件）",
            "vigloo_processed": "Pipeline 处理后的文件存储（压制后的视频）",
            "vigloo-temp-downloads": "Pipeline 临时下载文件存储",
            "vigloo-fission-uploads": "AI 裂变素材生成 - 用户上传的源视频",
            "vigloo-fission-outputs": "AI 裂变素材生成 - 生成的变体视频输出",
        }
        
        found_buckets = {}
        
        for bucket in buckets:
            print(f"📦 {bucket.name}")
            print(f"   位置: {bucket.location}")
            print(f"   存储类别: {bucket.storage_class}")
            print(f"   创建时间: {bucket.time_created}")
            
            # 检查是否是需要的存储桶
            if bucket.name in required_buckets:
                found_buckets[bucket.name] = True
                print(f"   ✅ 用途: {required_buckets[bucket.name]}")
            else:
                print(f"   ℹ️  用途: 未在代码中定义")
            
            print()
           # 检查缺失的存储桶
        print("=" * 80)
        print("存储桶需求检查")
        print("=" * 80)
        print()
        
        missing_buckets = []
        for bucket_name, description in required_buckets.items():
            if bucket_name in found_buckets:
                print(f"✅ {bucket_name}")
                print(f"   {description}")
            else:
                print(f"❌ {bucket_name} (缺失)")
                print(f"   {description}")
                missing_buckets.append(bucket_name)
            print()
        
        if missing_buckets:
            print("=" * 80)
            print("需要创建的存储桶")
            print("=" * 80)
            print()
            print("使用以下命令创建缺失的存储桶：\n")
            for bucket_name in missing_buckets:
                print(f"gsutil mb -p fleet-blend-469520-n7 -c STANDARD -l us-central1 gs://{bucket_name}")
            print()
        else:
            print("=" * 80)
            print("✅ 所有需要的存储桶都已存在！")
            print("=" * 80)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        print(f"\n请检查：")
        print(f"1. Service Account JSON 文件路径是否正确")
        print(f"2. Service Account 是否有 Storage Admin 权限")
        print(f"3. 网络连接是否正常")

if __name__ == "__main__":
    check_buckets()

