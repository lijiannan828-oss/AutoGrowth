#!/bin/bash
# 简单的 rclone filter 测试脚本

set -e

GDRIVE_PATH="US Programs/US044P01S01_Runaway Prince's Secret Vacation"
FILTER_FILE="test_transfer.filter"

echo "================================================================================"
echo "Rclone Filter 测试"
echo "================================================================================"
echo ""
echo "GDrive 路径: ${GDRIVE_PATH}"
echo "Filter 文件: ${FILTER_FILE}"
echo ""

# 显示 filter 内容
echo "Filter 文件内容:"
echo "--------------------------------------------------------------------------------"
cat "${FILTER_FILE}"
echo "--------------------------------------------------------------------------------"
echo ""

# 检查 rclone
if ! command -v rclone &> /dev/null; then
    echo "❌ rclone 未安装"
    exit 1
fi

# 测试 1: 查看匹配的目录
echo "测试 1: 查看匹配的目录 (rclone lsd)"
echo "--------------------------------------------------------------------------------"
rclone lsd "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" 2>&1 || echo "⚠️  命令执行失败或没有匹配"
echo ""

# 测试 2: 查看匹配的文件（前10个）
echo "测试 2: 查看匹配的文件 (rclone ls - 前10个)"
echo "--------------------------------------------------------------------------------"
rclone ls "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" 2>&1 | head -10 || echo "⚠️  命令执行失败或没有匹配"
echo ""

# 统计文件数量
FILE_COUNT=$(rclone ls "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" 2>&1 | wc -l | tr -d ' ')
echo "匹配到的文件总数: ${FILE_COUNT}"
echo ""

echo "================================================================================"
echo "测试完成"
echo "================================================================================"
echo ""
echo "如需执行实际传输，可使用:"
echo "  rclone copy \"my-drive:${GDRIVE_PATH}\" my-gcs-bucket:vigloo_source/US044P01S01_Runaway_Prince_Secret_Vacation \\"
echo "    --filter-from ${FILTER_FILE} -P"

