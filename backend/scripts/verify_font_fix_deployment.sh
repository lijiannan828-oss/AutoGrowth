#!/bin/bash
# 验证字体修复部署

set -e

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
JOB_NAME="drama-processor-job"
EXPECTED_COMMIT="e7f79f8"

echo "=========================================="
echo "字体修复部署验证"
echo "=========================================="
echo ""

# 1. 检查镜像是否更新
echo "1. 检查 Cloud Run Job 镜像..."
CURRENT_IMAGE=$(gcloud run jobs describe $JOB_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(spec.template.spec.template.spec.containers[0].image)' 2>/dev/null)

echo "   当前镜像: $CURRENT_IMAGE"

# Extract commit hash from image tag
IMAGE_TAG=$(echo $CURRENT_IMAGE | awk -F: '{print $NF}')
CURRENT_COMMIT=$(echo $IMAGE_TAG | cut -c1-7)

if [ "$CURRENT_COMMIT" = "$EXPECTED_COMMIT" ]; then
    echo "   ✅ 镜像已更新到最新版本 ($EXPECTED_COMMIT)"
else
    echo "   ⏳ 镜像尚未更新 (当前: $CURRENT_COMMIT, 期望: $EXPECTED_COMMIT)"
fi
echo ""

# 2. 检查 GitHub Actions 状态
echo "2. 检查 GitHub Actions 状态..."
GITHUB_STATUS=$(curl -s "https://api.github.com/repos/lijiannan828-oss/AutoGrowth/actions/runs?per_page=1" | \
    python3 -c "import sys, json; data = json.load(sys.stdin); runs = data.get('workflow_runs', []); print(runs[0]['status'] if runs else 'unknown')" 2>/dev/null || echo "unknown")

echo "   GitHub Actions 状态: $GITHUB_STATUS"
if [ "$GITHUB_STATUS" = "completed" ]; then
    echo "   ✅ 部署已完成"
elif [ "$GITHUB_STATUS" = "in_progress" ]; then
    echo "   ⏳ 部署进行中..."
else
    echo "   ⚠️  状态未知"
fi
echo ""

# 3. 验证字体包（需要运行容器才能验证）
echo "3. 字体包验证..."
echo "   预期的字体包:"
echo "     ✅ fonts-noto-cjk"
echo "     ✅ fonts-nanum"
echo "     ✅ fonts-noto-thai"
echo "     ✅ fonts-noto-devanagari"
echo "     ✅ fonts-noto-sans (新增)"
echo "     ✅ fonts-noto-sans-arabic (新增)"
echo "     ✅ fonts-noto-sans-cyrillic (新增)"
echo ""
echo "   ⚠️  字体包验证需要在容器运行时进行"
echo ""

# 4. 验证语言配置
echo "4. 语言配置验证..."
echo "   已配置的语言 (16个):"
echo "     CJK: ko, ja, zh"
echo "     Latin: en, es, fr, de, pt, it"
echo "     Southeast Asian: th, hi, id, vi"
echo "     Other: ar, ru"
echo "     Default: _default"
echo ""

# 5. 测试建议
echo "=========================================="
echo "测试建议"
echo "=========================================="
echo ""
echo "1. 等待部署完成（如果尚未完成）"
echo ""
echo "2. 触发测试任务:"
echo "   选择一个包含多种语言的剧集进行压制"
echo "   推荐测试语言: en, th, hi, ar, id"
echo ""
echo "3. 检查日志中的字体选择:"
echo "   gcloud logging read \\"
echo "     'resource.type=cloud_run_job AND textPayload=~\"使用字体\"' \\"
echo "     --limit=20 --project=$PROJECT_ID"
echo ""
echo "4. 检查字幕编码转换:"
echo "   gcloud logging read \\"
echo "     'resource.type=cloud_run_job AND textPayload=~\"字幕文件内容预览\"' \\"
echo "     --limit=10 --project=$PROJECT_ID"
echo ""
echo "5. 验证压制后的视频:"
echo "   - 下载压制后的视频"
echo "   - 检查字幕显示是否正常"
echo "   - 特别关注英文、泰语、印地语等之前有问题的语言"
echo ""


