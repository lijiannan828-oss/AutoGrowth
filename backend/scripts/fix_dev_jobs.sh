#!/bin/bash
# 修复开发环境创建的任务

echo "=========================================="
echo "🔧 修复开发环境创建的任务"
echo "=========================================="
echo ""

# 使用 gcloud 直接更新 Firestore
# 查找所有 PROCESSING 状态且 auth_mode=dev_default 的任务

echo "正在查找需要修复的任务..."
echo ""

# 使用 Python 脚本（需要激活虚拟环境）
cd "$(dirname "$0")/.."

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 << 'PYTHON_SCRIPT'
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.firestore import init_firestore, get_firestore_client
    from google.cloud.firestore_v1 import SERVER_TIMESTAMP
    
    init_firestore()
    firestore = get_firestore_client()
    
    jobs_ref = firestore.collection("pipeline_jobs")
    
    # 查找所有 PROCESSING 状态的任务
    processing_jobs = list(jobs_ref.where("status", "==", "PROCESSING").stream())
    
    print(f"找到 {len(processing_jobs)} 个 PROCESSING 任务")
    print()
    
    fixed_count = 0
    for job in processing_jobs:
        data = job.to_dict()
        auth_mode = data.get("auth_mode", "")
        created_by = data.get("created_by", "")
        
        # 检查是否是开发环境创建的
        if auth_mode == "dev_default" or created_by == "system":
            job_ref = jobs_ref.document(job.id)
            job_ref.update({
                "status": "QUEUED",
                "progress": "等待执行（已从开发环境重置）",
                "auth_mode": "user",
                "updated_at": SERVER_TIMESTAMP,
                "last_event": {
                    "type": "STATUS_RESET",
                    "reason": "开发环境任务重置，等待生产环境执行",
                    "timestamp": SERVER_TIMESTAMP,
                }
            })
            print(f"✅ 已修复: {job.id} ({data.get('drama_name', 'N/A')})")
            fixed_count += 1
    
    print()
    print("="*50)
    print(f"✅ 修复完成: {fixed_count}/{len(processing_jobs)} 个任务已修复")
    print("="*50)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已安装依赖: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

