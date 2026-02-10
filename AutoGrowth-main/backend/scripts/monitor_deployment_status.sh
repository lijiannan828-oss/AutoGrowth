#!/bin/bash
# Monitor deployment status and verify fixes

set -euo pipefail

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
EVENTARC_REGION="asia-northeast3"
JOB_NAME="drama-processor-job"
SERVICE_NAME="autogrowth-backend"
RELAY_SERVICE="drama-processor-relay-service"
TRANSFER_JOB_ID="f7DTMToHvkNLqBe4Bl97"

echo "=" | head -c 80
echo ""
echo "Deployment Status Monitor"
echo "=" | head -c 80
echo ""

# Check GitHub Actions status
echo "📊 GitHub Actions Status"
echo "   URL: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo "   Please check the latest workflow run status"
echo ""

# Check Cloud Run Services
echo "📋 Cloud Run Services"
echo "   Checking services..."

# Relay Service
RELAY_URL=$(gcloud run services describe "${RELAY_SERVICE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format="value(status.url)" 2>/dev/null || echo "")

if [ -n "${RELAY_URL}" ]; then
  echo "   ✅ ${RELAY_SERVICE}: ${RELAY_URL}"
else
  echo "   ⚠️  ${RELAY_SERVICE}: Not found or not accessible"
fi

# Main Backend Service
BACKEND_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format="value(status.url)" 2>/dev/null || echo "")

if [ -n "${BACKEND_URL}" ]; then
  echo "   ✅ ${SERVICE_NAME}: ${BACKEND_URL}"
else
  echo "   ⚠️  ${SERVICE_NAME}: Not found or not accessible"
fi

echo ""

# Check Eventarc Trigger
echo "📋 Eventarc Trigger Configuration"
TRIGGER_PATH=$(gcloud eventarc triggers describe drama-processor-trigger \
  --location="${EVENTARC_REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(destination.cloudRun.path)" 2>/dev/null || echo "")

if [ -n "${TRIGGER_PATH}" ]; then
  if [ "${TRIGGER_PATH}" = "/api/relay/event" ]; then
    echo "   ✅ Path: ${TRIGGER_PATH} (correct)"
  else
    echo "   ⚠️  Path: ${TRIGGER_PATH} (should be /api/relay/event)"
  fi
else
  echo "   ⚠️  Trigger not found or not accessible"
fi

echo ""

# Check Cloud Run Job configuration
echo "📋 Cloud Run Job Configuration (${JOB_NAME})"
JOB_CONFIG=$(gcloud run jobs describe "${JOB_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format="yaml(spec.template.spec.containers[0].resources,spec.parallelism,spec.template.spec.timeoutSeconds)" 2>/dev/null || echo "")

if [ -n "${JOB_CONFIG}" ]; then
  echo "${JOB_CONFIG}" | sed 's/^/   /'
else
  echo "   ⚠️  Job not found or not accessible"
fi

echo ""

# Check recent job executions
echo "📋 Recent Job Executions"
EXECUTIONS=$(gcloud run jobs executions list \
  --job "${JOB_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --limit 3 \
  --format="table(name,status.completionTime,status.succeededCount,status.failedCount,status.conditions[0].type,status.conditions[0].status)" 2>/dev/null || echo "")

if [ -n "${EXECUTIONS}" ]; then
  echo "${EXECUTIONS}" | sed 's/^/   /'
else
  echo "   ⚠️  No executions found"
fi

echo ""

# Test file pairing (if Python available)
echo "📋 File Pairing Test"
if command -v python3 >/dev/null 2>&1; then
  echo "   Running file pairing test..."
  cd "$(dirname "$0")/.." || exit 1
  if python3 -c "from app.services.pipeline_discovery_service import _is_video_file; print('✅ Video format detection available')" 2>/dev/null; then
    echo "   ✅ Video format detection module loaded successfully"
    
    # Test .mov detection
    if python3 -c "from app.services.pipeline_discovery_service import _is_video_file; assert _is_video_file('test.mov') == True; print('✅ .mov format detection works')" 2>/dev/null; then
      echo "   ✅ .mov format detection: PASSED"
    else
      echo "   ⚠️  .mov format detection: FAILED"
    fi
  else
    echo "   ⚠️  Cannot test (module not available)"
  fi
else
  echo "   ⚠️  Python3 not available, skipping test"
fi

echo ""
echo "=" | head -c 80
echo ""
echo "✅ Deployment monitoring complete"
echo ""
echo "Next steps:"
echo "1. Check GitHub Actions: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo "2. Wait for deployment to complete (~10-15 minutes)"
echo "3. Run verification tests:"
echo "   - python3 backend/scripts/test_file_pairing_with_mov.py"
echo "   - python3 backend/scripts/diagnose_auto_trigger.py"
echo "4. Monitor Relay Service logs for Eventarc events"
echo ""


