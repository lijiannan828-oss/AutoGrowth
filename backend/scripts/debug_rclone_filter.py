#!/usr/bin/env python3
"""Preview and validate rclone filter rules locally."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.workers.transfer.main import _compile_filter_rules


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the exact rclone filter rules that transfer worker would use.",
    )
    parser.add_argument(
        "--gdrive-path",
        required=True,
        help="完整的 GDrive 剧集路径（例如 KR Programs/KR001_SomeDrama）。",
    )
    parser.add_argument(
        "--include",
        action="append",
        required=True,
        help="需要传输的目录路径，可重复传入多次；与前端 include_folders 相同。",
    )
    parser.add_argument(
        "--output",
        default="transfer.filter",
        help="保存 filter 文件的路径（默认：transfer.filter）。",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="在终端打印规则内容，便于快速检查。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rules = _compile_filter_rules(args.include, args.gdrive_path)
    if not rules:
        raise SystemExit("未生成任何规则，请检查 --include 参数。")

    rules.append("- **")

    output_path = Path(args.output)
    output_path.write_text("\n".join(rules), encoding="utf-8")
    print(f"✅ Filter 文件已写入：{output_path.resolve()}")

    if args.print:
        print("—— 规则预览 ——")
        for line in rules:
            print(line)
        print("———————")

    print(
        "📌 调试方法：可使用下列命令验证 rclone 是否按预期匹配（请替换 remote/path）：\n"
        f"  rclone ls my-drive:\"{args.gdrive_path}\" --filter-from \"{output_path}\"\n"
        "或使用 `rclone lsd` 查看匹配到的目录，确认没有误伤/遗漏。"
    )


if __name__ == "__main__":
    main()



