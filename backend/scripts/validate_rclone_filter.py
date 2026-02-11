#!/usr/bin/env python3
"""
验证 rclone filter 函数对复杂文件结构和特殊字符的处理能力。

测试场景：
1. 深层嵌套目录结构
2. 特殊字符：[], ?, *, 空格（包括末尾空格）
3. 部分子文件夹选择
4. 文件结构保持一致性
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Tuple

from app.workers.transfer.main import (
    _build_filter_file,
    _compile_filter_rules,
    _escape_filter_component,
    _normalize_relative_path,
)


class FilterValidator:
    """验证 rclone filter 规则的正确性"""

    def __init__(self):
        self.test_cases: List[Tuple[str, str, List[str], List[str]]] = []
        # 格式: (drama_root, description, include_folders, expected_matches)

    def add_test_case(
        self,
        drama_root: str,
        description: str,
        include_folders: List[str],
        expected_matches: List[str],
    ) -> None:
        """添加测试用例"""
        self.test_cases.append((drama_root, description, include_folders, expected_matches))

    def test_escape_component(self) -> None:
        """测试 _escape_filter_component 函数"""
        print("=" * 80)
        print("测试 1: _escape_filter_component 函数")
        print("=" * 80)

        test_cases = [
            ("normal_folder", "normal_folder", "普通文件夹名"),
            ("[Final]Episodes", "[[]Final[]]Episodes", "方括号"),
            ("folder?", "folder\\?", "问号"),
            ("folder*", "folder\\*", "星号"),
            ("folder with spaces", "folder with spaces", "中间空格"),
            ("folder with trailing space ", "folder with trailing space ", "末尾空格（注意：当前可能被strip移除）"),
            ("folder[1]", "folder[[]1[]]", "方括号数字"),
            ("folder?*", "folder\\?\\*", "多个特殊字符"),
            ("[Final] Episodes", "[[]Final[]] Episodes", "方括号+空格"),
            ("folder (2024)", "folder (2024)", "圆括号（不需要转义）"),
            ("folder{test}", "folder{test}", "花括号（不需要转义）"),
        ]

        print(f"\n{'输入':<40} {'输出':<40} {'说明'}")
        print("-" * 80)
        all_passed = True
        for input_val, expected, description in test_cases:
            actual = _escape_filter_component(input_val)
            passed = actual == expected
            status = "✅" if passed else "❌"
            if not passed:
                all_passed = False
            print(f"{status} {input_val!r:<38} {actual!r:<38} {description}")
            if not passed:
                print(f"   期望: {expected!r}")

        print(f"\n{'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}\n")

    def test_normalize_relative_path(self) -> None:
        """测试 _normalize_relative_path 函数"""
        print("=" * 80)
        print("测试 2: _normalize_relative_path 函数")
        print("=" * 80)
        print("\n⚠️  注意：此函数使用 strip('/') 可能会移除路径末尾的空格！\n")

        test_cases = [
            (
                "KR Programs/KR001_Drama/[Final]Episodes",
                "KR Programs/KR001_Drama",
                "[Final]Episodes",
                "相对路径提取",
            ),
            (
                "KR Programs/KR001_Drama/[Final]Episodes ",
                "KR Programs/KR001_Drama",
                "[Final]Episodes",
                "⚠️ 末尾空格可能被移除",
            ),
            (
                "KR Programs/KR001_Drama/[Final]Episodes/subfolder",
                "KR Programs/KR001_Drama",
                "[Final]Episodes/subfolder",
                "深层路径",
            ),
            (
                "KR Programs/KR001_Drama",
                "KR Programs/KR001_Drama",
                "",
                "根目录本身",
            ),
        ]

        print(f"\n{'完整路径':<50} {'根路径':<30} {'期望相对路径':<30} {'实际相对路径':<30} {'说明'}")
        print("-" * 80)
        all_passed = True
        for full_path, root, expected, description in test_cases:
            actual = _normalize_relative_path(full_path, root)
            passed = actual == expected
            status = "✅" if passed else "⚠️"
            if not passed:
                all_passed = False
            print(
                f"{status} {full_path:<48} {root:<28} {expected!r:<28} {actual!r:<28} {description}"
            )

        print(f"\n{'✅ 所有测试通过' if all_passed else '⚠️ 部分测试需要注意'}\n")

    def test_compile_filter_rules(self) -> None:
        """测试 _compile_filter_rules 函数"""
        print("=" * 80)
        print("测试 3: _compile_filter_rules 函数")
        print("=" * 80)

        test_cases = [
            (
                "KR Programs/KR001_Drama",
                ["KR Programs/KR001_Drama/[Final]Episodes"],
                ["+ /[[]Final[]]Episodes/**"],
                "单个子文件夹，包含方括号",
            ),
            (
                "KR Programs/KR001_Drama",
                [
                    "KR Programs/KR001_Drama/[Final]Episodes",
                    "KR Programs/KR001_Drama/[Final]Subtitles",
                ],
                [
                    "+ /[[]Final[]]Episodes/**",
                    "+ /[[]Final[]]Subtitles/**",
                ],
                "多个子文件夹",
            ),
            (
                "KR Programs/KR001_Drama",
                ["KR Programs/KR001_Drama/[Final]Episodes/subfolder"],
                ["+ /[[]Final[]]Episodes/subfolder/**"],
                "深层嵌套路径",
            ),
            (
                "KR Programs/KR001_Drama",
                ["KR Programs/KR001_Drama/folder with spaces"],
                ["+ /folder with spaces/**"],
                "包含空格的文件夹名",
            ),
            (
                "KR Programs/KR001_Drama",
                ["KR Programs/KR001_Drama/folder?test"],
                ["+ /folder\\?test/**"],
                "包含问号的文件夹名",
            ),
            (
                "KR Programs/KR001_Drama",
                ["KR Programs/KR001_Drama/folder*test"],
                ["+ /folder\\*test/**"],
                "包含星号的文件夹名",
            ),
            (
                "KR Programs/KR001_Drama",
                [
                    "KR Programs/KR001_Drama/[Final]Episodes",
                    "KR Programs/KR001_Drama/[Final]Subtitles/ar_translated",
                ],
                [
                    "+ /[[]Final[]]Episodes/**",
                    "+ /[[]Final[]]Subtitles/ar_translated/**",
                ],
                "混合深度路径",
            ),
        ]

        print(f"\n{'根路径':<40} {'包含文件夹':<50} {'期望规则':<50} {'实际规则':<50} {'状态'}")
        print("-" * 80)
        all_passed = True
        for root, include_folders, expected_rules, description in test_cases:
            actual_rules = _compile_filter_rules(include_folders, root)
            passed = actual_rules == expected_rules
            status = "✅" if passed else "❌"
            if not passed:
                all_passed = False

            include_str = ", ".join(include_folders)
            expected_str = ", ".join(expected_rules)
            actual_str = ", ".join(actual_rules)

            print(f"{status} {root:<38} {include_str[:48]:<48} {expected_str[:48]:<48} {actual_str[:48]:<48}")
            if not passed:
                print(f"    说明: {description}")
                print(f"    期望: {expected_rules}")
                print(f"    实际: {actual_rules}")

        print(f"\n{'✅ 所有测试通过' if all_passed else '❌ 部分测试失败'}\n")

    def test_build_filter_file(self) -> None:
        """测试 _build_filter_file 函数"""
        print("=" * 80)
        print("测试 4: _build_filter_file 函数（生成完整 filter 文件）")
        print("=" * 80)

        test_cases = [
            (
                "KR Programs/KR001_Drama",
                ["KR Programs/KR001_Drama/[Final]Episodes"],
                "单个子文件夹",
            ),
            (
                "KR Programs/KR001_Drama",
                [
                    "KR Programs/KR001_Drama/[Final]Episodes",
                    "KR Programs/KR001_Drama/[Final]Subtitles",
                ],
                "多个子文件夹",
            ),
            (
                "KR Programs/KR001_Drama",
                [
                    "KR Programs/KR001_Drama/[Final]Episodes/subfolder1",
                    "KR Programs/KR001_Drama/[Final]Subtitles/subfolder2/deep",
                ],
                "深层嵌套路径",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            for root, include_folders, description in test_cases:
                print(f"\n测试: {description}")
                print(f"根路径: {root}")
                print(f"包含文件夹: {include_folders}")
                print("-" * 80)

                filter_file = _build_filter_file(include_folders, root, temp_dir)
                if filter_file and filter_file.exists():
                    content = filter_file.read_text(encoding="utf-8")
                    print("生成的 filter 文件内容:")
                    for i, line in enumerate(content.splitlines(), 1):
                        print(f"  {i}. {line}")
                    print("✅ Filter 文件生成成功\n")
                else:
                    print("❌ Filter 文件生成失败\n")

    def test_complex_scenarios(self) -> None:
        """测试复杂场景"""
        print("=" * 80)
        print("测试 5: 复杂场景测试")
        print("=" * 80)

        scenarios = [
            {
                "name": "场景 1: 深层嵌套 + 特殊字符",
                "drama_root": "KR Programs/KR001_Drama",
                "include_folders": [
                    "KR Programs/KR001_Drama/[Final]Episodes/Season1/[Episodes]",
                    "KR Programs/KR001_Drama/[Final]Subtitles/ar_translated",
                ],
                "description": "测试深层嵌套路径和特殊字符的组合",
            },
            {
                "name": "场景 2: 包含空格和特殊字符",
                "drama_root": "KR Programs/KR001_Drama",
                "include_folders": [
                    "KR Programs/KR001_Drama/folder with spaces",
                    "KR Programs/KR001_Drama/folder?test",
                    "KR Programs/KR001_Drama/folder*test",
                ],
                "description": "测试各种特殊字符的处理",
            },
            {
                "name": "场景 3: 部分子文件夹选择",
                "drama_root": "KR Programs/KR001_Drama",
                "include_folders": [
                    "KR Programs/KR001_Drama/[Final]Episodes",
                    "KR Programs/KR001_Drama/[Final]Subtitles/ar_translated",
                ],
                "description": "测试只选择部分子文件夹时，文件结构是否保持",
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            for scenario in scenarios:
                print(f"\n{scenario['name']}")
                print(f"说明: {scenario['description']}")
                print(f"根路径: {scenario['drama_root']}")
                print(f"包含文件夹: {scenario['include_folders']}")
                print("-" * 80)

                rules = _compile_filter_rules(scenario["include_folders"], scenario["drama_root"])
                print("生成的规则:")
                for i, rule in enumerate(rules, 1):
                    print(f"  {i}. {rule}")

                filter_file = _build_filter_file(
                    scenario["include_folders"], scenario["drama_root"], temp_dir
                )
                if filter_file and filter_file.exists():
                    content = filter_file.read_text(encoding="utf-8")
                    print("\n完整 filter 文件:")
                    print(content)
                    print("✅ 场景测试通过\n")
                else:
                    print("❌ Filter 文件生成失败\n")

    def identify_potential_issues(self) -> None:
        """识别潜在问题"""
        print("=" * 80)
        print("潜在问题分析")
        print("=" * 80)

        issues = [
            {
                "issue": "路径末尾空格可能被移除",
                "location": "_normalize_relative_path 函数中的 strip('/')",
                "impact": "如果文件夹名末尾有空格，可能会匹配失败",
                "recommendation": "考虑使用 rstrip('/') 而不是 strip('/')，或者单独处理末尾空格",
            },
            {
                "issue": "rclone filter 规则中的空格处理",
                "location": "rclone filter 文件中的路径规则",
                "impact": "rclone 的 glob 模式对空格的处理可能需要特殊考虑",
                "recommendation": "测试包含空格的文件夹名是否能正确匹配",
            },
            {
                "issue": "文件结构保持",
                "location": "rclone copy 命令",
                "impact": "使用相对路径 filter 时，rclone 应该能保持目录结构",
                "recommendation": "验证传输后的目录结构是否与源目录结构一致",
            },
            {
                "issue": "转义字符覆盖",
                "location": "_escape_filter_component 函数",
                "impact": "当前只转义了 [], ?, *，其他特殊字符可能需要处理",
                "recommendation": "根据 rclone glob 规范，确认是否需要转义其他字符",
            },
        ]

        for i, issue in enumerate(issues, 1):
            print(f"\n问题 {i}: {issue['issue']}")
            print(f"  位置: {issue['location']}")
            print(f"  影响: {issue['impact']}")
            print(f"  建议: {issue['recommendation']}")

    def run_all_tests(self) -> None:
        """运行所有测试"""
        print("\n" + "=" * 80)
        print("Rclone Filter 验证测试套件")
        print("=" * 80 + "\n")

        self.test_escape_component()
        self.test_normalize_relative_path()
        self.test_compile_filter_rules()
        self.test_build_filter_file()
        self.test_complex_scenarios()
        self.identify_potential_issues()

        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        print(
            "\n📌 下一步建议："
            "\n1. 使用实际 GDrive 数据测试 filter 规则"
            "\n2. 验证包含末尾空格的文件夹名是否能正确匹配"
            "\n3. 验证传输后的目录结构是否保持一致性"
            "\n4. 使用 rclone ls 命令验证 filter 规则的实际匹配效果"
        )


def main() -> None:
    validator = FilterValidator()
    validator.run_all_tests()


if __name__ == "__main__":
    main()

