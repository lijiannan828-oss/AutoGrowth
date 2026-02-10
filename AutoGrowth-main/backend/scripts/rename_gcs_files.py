"""
批量重命名 GCS 上包含 Windows 非法字符的文件。

Windows 非法字符: \ / : * ? " < > |

使用方法:
    python scripts/rename_gcs_files.py --bucket vigloo_source --dry-run
    python scripts/rename_gcs_files.py --bucket vigloo_source --execute
    python scripts/rename_gcs_files.py --bucket vigloo_processed --execute
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


# Windows 非法字符正则（包含半角和全角）
# 半角: \ / : * ? " < > | '
# 全角: ＼ ／ ： ＊ ？ ＂ ＜ ＞ ｜
# 注意: 单引号 ' 虽然不是 Windows 非法字符，但会导致命令行解析问题
ILLEGAL_CHARS_PATTERN = re.compile(r'[\\/:*?"<>|\'＼／：＊？＂＜＞｜]')


def sanitize_filename(name: str) -> str:
    """将文件名中的 Windows 非法字符替换为下划线。"""
    return ILLEGAL_CHARS_PATTERN.sub('_', name)


def rename_gcs_files(bucket_name: str, dry_run: bool = True, prefix: str = ""):
    """
    扫描并重命名 GCS bucket 中包含非法字符的文件。

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

    blobs = bucket.list_blobs(prefix=prefix)

    for blob in blobs:
        old_name = blob.name

        # 检查整个路径（包括文件夹名称）是否包含非法字符
        # 注意：GCS 路径中的 / 是合法的目录分隔符，不需要替换
        parts = old_name.split('/')

        # 检查每个部分是否包含非法字符
        has_illegal = any(ILLEGAL_CHARS_PATTERN.search(part) for part in parts)

        if has_illegal:
            # 替换每个部分中的非法字符，保留目录结构
            new_parts = [sanitize_filename(part) for part in parts]
            new_name = '/'.join(new_parts)

            print(f"发现: {old_name}", flush=True)
            print(f"  -> {new_name}", flush=True)

            if not dry_run:
                try:
                    # GCS 重命名 = 复制 + 删除
                    new_blob = bucket.copy_blob(blob, bucket, new_name)
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
        print(f"执行完成: 成功重命名 {renamed_count} 个文件, 失败 {error_count} 个")


def main():
    parser = argparse.ArgumentParser(description="批量重命名 GCS 上包含 Windows 非法字符的文件")
    parser.add_argument(
        "--bucket",
        required=True,
        help="GCS bucket 名称 (如 vigloo_source 或 vigloo_processed)"
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

    # 如果指定了 --execute，则不是 dry-run
    dry_run = not args.execute

    rename_gcs_files(
        bucket_name=args.bucket,
        dry_run=dry_run,
        prefix=args.prefix
    )


if __name__ == "__main__":
    main()
