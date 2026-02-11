"""上传贴纸文件到 GCS"""

import os
from pathlib import Path
from google.cloud import storage

# 配置
BUCKET_NAME = "vigloo_source"
LOCAL_STICKERS_DIR = Path(__file__).parent.parent.parent / "frontend" / "public" / "stickers"
GCS_PREFIX = "assets/stickers"

# 设置凭证
CREDENTIALS_PATH = Path(__file__).parent.parent / "fleet-blend-469520-n7-23b7c649292b.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDENTIALS_PATH)

def upload_stickers():
    """上传所有贴纸文件到 GCS"""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    uploaded = 0
    skipped = 0

    for root, dirs, files in os.walk(LOCAL_STICKERS_DIR):
        for filename in files:
            # 跳过非图片文件
            if not filename.endswith(('.png', '.gif', '.jpg', '.jpeg')):
                continue

            local_path = Path(root) / filename
            # 计算相对路径
            relative_path = local_path.relative_to(LOCAL_STICKERS_DIR)
            gcs_path = f"{GCS_PREFIX}/{relative_path}".replace("\\", "/")

            # 检查是否已存在
            blob = bucket.blob(gcs_path)
            if blob.exists():
                print(f"[SKIP] {gcs_path} (already exists)")
                skipped += 1
                continue

            # 上传
            blob.upload_from_filename(str(local_path))
            print(f"[OK] {gcs_path}")
            uploaded += 1

    print(f"\n完成! 上传: {uploaded}, 跳过: {skipped}")

if __name__ == "__main__":
    upload_stickers()
