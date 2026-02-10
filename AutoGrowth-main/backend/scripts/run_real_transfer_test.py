#!/usr/bin/env python3
"""
执行真实的 rclone filter 测试。

从 .env 文件读取环境变量，生成 rclone 配置，然后执行测试。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    print("⚠️  python-dotenv 未安装，将使用系统环境变量")

try:
    from app.workers.transfer.main import (
        _build_filter_file,
        _compile_filter_rules,
        _exchange_refresh_token,
        _write_rclone_config,
    )
    from app.services.google_oauth_service import retrieve_refresh_token
except ImportError as e:
    print(f"❌ 无法导入模块: {e}")
    print("   请确保已安装项目依赖")
    sys.exit(1)


def print_section(title: str) -> None:
    """打印分节标题"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    """主函数"""
    # 测试参数
    gdrive_path = "US Programs/US044P01S01_Runaway Prince's Secret Vacation"
    include_folders = [
        f"{gdrive_path}/subtitles/[final]subtitles",
    ]
    drama_name = "US044P01S01_Runaway_Prince_Secret_Vacation"
    bucket_name = "vigloo_source"

    print("\n" + "=" * 80)
    print("Rclone Filter 真实环境测试")
    print("=" * 80)
    print(f"\n测试参数:")
    print(f"  GDrive 路径: {gdrive_path}")
    print(f"  包含文件夹: {include_folders}")
    print(f"  目标 Bucket: {bucket_name}")
    print(f"  目标目录: {drama_name}")

    try:
        # 步骤 1: 生成 filter 文件
        print_section("步骤 1: 生成 Filter 文件")

        rules = _compile_filter_rules(include_folders, gdrive_path)
        print("\n生成的 filter 规则:")
        for i, rule in enumerate(rules, 1):
            print(f"  {i}. {rule}")

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            filter_file = _build_filter_file(include_folders, gdrive_path, temp_dir)

            if filter_file and filter_file.exists():
                content = filter_file.read_text(encoding="utf-8")
                print("\n完整 filter 文件内容:")
                print("-" * 80)
                print(content)
                print("-" * 80)

                # 保存到当前目录
                output_filter = Path("test_transfer.filter")
                output_filter.write_text(content, encoding="utf-8")
                print(f"\n✅ Filter 文件已保存到: {output_filter.resolve()}")

        # 步骤 2: 设置 rclone 配置
        print_section("步骤 2: 设置 Rclone 配置")

        refresh_token_ref = os.environ.get("REFRESH_TOKEN_REF")
        if not refresh_token_ref:
            print("⚠️  未找到 REFRESH_TOKEN_REF 环境变量")
            print("   将尝试使用系统默认的 rclone 配置")
            rclone_config = None
        else:
            print(f"找到 REFRESH_TOKEN_REF: {refresh_token_ref}")
            try:
                refresh_token = retrieve_refresh_token(refresh_token_ref)
                drive_token = _exchange_refresh_token(refresh_token)

                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_dir = Path(tmpdir)
                    config_path = _write_rclone_config(drive_token, temp_dir=temp_dir)

                    # 保存配置到当前目录
                    output_config = Path("test_rclone.conf")
                    output_config.write_text(
                        config_path.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                    print(f"✅ Rclone 配置已生成: {output_config.resolve()}")
                    rclone_config = output_config

            except Exception as e:
                print(f"⚠️  生成 rclone 配置失败: {e}")
                print("   将尝试使用系统默认的 rclone 配置")
                rclone_config = None

        # 步骤 3: 使用 rclone lsd 验证
        print_section("步骤 3: 验证 Filter 规则（rclone lsd）")

        cmd_lsd = [
            "rclone",
            "lsd",
            f'my-drive:"{gdrive_path}"',
            "--filter-from",
            str(output_filter),
        ]

        if rclone_config:
            cmd_lsd.extend(["--config", str(rclone_config)])

        print(f"执行命令: {' '.join(cmd_lsd)}")
        print("\n匹配的目录:")
        print("-" * 80)

        try:
            result = subprocess.run(
                cmd_lsd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                if result.stdout.strip():
                    print(result.stdout)
                    print("-" * 80)
                    print("✅ 目录匹配成功")
                else:
                    print("⚠️  没有匹配到目录")
            else:
                print(f"❌ 命令执行失败")
                print(f"返回码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
        except FileNotFoundError:
            print("❌ rclone 未安装或不在 PATH 中")

        # 步骤 4: 使用 rclone ls 验证文件
        print_section("步骤 4: 验证 Filter 规则（rclone ls - 前20个文件）")

        cmd_ls = [
            "rclone",
            "ls",
            f'my-drive:"{gdrive_path}"',
            "--filter-from",
            str(output_filter),
        ]

        if rclone_config:
            cmd_ls.extend(["--config", str(rclone_config)])

        print(f"执行命令: {' '.join(cmd_ls)} | head -20")
        print("\n匹配的文件（前20个）:")
        print("-" * 80)

        try:
            result = subprocess.run(
                cmd_ls,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines and lines[0]:
                    for line in lines[:20]:
                        print(line)
                    print("-" * 80)
                    total_count = len([l for l in lines if l.strip()])
                    print(f"✅ 匹配到 {total_count} 个文件（显示前20个）")
                else:
                    print("⚠️  没有匹配到文件")
            else:
                print(f"❌ 命令执行失败")
                print(f"错误: {result.stderr}")
        except FileNotFoundError:
            print("❌ rclone 未安装")

        # 步骤 5: 询问是否执行实际传输
        print_section("步骤 5: 实际传输测试（可选）")

        print(f"\n目标路径: gs://{bucket_name}/{drama_name}/")
        print("\n⚠️  注意：这将执行实际的文件传输")
        response = input("是否执行实际传输测试？(y/N): ").strip().lower()

        if response == "y":
            print("\n开始传输...")
            print("-" * 80)

            cmd_copy = [
                "rclone",
                "copy",
                f'my-drive:"{gdrive_path}"',
                f"my-gcs-bucket:{bucket_name}/{drama_name}",
                "--filter-from",
                str(output_filter),
                "-P",
            ]

            if rclone_config:
                cmd_copy.extend(["--config", str(rclone_config)])

            print(f"执行命令: {' '.join(cmd_copy)}")
            print("")

            try:
                process = subprocess.Popen(
                    cmd_copy,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                for line in process.stdout:
                    print(line, end="", flush=True)

                return_code = process.wait()
                if return_code == 0:
                    print("\n" + "-" * 80)
                    print("✅ 传输完成")
                    print(f"\n验证传输结果:")
                    print(f"  gsutil ls -r gs://{bucket_name}/{drama_name}/")
                else:
                    print(f"\n❌ 传输失败，返回码: {return_code}")
            except FileNotFoundError:
                print("❌ rclone 未安装")
            except KeyboardInterrupt:
                print("\n\n⚠️  传输被用户中断")
        else:
            print("\n跳过实际传输测试")
            print("\n如需手动执行传输，可使用以下命令:")
            cmd_str = " ".join([
                "rclone",
                "copy",
                f'my-drive:"{gdrive_path}"',
                f"my-gcs-bucket:{bucket_name}/{drama_name}",
                "--filter-from",
                str(output_filter),
                "-P",
            ])
            if rclone_config:
                cmd_str += f" --config {rclone_config}"
            print(f"  {cmd_str}")

        print_section("测试完成")

        print("\n📌 总结:")
        print("1. Filter 文件已生成: test_transfer.filter")
        if rclone_config:
            print("2. Rclone 配置已生成: test_rclone.conf")
        print("3. 请检查上述验证结果，确认 filter 规则是否正确匹配文件")
        print("4. 如果匹配正确，可以执行实际传输测试")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

