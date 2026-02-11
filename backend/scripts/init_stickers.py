"""Initialize sticker assets in Firestore."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.firestore import get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP


def init_stickers():
    """初始化贴纸素材库"""
    firestore = get_firestore_client()
    stickers_collection = firestore.collection("fission_stickers")
    
    # 示例贴纸数据
    stickers = [
        {
            "name": "爱心",
            "category": "emoji",
            "gcs_path": "gs://your-bucket/stickers/heart.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/heart.jpg",
            "animation_type": "static",
            "created_at": SERVER_TIMESTAMP,
        },
        {
            "name": "星星",
            "category": "emoji",
            "gcs_path": "gs://your-bucket/stickers/star.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/star.jpg",
            "animation_type": "static",
            "created_at": SERVER_TIMESTAMP,
        },
        {
            "name": "火焰",
            "category": "effect",
            "gcs_path": "gs://your-bucket/stickers/fire.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/fire.jpg",
            "animation_type": "animated",
            "created_at": SERVER_TIMESTAMP,
        },
        {
            "name": "闪光",
            "category": "effect",
            "gcs_path": "gs://your-bucket/stickers/sparkle.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/sparkle.jpg",
            "animation_type": "animated",
            "created_at": SERVER_TIMESTAMP,
        },
        {
            "name": "品牌Logo",
            "category": "brand",
            "gcs_path": "gs://your-bucket/stickers/logo.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/logo.jpg",
            "animation_type": "static",
            "created_at": SERVER_TIMESTAMP,
        },
        {
            "name": "限时优惠",
            "category": "text",
            "gcs_path": "gs://your-bucket/stickers/sale.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/sale.jpg",
            "animation_type": "static",
            "created_at": SERVER_TIMESTAMP,
        },
        {
            "name": "新品上市",
            "category": "text",
            "gcs_path": "gs://your-bucket/stickers/new.png",
            "thumbnail_path": "gs://your-bucket/stickers/thumbnails/new.jpg",
            "animation_type": "static",
            "created_at": SERVER_TIMESTAMP,
        },
    ]
    
    print("开始初始化贴纸素材库...")
    
    for sticker in stickers:
        doc_ref = stickers_collection.document()
        doc_ref.set(sticker)
        print(f"✓ 已添加贴纸: {sticker['name']} ({sticker['category']})")
    
    print(f"\n完成！共添加 {len(stickers)} 个贴纸素材。")


if __name__ == "__main__":
    init_stickers()

