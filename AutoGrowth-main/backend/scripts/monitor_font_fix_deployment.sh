#!/bin/bash
# 监控字体修复部署状态

set -e

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
JOB_NAME="drama-processor-job"

echo "=========================================="
echo "字体修复部署监控"
echo "=========================================="
echo ""

# 1. 检查 GitHub Actions 状态
echo "1. 检查 GitHub Actions 部署状态..."
echo "   URL: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo ""

# 2. 检查 Cloud Run Job 镜像
echo "2. 检查 Cloud Run Job 镜像..."
CURRENT_IMAGE=$(gcloud run jobs describe $JOB_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(spec.template.spec.template.spec.containers[0].image)' 2>/dev/null || echo "N/A")

echo "   当前镜像: $CURRENT_IMAGE"
echo ""

# 3. 检查镜像构建时间
if [ "$CURRENT_IMAGE" != "N/A" ]; then
    IMAGE_TAG=$(echo $CURRENT_IMAGE | awk -F: '{print $NF}')
    echo "   镜像标签: $IMAGE_TAG"
    
    # Try to get image creation time
    IMAGE_NAME=$(echo $CURRENT_IMAGE | awk -F/ '{print $NF}' | awk -F: '{print $1}')
    echo "   镜像名称: $IMAGE_NAME"
fi

echo ""

# 4. 验证字体包
echo "3. 验证字体包安装..."
echo "   预期的字体包:"
echo "     - fonts-noto-cjk"
echo "     - fonts-nanum"
echo "     - fonts-noto-thai"
echo "     - fonts-noto-devanagari"
echo "     - fonts-noto-sans ✅ 新增"
echo "     - fonts-noto-sans-arabic ✅ 新增"
echo "     - fonts-noto-sans-cyrillic ✅ 新增"
echo ""

# 5. 验证语言配置
echo "4. 验证语言配置..."
echo "   预期的语言配置:"
echo "     - en, es, zh, ja, ko, th, hi ✅"
echo "     - ar, id, fr, de, pt, ru, it, vi ✅ 新增"
echo ""

echo "=========================================="
echo "部署后测试建议:"
echo "=========================================="
echo ""
echo "1. 触发一个包含多种语言的测试任务"
echo "2. 检查压制后的视频字幕显示:"
echo "   - 英文 (en) - 应该不再乱码"
echo "   - 泰语 (th) - 应该正常显示"
echo "   - 印地语 (hi) - 应该正常显示"
echo "   - 其他语言 - 应该正常显示"
echo ""
echo "3. 检查日志中的字体选择:"
echo "   gcloud logging read 'resource.type=cloud_run_job AND textPayload=~\"使用字体\"' --limit=20"
echo ""


