#!/usr/bin/env python3
"""Diagnose why a job is blocked."""

import sys
from pathlib import Path
from datetime import datetime, timezone

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore
from app.services.concurrency_service import ConcurrencyService

JOB_ID = "XaiII9IaNSWnxtO0K72C"


def check_job_status():
    """Check the job status."""
    print("=" * 60)
    print("1. 检查任务状态")
    print("=" * 60)
    
    firestore_client = get_firestore_client()
    job_ref = firestore_client.collection("pipeline_jobs").document(JOB_ID)
    snapshot = job_ref.get()
    
    if not snapshot.exists:
        print(f"❌ Job {JOB_ID} 不存在")
        return None
    
    data = snapshot.to_dict() or {}
    print(f"✅ Job {JOB_ID} 存在")
    print(f"  drama_name: {data.get('drama_name')}")
    print(f"  status: {data.get('status')}")
    print(f"  stage: {data.get('stage')}")
    print(f"  created_at: {data.get('created_at')}")
    print(f"  updated_at: {data.get('updated_at')}")
    print(f"  progress: {data.get('progress')}")
    print(f"  total_files: {data.get('total_files')}")
    print(f"  processed_files: {data.get('processed_files')}")
    print(f"  failed_files: {data.get('failed_files')}")
    
    return data


def check_concurrency_control():
    """Check concurrency control status."""
    print("\n" + "=" * 60)
    print("2. 检查并发控制状态")
    print("=" * 60)
    
    firestore_client = get_firestore_client()
    control_ref = firestore_client.collection("system_config").document("concurrency_control")
    snapshot = control_ref.get()
    
    if not snapshot.exists:
        print("⚠️  并发控制文档不存在")
        return None
    
    data = snapshot.to_dict() or {}
    running_jobs = data.get("running_jobs", 0)
    running_job_ids = data.get("running_job_ids", [])
    queue = data.get("queue", [])
    max_concurrent = data.get("max_concurrent_jobs", 1)
    updated_at = data.get("updated_at")
    
    print(f"最大并发数: {max_concurrent}")
    print(f"当前运行数: {running_jobs}")
    print(f"运行中的任务: {running_job_ids}")
    print(f"队列中的任务: {queue}")
    print(f"更新时间: {updated_at}")
    
    # Check if our job is in queue
    if JOB_ID in queue:
        position = queue.index(JOB_ID) + 1
        print(f"\n⚠️  任务 {JOB_ID} 在队列中，位置: {position}")
        print(f"   前面有 {position - 1} 个任务在等待")
    
    # Check if our job is running
    if JOB_ID in running_job_ids:
        print(f"\n✅ 任务 {JOB_ID} 正在运行中")
    
    # Check if there are zombie jobs
    if running_job_ids:
        print(f"\n检查运行中的任务状态...")
        jobs_collection = firestore_client.collection("pipeline_jobs")
        for running_job_id in running_job_ids:
            job_ref = jobs_collection.document(running_job_id)
            job_snapshot = job_ref.get()
            if job_snapshot.exists:
                job_data = job_snapshot.to_dict() or {}
                status = job_data.get("status", "").upper()
                print(f"  {running_job_id}: status={status}")
                
                # Check if it's a zombie (completed but still in running_job_ids)
                if status in ("SUCCEEDED", "FAILED", "COMPLETE"):
                    print(f"    ⚠️  僵尸任务！状态为 {status} 但仍在使用 slot")
            else:
                print(f"  {running_job_id}: 文档不存在（可能是僵尸任务）")
    
    return data


def check_cloud_run_job_executions():
    """Check Cloud Run Job executions."""
    print("\n" + "=" * 60)
    print("3. 检查 Cloud Run Job 执行情况")
    print("=" * 60)
    
    import subprocess
    
    try:
        # Get recent executions
        result = subprocess.run(
            ["gcloud", "run", "jobs", "executions", "list",
             "--job=drama-processor-job",
             "--region=us-central1",
             "--limit=10",
             "--format=json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            import json
            executions = json.loads(result.stdout)
            print(f"找到 {len(executions)} 个最近的执行")
            
            for exec in executions[:5]:
                name = exec.get("metadata", {}).get("name", "")
                status = exec.get("status", {})
                conditions = status.get("conditions", [])
                succeeded_count = status.get("succeededCount", 0)
                failed_count = status.get("failedCount", 0)
                
                print(f"\n  执行: {name}")
                print(f"    成功: {succeeded_count}, 失败: {failed_count}")
                for condition in conditions:
                    cond_type = condition.get("type", "")
                    cond_status = condition.get("status", "")
                    if cond_type == "Completed":
                        print(f"    状态: {cond_type} = {cond_status}")
        else:
            print("⚠️  无法获取 Cloud Run Job 执行列表")
            print(f"   错误: {result.stderr}")
    except Exception as exc:
        print(f"⚠️  检查 Cloud Run Job 执行失败: {exc}")


def check_related_jobs(job_data):
    """Check related jobs."""
    print("\n" + "=" * 60)
    print("4. 检查相关任务")
    print("=" * 60)
    
    if not job_data:
        print("⚠️  无法检查：缺少 job_data")
        return
    
    drama_name = job_data.get("drama_name")
    if not drama_name:
        print("⚠️  无法检查：缺少 drama_name")
        return
    
    firestore_client = get_firestore_client()
    jobs_collection = firestore_client.collection("pipeline_jobs")
    
    # Find all process jobs for this drama
    query = jobs_collection.where("drama_name", "==", drama_name).where("stage", "==", 2)
    
    process_jobs = []
    for doc in query.stream():
        doc_data = doc.to_dict() or {}
        process_jobs.append((doc.id, doc_data))
    
    if process_jobs:
        print(f"找到 {len(process_jobs)} 个压制任务:")
        for job_id, job_data in process_jobs:
            status = job_data.get("status", "").upper()
            created_at = job_data.get("created_at")
            print(f"\n  {job_id}:")
            print(f"    status: {status}")
            print(f"    created_at: {created_at}")
            if job_id == JOB_ID:
                print(f"    ⭐ 这是当前任务")
    else:
        print("⚠️  没有找到相关任务")


def main():
    """Run all checks."""
    print("=" * 60)
    print("🔍 任务阻塞诊断")
    print("=" * 60)
    print(f"任务 ID: {JOB_ID}")
    print("")
    
    init_firestore()
    
    # Step 1: Check job status
    job_data = check_job_status()
    
    # Step 2: Check concurrency control
    control_data = check_concurrency_control()
    
    # Step 3: Check Cloud Run Job executions
    check_cloud_run_job_executions()
    
    # Step 4: Check related jobs
    check_related_jobs(job_data)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 诊断总结")
    print("=" * 60)
    
    if control_data:
        running_jobs = control_data.get("running_jobs", 0)
        running_job_ids = control_data.get("running_job_ids", [])
        queue = control_data.get("queue", [])
        max_concurrent = control_data.get("max_concurrent_jobs", 1)
        
        if JOB_ID in queue:
            position = queue.index(JOB_ID) + 1
            print(f"❌ 任务在队列中，位置: {position}")
            print(f"   原因: 当前有 {running_jobs}/{max_concurrent} 个任务在运行")
            if running_job_ids:
                print(f"   运行中的任务: {running_job_ids}")
        elif JOB_ID in running_job_ids:
            print(f"✅ 任务正在运行中")
        else:
            print(f"⚠️  任务不在队列中，也不在运行中")
            print(f"   可能原因:")
            print(f"   1. 任务还未被触发")
            print(f"   2. 并发控制逻辑有问题")
            print(f"   3. 任务状态异常")


if __name__ == "__main__":
    main()


