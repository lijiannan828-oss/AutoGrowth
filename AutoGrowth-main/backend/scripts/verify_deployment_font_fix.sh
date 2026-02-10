#!/bin/bash
# 部署验证脚本：字体修复和文件路径过滤功能

set -e

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
JOB_NAME="drama-processor-job"

echo "============================================================"
echo "🚀 开始部署验证：字体修复和文件路径过滤功能"
echo "============================================================"
echo ""

# 1. 检查 GitHub Actions 部署状态
echo "1️⃣ 检查 GitHub Actions 部署状态..."
echo "   请在 GitHub 网页上查看 Actions: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo "   等待部署完成..."
echo ""

# 2. 检查 Cloud Run Job 是否更新
echo "2️⃣ 检查 Cloud Run Job 部署状态..."
LATEST_REVISION=$(gcloud run jobs describe $JOB_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.template.spec.containers[0].image)" 2>/dev/null || echo "")

if [ -n "$LATEST_REVISION" ]; then
  echo "   ✅ Job 已部署"
  echo "   镜像: $LATEST_REVISION"
else
  echo "   ⚠️  无法获取 Job 信息，请检查部署是否完成"
fi
echo ""

# 3. 等待用户触发测试任务
echo "3️⃣ 准备验证字体诊断日志..."
echo "   请在前端页面触发一个泰语或印地语的压制任务"
echo "   然后按 Enter 继续查看日志..."
read -p "   按 Enter 继续..." 

# 4. 查看字体诊断日志
echo ""
echo "4️⃣ 查看字体诊断日志..."
echo "   正在查询最近的字体诊断日志..."
echo ""

gcloud logging read "resource.type=cloud_run_job AND textPayload=~'字体诊断'" \
  --limit 50 \
  --format="table(timestamp,textPayload)" \
  --project=$PROJECT_ID \
  --freshness=1h || echo "   未找到字体诊断日志，请确认任务已执行"

echo ""
echo "5️⃣ 查看字体使用日志..."
gcloud logging read "resource.type=cloud_run_job AND textPayload=~'使用通用字体.*Sans'" \
  --limit 20 \
  --format="table(timestamp,textPayload)" \
  --project=$PROJECT_ID \
  --freshness=1h || echo "   未找到字体使用日志"

echo ""
echo "============================================================"
echo "✅ 验证完成"
echo "============================================================"
echo ""
echo "📋 验证检查清单:"
echo "   [ ] 字体诊断日志正常输出"
echo "   [ ] 使用了 'Sans' 字体（Fontconfig fallback）"
echo "   [ ] 文件路径过滤功能正常（只处理选中的文件）"
echo "   [ ] 泰语/印地语字幕正常显示（无乱码）"
echo ""

