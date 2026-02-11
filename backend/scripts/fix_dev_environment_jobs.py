#!/usr/bin/env python3
"""修复开发环境创建的任务，将其状态更新为 QUEUED 以便在生产环境重新执行"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# 设置环境变量（如果需要）
os.environ.setdefault("APP_ENV", "production")

from app.core.firestore import init_firestore, get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

def main():
    print("="*70)
    print("🔧 修复开发环境创建的任务")
    print("="*70)
    print()
    
    try:
        init_firestore()
        firestore = get_firestore_client()
    except Exception as e:
        print(f"❌ Firestore 初始化失败: {e}")
        print("   请确保已设置 GOOGLE_APPLICATION_CREDENTIALS 或已运行 gcloud auth application-default login")
        sys.exit(1)
    
    jobs_ref = firestore.collection("pipeline_jobs")
    
    # 查找所有 PROCESSING 状态的任务
    print("🔍 正在查找 PROCESSING 状态的任务...")
    processing_jobs = list(jobs_ref.where("status", "==", "PROCESSING").stream())
    
    if not processing_jobs:
        print("✅ 未找到 PROCESSING 状态的任务")
        return
    
    print(f"找到 {len(processing_jobs)} 个 PROCESSING 任务")
    print()
    
    # 查找需要修复的任务（开发环境创建的）
    jobs_to_fix = []
    for job in processing_jobs:
        data = job.to_dict()
        auth_mode = data.get("auth_mode", "")
        created_by = data.get("created_by", "")
        created_by_name = data.get("created_by_name", "")
        
        # 检查是否是开发环境创建的
        is_dev_job = (
            auth_mode == "dev_default" or
            created_by == "system" or
            created_by_name == "Batch Reprocess Script" or
            (created_by and "dev" in created_by.lower())
        )
        
        if is_dev_job:
            jobs_to_fix.append({
                "id": job.id,
                "drama_name": data.get("drama_name", "N/A"),
                "status": data.get("status"),
                "auth_mode": auth_mode,
                "created_by": created_by,
                "created_at": data.get("created_at"),
            })
    
    if not jobs_to_fix:
        print("✅ 未找到需要修复的任务（所有任务都是生产环境创建的）")
        return
    
    print(f"找到 {len(jobs_to_fix)} 个需要修复的任务:")
    print()
    for job in jobs_to_fix:
        print(f"  - {job['id']}: {job['drama_name']}")
        print(f"    状态: {job['status']}, auth_mode: {job['auth_mode']}, created_by: {job['created_by']}")
    print()
    
    # 确认修复
    print("将执行以下操作:")
    print("  1. 将任务状态更新为 QUEUED")
    print("  2. 更新 progress 信息")
    print("  3. 更新 auth_mode 为 'user'（生产环境）")
    print("  4. 添加 last_event 记录")
    print()
    
    # 执行修复
    fixed_count = 0
    failed_count = 0
    
    for job_info in jobs_to_fix:
        job_id = job_info["id"]
        job_ref = jobs_ref.document(job_id)
        
        try:
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
            print(f"✅ 已修复: {job_id} ({job_info['drama_name']})")
            fixed_count += 1
        except Exception as e:
            print(f"❌ 修复失败 {job_id}: {e}")
            failed_count += 1
    
    print()
    print("="*70)
    print(f"✅ 修复完成:")
    print(f"   成功: {fixed_count}/{len(jobs_to_fix)}")
    if failed_count > 0:
        print(f"   失败: {failed_count}/{len(jobs_to_fix)}")
    print("="*70)
    print()
    print("📋 下一步:")
    print("   这些任务现在处于 QUEUED 状态，会在生产环境的 Cloud Run 中执行")
    print("   请运行: APP_ENV=production python3 scripts/batch_reprocess_th_hi_subtitles.py")

if __name__ == "__main__":
    main()
