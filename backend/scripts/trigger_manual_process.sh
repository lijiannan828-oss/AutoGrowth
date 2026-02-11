#!/bin/bash
# Script to trigger a manual process job

set -e

DRAMA_NAME="${1:-}"
API_URL="${API_URL:-http://localhost:8000}"

if [ -z "$DRAMA_NAME" ]; then
    echo "用法: $0 <drama_name> [api_url]"
    echo ""
    echo "示例:"
    echo "  $0 'US009P03S01_Good Girl Gone Bad'"
    echo "  $0 'KR051P07S01_김대표의 엽기적인 부인' http://localhost:8000"
    echo ""
    echo "注意: 需要设置认证 token"
    echo "  export API_TOKEN='your_token_here'"
    exit 1
fi

if [ -z "$API_TOKEN" ]; then
    echo "错误: 需要设置 API_TOKEN 环境变量"
    echo "  export API_TOKEN='your_token_here'"
    exit 1
fi

echo "🚀 触发手动压制任务"
echo "=================="
echo "剧集名称: $DRAMA_NAME"
echo "API URL: $API_URL"
echo ""

# Trigger manual process job
RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/pipeline/process-manual" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -d "{
    \"drama_name\": \"${DRAMA_NAME}\",
    \"file_paths\": []
  }")

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Extract job_id if available
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('job_id', ''))" 2>/dev/null || echo "")

if [ -n "$JOB_ID" ]; then
    echo ""
    echo "✅ 任务已创建: $JOB_ID"
    echo ""
    echo "检查任务状态:"
    echo "  python backend/scripts/diagnose_blocked_job.py"
    echo ""
    echo "或使用 job_id:"
    echo "  python backend/scripts/diagnose_blocked_job.py $JOB_ID"
fi


