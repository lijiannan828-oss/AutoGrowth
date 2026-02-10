"""
批量去掉 GCS 文件名中的韩文副本后缀。

韩文副本后缀: 의 사본 (意思是 "的副本")

使用方法:
    # 预览要重命名的文件
    python scripts/remove_copy_suffix.py --bucket vigloo_source --dry-run

    # 只处理特定目录
    python scripts/remove_copy_suffix.py --bucket vigloo_source --prefix "US043P02S01" --dry-run

    # 实际执行重命名
    python scripts/remove_copy_suffix.py --bucket vigloo_source --prefix "US043P02S01" --execute
"""

import argparse
import os
import re
import sys
from pathlib import Path

# 修复 Windows 终端编码问题
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 设置凭证文件路径（相对于 backend 目录）
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
CREDENTIALS_FILE = BACKEND_DIR / "fleet-blend-469520-n7-23b7c649292b.json"

if CREDENTIALS_FILE.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDENTIALS_FILE)

from google.cloud import storage


# 韩文副本后缀正则
# 匹配: 의 사본, 의 사본의 사본, 等
COPY_SUFFIX_PATTERN = re.compile(r'(의 사본)+$')


def remove_copy_suffix(name: str) -> str:
    """去掉文件名中的韩文副本后缀。"""
    return COPY_SUFFIX_PATTERN.sub('', name)


def rename_gcs_files(bucket_name: str, dry_run: bool = True, prefix: str = ""):
    """
    扫描并重命名 GCS bucket 中包含韩文副本后缀的文件。

    Args:
        bucket_name: GCS bucket 名称
        dry_run: 如果为 True，只打印要重命名的文件，不实际执行
        prefix: 可选的路径前缀，用于只处理特定目录
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    print(f"扫描 bucket: {bucket_name}", flush=True)
    if prefix:
        print(f"路径前缀: {prefix}", flush=True)
    print(f"模式: {'预览 (dry-run)' if dry_run else '执行重命名'}", flush=True)
    print("-" * 60, flush=True)

    renamed_count = 0
    error_count = 0
    skipped_count = 0

    blobs = list(bucket.list_blobs(prefix=prefix))
    total = len(blobs)
    print(f"找到 {total} 个文件", flush=True)
    print("-" * 60, flush=True)

    for i, blob in enumerate(blobs):
        old_name = blob.name

        # 检查文件名是否包含韩文副本后缀
        if '의 사본' not in old_name:
            continue

        # 去掉副本后缀
        new_name = remove_copy_suffix(old_name)

        if new_name == old_name:
            continue

        print(f"[{i+1}/{total}] 发现:", flush=True)
        print(f"  旧: {old_name}", flush=True)
        print(f"  新: {new_name}", flush=True)

        if not dry_run:
            # 检查目标文件是否已存在
            target_blob = bucket.blob(new_name)
            if target_blob.exists():
                print(f"  [SKIP] 目标文件已存在，跳过", flush=True)
                skipped_count += 1
                continue

            try:
                # GCS 重命名 = 复制 + 删除
                bucket.copy_blob(blob, bucket, new_name)
                blob.delete()
                print(f"  [OK] 已重命名", flush=True)
                renamed_count += 1
            except Exception as e:
                print(f"  [ERROR] 重命名失败: {e}", flush=True)
                error_count += 1
        else:
            renamed_count += 1

        print(flush=True)

    print("-" * 60)
    if dry_run:
        print(f"预览完成: 发现 {renamed_count} 个需要重命名的文件")
        print("使用 --execute 参数来实际执行重命名")
    else:
        print(f"执行完成:")
        print(f"  成功: {renamed_count} 个")
        print(f"  跳过: {skipped_count} 个")
        print(f"  失败: {error_count} 个")


def main():
    parser = argparse.ArgumentParser(
        description="批量去掉 GCS 文件名中的韩文副本后缀 (의 사본)"
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket 名称 (如 vigloo_source)"
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="可选的路径前缀，用于只处理特定目录"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行重命名（默认只预览）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="只预览，不实际执行（默认）"
    )

    args = parser.parse_args()
    dry_run = not args.execute

    rename_gcs_files(
        bucket_name=args.bucket,
        dry_run=dry_run,
        prefix=args.prefix
    )


if __name__ == "__main__":
    main()
