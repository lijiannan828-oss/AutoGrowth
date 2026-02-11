#!/usr/bin/env python3
"""检查生产环境 Cloud Run 的队列状态"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import init_firestore, get_firestore_client

def main():
    print("="*70)
    print("🔍 检查生产环境并发控制状态")
    print("="*70)
    print()
    
    try:
        init_firestore()
        firestore = get_firestore_client()
    except Exception as e:
        print(f"❌ Firestore 初始化失败: {e}")
        print("   请确保已设置 GOOGLE_APPLICATION_CREDENTIALS 或已运行 gcloud auth application-default login")
        sys.exit(1)
    
    # 检查并发控制文档
    concurrency_ref = firestore.collection("system_config").document("concurrency_control")
    concurrency_snapshot = concurrency_ref.get()
    
    if not concurrency_snapshot.exists:
        print("⚠️  并发控制文档不存在")
        print("   这可能是正常的，如果没有任务在运行")
        return
    
    concurrency_data = concurrency_snapshot.to_dict() or {}
    
    max_concurrent = concurrency_data.get("max_concurrent_jobs", 1)
    running_job_ids = concurrency_data.get("running_job_ids", [])
    queue = concurrency_data.get("queue", [])
    updated_at = concurrency_data.get("updated_at", "N/A")
    
    print("📊 并发控制状态:")
    print(f"   最大并发数: {max_concurrent}")
    print(f"   运行中的任务数: {len(running_job_ids)}")
    print(f"   队列中的任务数: {len(queue)}")
    print(f"   最后更新时间: {updated_at}")
    print()
    
    # 检查 running_job_ids
    if running_job_ids:
        print("⚠️  运行中的任务 (running_job_ids):")
        for idx, job_id in enumerate(running_job_ids, 1):
            # 检查任务状态
            job_ref = firestore.collection("pipeline_jobs").document(job_id)
            job_snapshot = job_ref.get()
            
            if job_snapshot.exists:
                job_data = job_snapshot.to_dict() or {}
                drama_name = job_data.get("drama_name", "N/A")
                status = job_data.get("status", "N/A")
                progress = job_data.get("progress", "N/A")
                print(f"   {idx}. {job_id}")
                print(f"      剧集: {drama_name}")
                print(f"      状态: {status}")
                print(f"      进度: {progress}")
            else:
                print(f"   {idx}. {job_id} (任务不存在)")
            print()
    else:
        print("✅ running_job_ids 为空 - 没有正在运行的任务")
        print()
    
    # 检查 queue
    if queue:
        print("📋 队列中的任务 (queue):")
        for idx, job_id in enumerate(queue, 1):
            # 检查任务状态
            job_ref = firestore.collection("pipeline_jobs").document(job_id)
            job_snapshot = job_ref.get()
            
            if job_snapshot.exists:
                job_data = job_snapshot.to_dict() or {}
                drama_name = job_data.get("drama_name", "N/A")
                status = job_data.get("status", "N/A")
                progress = job_data.get("progress", "N/A")
                print(f"   {idx}. {job_id} (位置: {idx})")
                print(f"      剧集: {drama_name}")
                print(f"      状态: {status}")
                print(f"      进度: {progress}")
            else:
                print(f"   {idx}. {job_id} (任务不存在)")
            print()
    else:
        print("✅ queue 为空 - 没有排队的任务")
        print()
    
    # 总结
    print("="*70)
    if not running_job_ids and not queue:
        print("✅ 状态正常：没有运行中的任务，也没有排队的任务")
    elif not running_job_ids:
        print(f"✅ 没有运行中的任务，但有 {len(queue)} 个任务在队列中等待")
    elif running_job_ids:
        print(f"⚠️  有 {len(running_job_ids)} 个任务标记为运行中")
        if queue:
            print(f"   还有 {len(queue)} 个任务在队列中等待")
    print("="*70)

if __name__ == "__main__":
    main()

