#!/usr/bin/env python3
"""检查字幕文件编码，诊断泰语和印地语乱码问题"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import chardet
from google.cloud import storage
from app.core.config import settings


def check_subtitle_encoding(gcs_path: str):
    """检查 GCS 字幕文件的编码"""
    print(f"\n{'='*60}")
    print(f"检查字幕文件: {gcs_path}")
    print(f"{'='*60}")
    
    # Parse GCS path
    if not gcs_path.startswith("gs://"):
        print(f"❌ 无效的 GCS 路径: {gcs_path}")
        return
    
    parts = gcs_path[5:].split("/", 1)
    if len(parts) != 2:
        print(f"❌ 无效的 GCS 路径格式: {gcs_path}")
        return
    
    bucket_name, blob_name = parts
    
    # Download file
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    if not blob.exists():
        print(f"❌ 文件不存在: {gcs_path}")
        return
    
    print(f"✅ 文件存在，大小: {blob.size} bytes")
    
    # Download to memory
    raw_data = blob.download_as_bytes()
    
    # Detect encoding
    detection = chardet.detect(raw_data)
    detected_encoding = detection.get("encoding", "unknown")
    confidence = detection.get("confidence", 0)
    
    print(f"\n📊 编码检测结果:")
    print(f"  检测到的编码: {detected_encoding}")
    print(f"  置信度: {confidence:.2%}")
    
    # Try to decode with detected encoding
    if detected_encoding and detected_encoding.lower() != "unknown":
        try:
            text = raw_data.decode(detected_encoding, errors="replace")
            print(f"✅ 使用 {detected_encoding} 解码成功")
            
            # Show first few lines
            lines = text.split("\n")[:10]
            print(f"\n📄 文件内容预览 (前10行):")
            for i, line in enumerate(lines, 1):
                print(f"  {i:2d}: {line[:80]}")
        except Exception as e:
            print(f"❌ 使用 {detected_encoding} 解码失败: {e}")
    
    # Try UTF-8
    try:
        text_utf8 = raw_data.decode("utf-8", errors="replace")
        print(f"\n✅ 使用 UTF-8 解码成功")
        
        # Show first few lines
        lines = text_utf8.split("\n")[:10]
        print(f"\n📄 UTF-8 解码内容预览 (前10行):")
        for i, line in enumerate(lines, 1):
            print(f"  {i:2d}: {line[:80]}")
    except Exception as e:
        print(f"❌ UTF-8 解码失败: {e}")
    
    # Check for BOM
    if raw_data.startswith(b'\xef\xbb\xbf'):
        print(f"\n⚠️  检测到 UTF-8 BOM")
    elif raw_data.startswith(b'\xff\xfe'):
        print(f"\n⚠️  检测到 UTF-16 LE BOM")
    elif raw_data.startswith(b'\xfe\xff'):
        print(f"\n⚠️  检测到 UTF-16 BE BOM")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python check_subtitle_encoding.py <gcs_path>")
        print("示例: python check_subtitle_encoding.py gs://vigloo_source/US009P03S01_Good Girl Gone Bad/th_translated/ep001.srt")
        sys.exit(1)
    
    gcs_path = sys.argv[1]
    check_subtitle_encoding(gcs_path)


