#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

export APP_ENV=development
export PYTHONPATH="${PROJECT_ROOT}"

if [[ -z "${JOB_ID:-}" ]]; then
  read -rp "请输入 Firestore JOB_ID: " JOB_ID
  export JOB_ID
fi

if [[ -z "${REFRESH_TOKEN_REF:-}" ]]; then
  read -rp "请输入 REFRESH_TOKEN_REF: " REFRESH_TOKEN_REF
  export REFRESH_TOKEN_REF
fi

echo "启动本地传输 Worker，JOB_ID=${JOB_ID}"
cd "${PROJECT_ROOT}"
python -m app.workers.transfer.main



