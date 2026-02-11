#!/bin/bash
# Monitor CI/CD deployment status

set -euo pipefail

PROJECT_ID="fleet-blend-469520-n7"
REGION="us-central1"
JOB_NAME="drama-processor-job"
SERVICE_NAME="autogrowth-backend"
RELAY_SERVICE="drama-processor-relay-service"

echo "=" | head -c 80
echo ""
echo "CI/CD Deployment Monitor"
echo "=" | head -c 80
echo ""

# Check GitHub Actions status
echo "📊 GitHub Actions Status"
echo "   URL: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo "   Please check the latest workflow run status"
echo ""

# Check Cloud Run Job configuration
echo "📋 Cloud Run Job Configuration (drama-processor-job)"
echo "   Checking deployment..."
gcloud run jobs describe "${JOB_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format="table(
    metadata.name,
    spec.template.spec.containers[0].resources.limits.cpu,
    spec.template.spec.containers[0].resources.limits.memory,
    spec.parallelism,
    spec.template.spec.timeoutSeconds
  )" || echo "   ⚠️  Job not found or not accessible"

echo ""

# Check Relay Service
echo "📋 Relay Service Status (drama-processor-relay-service)"
RELAY_URL=$(gcloud run services describe "${RELAY_SERVICE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format="value(status.url)" 2>/dev/null || echo "")

if [ -n "${RELAY_URL}" ]; then
  echo "   ✅ Service URL: ${RELAY_URL}"
  echo "   Health check: curl -f ${RELAY_URL}/health"
else
  echo "   ⚠️  Service not found or not accessible"
fi

echo ""

# Check recent job executions
echo "📋 Recent Job Executions"
gcloud run jobs executions list \
  --job "${JOB_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --limit 5 \
  --format="table(
    metadata.name,
    status.completionTime,
    status.succeededCount,
    status.failedCount,
    status.conditions[0].type,
    status.conditions[0].status
  )" || echo "   ⚠️  No executions found"

echo ""
echo "=" | head -c 80
echo ""
echo "✅ Deployment monitoring complete"
echo ""
echo "Next steps:"
echo "1. Check GitHub Actions: https://github.com/lijiannan828-oss/AutoGrowth/actions"
echo "2. Verify Job configuration matches expected values"
echo "3. Run production test with real data"
echo ""


