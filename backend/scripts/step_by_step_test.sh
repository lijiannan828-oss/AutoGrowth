#!/bin/bash
# 逐步真实测试脚本

set -e

GDRIVE_PATH="US Programs/US044P01S01_Runaway Prince's Secret Vacation"
FILTER_FILE="test_transfer.filter"
BUCKET_NAME="vigloo_source"
DRAMA_NAME="US044P01S01_Runaway_Prince_Secret_Vacation"

echo "================================================================================"
echo "Rclone Filter 逐步真实测试"
echo "================================================================================"
echo ""
echo "测试参数:"
echo "  GDrive 路径: ${GDRIVE_PATH}"
echo "  包含文件夹: subtitles/[final]subtitles"
echo "  目标 Bucket: ${BUCKET_NAME}"
echo "  目标目录: ${DRAMA_NAME}"
echo ""

# 步骤 1: 验证 filter 文件
echo "================================================================================"
echo "步骤 1: 验证 Filter 文件"
echo "================================================================================"
if [ ! -f "${FILTER_FILE}" ]; then
    echo "❌ Filter 文件不存在: ${FILTER_FILE}"
    exit 1
fi

echo "✅ Filter 文件存在"
echo ""
echo "Filter 文件内容:"
echo "--------------------------------------------------------------------------------"
cat "${FILTER_FILE}"
echo "--------------------------------------------------------------------------------"
echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 2: 测试 GDrive 连接
echo "================================================================================"
echo "步骤 2: 测试 GDrive 连接"
echo "================================================================================"
echo "测试命令: rclone lsd \"my-drive:${GDRIVE_PATH}\""
echo ""

if rclone lsd "my-drive:${GDRIVE_PATH}" 2>&1 | head -20; then
    echo ""
    echo "✅ GDrive 连接成功"
else
    echo ""
    echo "⚠️  GDrive 连接失败或路径不存在"
    echo "   请检查路径是否正确"
fi
echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 3: 查看源目录结构
echo "================================================================================"
echo "步骤 3: 查看源目录结构"
echo "================================================================================"
echo "测试命令: rclone lsd \"my-drive:${GDRIVE_PATH}\""
echo ""

echo "源目录下的子目录:"
rclone lsd "my-drive:${GDRIVE_PATH}" 2>&1 || echo "无法列出目录"
echo ""

echo "查看 subtitles 目录:"
rclone lsd "my-drive:${GDRIVE_PATH}/subtitles" 2>&1 || echo "subtitles 目录不存在或无法访问"
echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 4: 测试 filter 规则 - 查看匹配的目录
echo "================================================================================"
echo "步骤 4: 测试 Filter 规则 - 查看匹配的目录"
echo "================================================================================"
echo "测试命令: rclone lsd \"my-drive:${GDRIVE_PATH}\" --filter-from ${FILTER_FILE}"
echo ""

MATCHED_DIRS=$(rclone lsd "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" 2>&1 || true)

if [ -n "${MATCHED_DIRS}" ] && ! echo "${MATCHED_DIRS}" | grep -q "ERROR\|error\|Failed"; then
    echo "${MATCHED_DIRS}"
    echo ""
    echo "✅ Filter 规则成功匹配到目录"
else
    echo "${MATCHED_DIRS}"
    echo ""
    echo "⚠️  Filter 规则没有匹配到目录或执行失败"
    echo "   这可能是因为："
    echo "   1. 路径不存在"
    echo "   2. Filter 规则不正确"
    echo "   3. 权限问题"
fi
echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 5: 测试 filter 规则 - 查看匹配的文件
echo "================================================================================"
echo "步骤 5: 测试 Filter 规则 - 查看匹配的文件（前20个）"
echo "================================================================================"
echo "测试命令: rclone ls \"my-drive:${GDRIVE_PATH}\" --filter-from ${FILTER_FILE}"
echo ""

MATCHED_FILES=$(rclone ls "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" 2>&1 || true)

if [ -n "${MATCHED_FILES}" ] && ! echo "${MATCHED_FILES}" | grep -q "ERROR\|error\|Failed"; then
    echo "${MATCHED_FILES}" | head -20
    echo ""
    FILE_COUNT=$(echo "${MATCHED_FILES}" | grep -v "ERROR\|error\|Failed" | wc -l | tr -d ' ')
    echo "✅ Filter 规则成功匹配到 ${FILE_COUNT} 个文件（显示前20个）"
else
    echo "${MATCHED_FILES}"
    echo ""
    echo "⚠️  Filter 规则没有匹配到文件或执行失败"
fi
echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 6: 询问是否执行实际传输
echo "================================================================================"
echo "步骤 6: 实际传输测试（可选）"
echo "================================================================================"
echo ""
echo "目标路径: gs://${BUCKET_NAME}/${DRAMA_NAME}/"
echo ""
echo "⚠️  这将执行实际的文件传输"
echo ""
read -p "是否执行实际传输测试？(y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "开始传输..."
    echo "执行命令:"
    echo "  rclone copy \"my-drive:${GDRIVE_PATH}\" my-gcs-bucket:${BUCKET_NAME}/${DRAMA_NAME} \\"
    echo "    --filter-from ${FILTER_FILE} -P"
    echo ""
    echo "--------------------------------------------------------------------------------"
    
    if rclone copy \
        "my-drive:${GDRIVE_PATH}" \
        "my-gcs-bucket:${BUCKET_NAME}/${DRAMA_NAME}" \
        --filter-from "${FILTER_FILE}" \
        -P; then
        echo ""
        echo "--------------------------------------------------------------------------------"
        echo "✅ 传输完成"
        echo ""
        echo "验证传输结果:"
        echo "  gsutil ls -r gs://${BUCKET_NAME}/${DRAMA_NAME}/"
    else
        echo ""
        echo "❌ 传输失败"
    fi
else
    echo ""
    echo "跳过实际传输测试"
    echo ""
    echo "如需手动执行传输，可使用以下命令:"
    echo "  rclone copy \"my-drive:${GDRIVE_PATH}\" my-gcs-bucket:${BUCKET_NAME}/${DRAMA_NAME} \\"
    echo "    --filter-from ${FILTER_FILE} -P"
fi

echo ""
echo "================================================================================"
echo "测试完成"
echo "================================================================================"

