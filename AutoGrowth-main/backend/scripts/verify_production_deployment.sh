#!/bin/bash
# Script to verify production deployment and test auto-trigger functionality

set -e

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
RELAY_SERVICE="drama-processor-relay-service"
DRAMA_NAME="KR071P01S01_타임 리프 조선"

echo "================================================================================"
echo "  生产环境部署验证"
echo "================================================================================"
echo ""
echo "项目 ID: ${PROJECT_ID}"
echo "区域: ${REGION}"
echo "Relay Service: ${RELAY_SERVICE}"
echo "测试 Drama: ${DRAMA_NAME}"
echo ""

# Step 1: Check Relay Service status
echo "================================================================================"
echo "步骤 1: 检查 Relay Service 状态"
echo "================================================================================"
echo ""

RELAY_URL=$(gcloud run services describe ${RELAY_SERVICE} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format="value(status.url)" 2>/dev/null || echo "")

if [ -z "${RELAY_URL}" ]; then
  echo "❌ Relay Service 未找到或未部署"
  exit 1
fi

echo "✅ Relay Service URL: ${RELAY_URL}"
echo ""

# Step 2: Check Firestore job
echo "================================================================================"
echo "步骤 2: 检查 Firestore 中的传输任务"
echo "================================================================================"
echo ""

python3 << 'PYTHON_SCRIPT'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('backend')))

from app.core.firestore import init_firestore
from google.cloud import firestore

init_firestore()
firestore_client = firestore.Client()

drama_name = "KR071P01S01_타임 리프 조선"

query = firestore_client.collection('pipeline_jobs').where('drama_name', '==', drama_name)
jobs = list(query.limit(10).stream())

if jobs:
    print(f"✅ 找到 {len(jobs)} 个 jobs")
    print()
    
    ready_jobs = []
    for job in jobs:
        data = job.to_dict() or {}
        transfer_completed = bool(data.get('transfer_completed'))
        stage = data.get('stage')
        status = data.get('status', 'N/A')
        
        if transfer_completed and (stage == 1 or stage is None):
            ready_jobs.append((job.id, data))
            print(f"  ✅ Ready Job: {job.id}")
            print(f"     Status: {status}")
            print(f"     Stage: {stage}")
            print(f"     transfer_completed: {transfer_completed}")
            print()
    
    if ready_jobs:
        print(f"✅ 找到 {len(ready_jobs)} 个 ready jobs")
    else:
        print("⚠️  没有找到 ready jobs")
else:
    print("❌ 未找到任何 jobs")
    sys.exit(1)
PYTHON_SCRIPT

# Step 3: Test Relay Service endpoint
echo "================================================================================"
echo "步骤 3: 测试 Relay Service 端点"
echo "================================================================================"
echo ""

SIGNAL_FILE="${DRAMA_NAME}/_PROCESS_NOW.txt"
PAYLOAD=$(cat <<EOF
{
  "type": "google.cloud.storage.object.v1.finalized",
  "data": {
    "bucket": "vigloo_source",
    "name": "${SIGNAL_FILE}"
  }
}
EOF
)

echo "发送测试请求到: ${RELAY_URL}/api/relay/event"
echo "Payload:"
echo "${PAYLOAD}" | python3 -m json.tool
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "${RELAY_URL}/api/relay/event" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

HTTP_CODE=$(echo "${RESPONSE}" | tail -n1)
BODY=$(echo "${RESPONSE}" | sed '$d')

echo "响应状态码: ${HTTP_CODE}"
echo "响应内容:"
echo "${BODY}" | python3 -m json.tool 2>/dev/null || echo "${BODY}"
echo ""

if [ "${HTTP_CODE}" = "200" ]; then
  STATUS=$(echo "${BODY}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
  
  if [ "${STATUS}" = "triggered" ]; then
    echo "✅ Relay Service 成功触发处理任务"
    JOB_ID=$(echo "${BODY}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', 'N/A'))" 2>/dev/null || echo "N/A")
    echo "   处理任务 ID: ${JOB_ID}"
  elif [ "${STATUS}" = "ignored" ]; then
    REASON=$(echo "${BODY}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('reason', 'N/A'))" 2>/dev/null || echo "N/A")
    echo "⚠️  请求被忽略，原因: ${REASON}"
  else
    echo "⚠️  未知状态: ${STATUS}"
  fi
else
  echo "❌ HTTP 错误: ${HTTP_CODE}"
fi

# Step 4: Check Relay Service logs
echo ""
echo "================================================================================"
echo "步骤 4: 检查 Relay Service 日志（最近 10 条）"
echo "================================================================================"
echo ""

gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${RELAY_SERVICE}" \
  --limit 10 \
  --format "table(timestamp,textPayload)" \
  --project ${PROJECT_ID} 2>/dev/null | head -20 || echo "⚠️  无法获取日志"

echo ""
echo "================================================================================"
echo "  验证完成"
echo "================================================================================"


