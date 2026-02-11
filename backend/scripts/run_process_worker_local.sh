#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "❌ 未检测到 ffmpeg，请先安装：brew install ffmpeg"
  exit 1
fi

if [ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
  echo "❌ 请先设置 GOOGLE_APPLICATION_CREDENTIALS 指向 service account JSON"
  exit 1
fi

# Parse arguments: JOB_ID [TASK_INDEX] [TASK_COUNT]
JOB_ID="${1:-}"
TASK_INDEX="${2:-0}"
TASK_COUNT="${3:-1}"

if [ -z "${JOB_ID}" ]; then
  read -p "请输入待压制的 Firestore JOB_ID: " JOB_ID
  if [ -z "${JOB_ID}" ]; then
    echo "❌ JOB_ID 不能为空"
    exit 1
  fi
fi

# If TASK_INDEX or TASK_COUNT not provided, prompt for them
if [ -z "${2:-}" ]; then
  read -p "请输入 CLOUD_RUN_TASK_INDEX (默认: 0): " TASK_INDEX
  TASK_INDEX="${TASK_INDEX:-0}"
fi

if [ -z "${3:-}" ]; then
  read -p "请输入 CLOUD_RUN_TASK_COUNT (默认: 1): " TASK_COUNT
  TASK_COUNT="${TASK_COUNT:-1}"
fi

echo "🚀 启动本地 Process Worker"
echo "   JOB_ID: ${JOB_ID}"
echo "   CLOUD_RUN_TASK_INDEX: ${TASK_INDEX}"
echo "   CLOUD_RUN_TASK_COUNT: ${TASK_COUNT}"

export APP_ENV=development
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export JOB_ID="${JOB_ID}"
export CLOUD_RUN_TASK_INDEX="${TASK_INDEX}"
export CLOUD_RUN_TASK_COUNT="${TASK_COUNT}"

cd "${PROJECT_ROOT}"
python -m app.workers.process.main


