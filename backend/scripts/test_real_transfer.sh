#!/bin/bash
# 真实环境测试 rclone filter 和传输

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "Rclone Filter 真实环境测试"
echo "================================================================================"

# 测试参数
GDRIVE_PATH="US Programs/US044P01S01_Runaway Prince's Secret Vacation"
INCLUDE_FOLDER="${GDRIVE_PATH}/subtitles/[final]subtitles"
DRAMA_NAME="US044P01S01_Runaway_Prince_Secret_Vacation"
BUCKET_NAME="vigloo_source"
FILTER_FILE="test_transfer.filter"

echo ""
echo "测试参数:"
echo "  GDrive 路径: ${GDRIVE_PATH}"
echo "  包含文件夹: ${INCLUDE_FOLDER}"
echo "  目标 Bucket: ${BUCKET_NAME}"
echo "  目标目录: ${DRAMA_NAME}"
echo ""

# 检查 filter 文件是否存在
if [ ! -f "${FILTER_FILE}" ]; then
    echo -e "${RED}❌ Filter 文件不存在: ${FILTER_FILE}${NC}"
    echo "   请先运行生成 filter 文件的脚本"
    exit 1
fi

echo -e "${GREEN}✅ Filter 文件已找到${NC}"
echo ""
echo "Filter 文件内容:"
echo "--------------------------------------------------------------------------------"
cat "${FILTER_FILE}"
echo "--------------------------------------------------------------------------------"
echo ""

# 检查 rclone 是否安装
if ! command -v rclone &> /dev/null; then
    echo -e "${RED}❌ rclone 未安装${NC}"
    echo "   请先安装 rclone: https://rclone.org/install/"
    exit 1
fi

echo -e "${GREEN}✅ rclone 已安装${NC}"
echo ""

# 检查 rclone 配置
RCLONE_CONFIG=""
if [ -f "test_rclone.conf" ]; then
    RCLONE_CONFIG="--config test_rclone.conf"
    echo -e "${GREEN}✅ 找到测试 rclone 配置${NC}"
else
    echo -e "${YELLOW}⚠️  未找到测试 rclone 配置，将使用系统默认配置${NC}"
fi
echo ""

# 步骤 1: 使用 rclone lsd 查看匹配的目录
echo "================================================================================"
echo "步骤 1: 查看匹配的目录结构"
echo "================================================================================"
echo ""
echo "执行命令: rclone lsd my-drive:\"${GDRIVE_PATH}\" --filter-from ${FILTER_FILE} ${RCLONE_CONFIG}"
echo ""

if rclone lsd "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" ${RCLONE_CONFIG} 2>&1; then
    echo ""
    echo -e "${GREEN}✅ 目录匹配成功${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  目录匹配失败或没有匹配到目录${NC}"
    echo "   这可能是因为："
    echo "   1. rclone 配置不正确"
    echo "   2. GDrive 路径不存在"
    echo "   3. filter 规则不匹配"
fi

echo ""
echo ""

# 步骤 2: 使用 rclone ls 查看匹配的文件
echo "================================================================================"
echo "步骤 2: 查看匹配的文件列表（前20个）"
echo "================================================================================"
echo ""
echo "执行命令: rclone ls my-drive:\"${GDRIVE_PATH}\" --filter-from ${FILTER_FILE} ${RCLONE_CONFIG} | head -20"
echo ""

MATCHED_FILES=$(rclone ls "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" ${RCLONE_CONFIG} 2>&1 | head -20 || true)

if [ -n "${MATCHED_FILES}" ]; then
    echo "${MATCHED_FILES}"
    echo ""
    FILE_COUNT=$(rclone ls "my-drive:${GDRIVE_PATH}" --filter-from "${FILTER_FILE}" ${RCLONE_CONFIG} 2>&1 | wc -l | tr -d ' ')
    echo -e "${GREEN}✅ 匹配到 ${FILE_COUNT} 个文件${NC}"
else
    echo -e "${YELLOW}⚠️  没有匹配到文件或命令执行失败${NC}"
fi

echo ""
echo ""

# 步骤 3: 询问是否执行实际传输
echo "================================================================================"
echo "步骤 3: 实际传输测试（可选）"
echo "================================================================================"
echo ""
echo "目标路径: gs://${BUCKET_NAME}/${DRAMA_NAME}/"
echo ""
read -p "是否执行实际传输测试？(y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "执行命令:"
    echo "  rclone copy my-drive:\"${GDRIVE_PATH}\" my-gcs-bucket:${BUCKET_NAME}/${DRAMA_NAME} \\"
    echo "    --filter-from ${FILTER_FILE} ${RCLONE_CONFIG} -P"
    echo ""
    echo "开始传输..."
    echo ""
    
    if rclone copy "my-drive:${GDRIVE_PATH}" "my-gcs-bucket:${BUCKET_NAME}/${DRAMA_NAME}" \
        --filter-from "${FILTER_FILE}" ${RCLONE_CONFIG} -P; then
        echo ""
        echo -e "${GREEN}✅ 传输完成${NC}"
        echo ""
        echo "验证传输结果:"
        echo "  gsutil ls -r gs://${BUCKET_NAME}/${DRAMA_NAME}/"
    else
        echo ""
        echo -e "${RED}❌ 传输失败${NC}"
    fi
else
    echo ""
    echo "跳过实际传输测试"
    echo ""
    echo "如需手动执行传输，可使用以下命令:"
    echo "  rclone copy my-drive:\"${GDRIVE_PATH}\" my-gcs-bucket:${BUCKET_NAME}/${DRAMA_NAME} \\"
    echo "    --filter-from ${FILTER_FILE} ${RCLONE_CONFIG} -P"
fi

echo ""
echo "================================================================================"
echo "测试完成"
echo "================================================================================"

