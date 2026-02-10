"""手动触发指定的 job（绕过环境检查）

使用方法:
    python -m backend.scripts.manual_trigger_job <job_id>
    
示例:
    python -m backend.scripts.manual_trigger_job yuwKMUrqkePQWoAfNFZe
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore
from app.services.concurrency_service import ConcurrencyService
from google.cloud import run_v2
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from app.core.config import settings


def manual_trigger_job(job_id: str):
    """手动触发指定的 job（绕过环境检查）"""
    print("=" * 60)
    print(f"手动触发 Job: {job_id}")
    print("=" * 60)
    
    init_firestore()
    firestore_client = get_firestore_client()
    
    # 1. 检查 job 信息
    print("\n1. 检查 job 信息...")
    job_ref = firestore_client.collection("pipeline_jobs").document(job_id)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"❌ Job {job_id} 不存在")
        return False
    
    job_data = job_snapshot.to_dict() or {}
    drama_name = job_data.get('drama_name')
    
    if not drama_name:
        print(f"❌ Job {job_id} 缺少 drama_name")
        return False
    
    print(f"   Drama Name: {drama_name}")
    print(f"   Status: {job_data.get('status', 'N/A')}")
    
    # 2. 检查 PROCESSOR_JOB_NAME
    job_name = settings.process_job_name.strip()
    if not job_name:
        # 尝试从环境变量获取
        job_name = os.environ.get('PROCESSOR_JOB_NAME', '').strip()
    
    if not job_name:
        print(f"\n❌ PROCESSOR_JOB_NAME 未配置")
        print("   请设置环境变量 PROCESSOR_JOB_NAME")
        return False
    
    print(f"\n2. 使用 Job Name: {job_name}")
    
    # 3. 直接触发 Cloud Run Job（绕过环境检查）
    print("\n3. 触发 Cloud Run Job...")
    try:
        # 使用 ConcurrencyService 的 _trigger_cloud_run_job 方法
        service = ConcurrencyService()
        operation = service._trigger_cloud_run_job(job_id, drama_name)
        print(f"✅ 触发成功: {operation}")
        
        # 更新 job 状态
        job_ref.update({
            "status": "PROCESSING",
            "progress": "任务已手动触发",
            "updated_at": SERVER_TIMESTAMP,
        })
        print("✅ 已更新 job 状态为 PROCESSING")
        
        return True
    except Exception as e:
        print(f"❌ 触发失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='手动触发指定的 job（绕过环境检查）')
    parser.add_argument('job_id', help='要触发的 job ID')
    
    args = parser.parse_args()
    
    # 检查认证
    creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds:
        print("⚠️  警告: GOOGLE_APPLICATION_CREDENTIALS 未设置")
        print("   需要 GCP 认证才能访问 Firestore 和 Cloud Run")
        print()
    
    success = manual_trigger_job(args.job_id)
    sys.exit(0 if success else 1)

