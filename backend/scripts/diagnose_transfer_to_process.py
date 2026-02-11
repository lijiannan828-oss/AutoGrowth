#!/usr/bin/env python3
"""Diagnose why transfer job didn't trigger process job."""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import firestore, storage
from app.core.firestore import get_firestore_client, init_firestore

EXECUTION_NAME = "gdrive-transfer-worker-j6vtn"
JOB_ID = "fnfOqA3U32u0o8JUG1qh"


def check_transfer_job():
    """Check transfer job status."""
    print("=" * 60)
    print("1. 检查传输任务状态")
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
    print(f"  transfer_completed: {data.get('transfer_completed')}")
    print(f"  created_at: {data.get('created_at')}")
    print(f"  updated_at: {data.get('updated_at')}")
    print(f"  progress: {data.get('progress')}")
    
    return data


def check_signal_file(job_data):
    """Check if _PROCESS_NOW.txt exists."""
    print("\n" + "=" * 60)
    print("2. 检查信号文件 (_PROCESS_NOW.txt)")
    print("=" * 60)
    
    if not job_data:
        print("⚠️  无法检查：缺少 job_data")
        return None
    
    drama_name = job_data.get("drama_name")
    bucket_name = job_data.get("gcs_source_bucket") or "vigloo_source"
    
    if not drama_name:
        print("❌ drama_name 不存在")
        return None
    
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob_path = f"{drama_name}/_PROCESS_NOW.txt"
    blob = bucket.blob(blob_path)
    
    if blob.exists():
        blob.reload()
        print(f"✅ 信号文件存在: gs://{bucket_name}/{blob_path}")
        print(f"  创建时间: {blob.time_created}")
        print(f"  更新时间: {blob.updated}")
        print(f"  大小: {blob.size} bytes")
        
        # Check if created after transfer completion
        transfer_completed_time = job_data.get("updated_at")
        if transfer_completed_time and hasattr(transfer_completed_time, 'timestamp'):
            transfer_ts = transfer_completed_time.timestamp()
            signal_ts = blob.time_created.timestamp()
            if signal_ts >= transfer_ts:
                print(f"  ✅ 信号文件在传输完成后创建（时间戳验证）")
            else:
                print(f"  ⚠️  信号文件创建时间早于传输完成时间")
        
        return blob
    else:
        print(f"❌ 信号文件不存在: gs://{bucket_name}/{blob_path}")
        return None


def check_eventarc_logs(blob):
    """Check Eventarc logs."""
    print("\n" + "=" * 60)
    print("3. 检查 Eventarc 日志")
    print("=" * 60)
    
    if not blob:
        print("⚠️  无法检查：信号文件不存在")
        return
    
    # Eventarc logs are in Cloud Logging
    # We need to search for GCS object finalized events
    signal_time = blob.time_created
    
    print(f"搜索时间范围: {signal_time} 之后")
    print("⚠️  注意：Eventarc 日志可能需要通过 GCP Console 查看")
    print("   查询条件:")
    print(f"   resource.type=eventarc_trigger")
    print(f"   resource.labels.trigger_id=drama-processor-trigger")
    print(f"   timestamp>=\"{signal_time.isoformat()}\"")


def check_relay_service_logs(blob, job_data):
    """Check Relay Service logs."""
    print("\n" + "=" * 60)
    print("4. 检查 Relay Service 日志")
    print("=" * 60)
    
    if not blob or not job_data:
        print("⚠️  无法检查：缺少必要信息")
        return
    
    drama_name = job_data.get("drama_name")
    signal_time = blob.time_created
    
    print(f"搜索时间范围: {signal_time} 之后")
    print("⚠️  注意：Relay Service 日志需要通过 GCP Console 查看")
    print("   查询条件:")
    print(f"   resource.type=cloud_run_revision")
    print(f"   resource.labels.service_name=drama-processor-relay-service")
    print(f"   textPayload=~\"{drama_name}\" OR textPayload=~\"{JOB_ID}\"")
    print(f"   timestamp>=\"{signal_time.isoformat()}\"")


def check_process_jobs(job_data):
    """Check if any process jobs were created."""
    print("\n" + "=" * 60)
    print("5. 检查是否创建了压制任务")
    print("=" * 60)
    
    if not job_data:
        print("⚠️  无法检查：缺少 job_data")
        return
    
    drama_name = job_data.get("drama_name")
    transfer_completed_time = job_data.get("updated_at")
    
    firestore_client = get_firestore_client()
    jobs_collection = firestore_client.collection("pipeline_jobs")
    
    # Query for process jobs (stage=2 or status=PROCESSING/SUCCEEDED/FAILED)
    # that match this drama_name and were created after transfer completion
    query = jobs_collection.where("drama_name", "==", drama_name)
    
    process_jobs = []
    for doc in query.stream():
        doc_data = doc.to_dict() or {}
        stage = doc_data.get("stage")
        status = doc_data.get("status", "").upper()
        
        # Check if it's a process job
        if stage == 2 or status in ("PROCESSING", "SUCCEEDED", "FAILED", "QUEUED"):
            created_at = doc_data.get("created_at")
            if created_at and transfer_completed_time:
                if hasattr(created_at, 'timestamp') and hasattr(transfer_completed_time, 'timestamp'):
                    if created_at.timestamp() >= transfer_completed_time.timestamp():
                        process_jobs.append((doc.id, doc_data))
    
    if process_jobs:
        print(f"✅ 找到 {len(process_jobs)} 个压制任务:")
        for job_id, job_data in process_jobs:
            print(f"  - {job_id}: status={job_data.get('status')}, stage={job_data.get('stage')}")
            print(f"    created_at: {job_data.get('created_at')}")
    else:
        print("❌ 没有找到压制任务")
        print(f"   搜索条件: drama_name={drama_name}, 创建时间在传输完成后")


def check_transfer_logs():
    """Check transfer worker logs."""
    print("\n" + "=" * 60)
    print("6. 检查传输任务日志")
    print("=" * 60)
    
    print("⚠️  传输任务日志需要通过 GCP Console 查看")
    print("   查询条件:")
    print(f"   resource.type=cloud_run_job")
    print(f"   resource.labels.job_name=gdrive-transfer-worker")
    print(f"   labels.execution_name={EXECUTION_NAME}")
    print("")
    print("   关键日志:")
    print("   - \"传输完成，_PROCESS_NOW.txt 已创建\"")
    print("   - \"_PROCESS_NOW.txt\"")
    print("   - \"COMPLETE\"")


def main():
    """Run all checks."""
    print("=" * 60)
    print("🔍 传输任务未触发压制任务诊断")
    print("=" * 60)
    print(f"传输任务执行: {EXECUTION_NAME}")
    print(f"Job ID: {JOB_ID}")
    print("")
    
    init_firestore()
    
    # Step 1: Check transfer job
    job_data = check_transfer_job()
    
    # Step 2: Check signal file
    blob = check_signal_file(job_data)
    
    # Step 3: Check Eventarc logs
    check_eventarc_logs(blob)
    
    # Step 4: Check Relay Service logs
    check_relay_service_logs(blob, job_data)
    
    # Step 5: Check process jobs
    check_process_jobs(job_data)
    
    # Step 6: Check transfer logs
    check_transfer_logs()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 诊断总结")
    print("=" * 60)
    
    if not job_data:
        print("❌ 无法获取传输任务信息")
        return
    
    if job_data.get("transfer_completed"):
        print("✅ 传输任务标记为完成")
    else:
        print("❌ 传输任务未标记为完成")
    
    if blob:
        print("✅ 信号文件存在")
    else:
        print("❌ 信号文件不存在 - 这是主要问题！")
        print("   可能原因:")
        print("   1. 传输任务失败但未抛出异常")
        print("   2. 信号文件创建失败")
        print("   3. 信号文件被删除")
    
    if job_data.get("drama_name"):
        print(f"✅ drama_name: {job_data.get('drama_name')}")
    else:
        print("❌ drama_name 缺失")


if __name__ == "__main__":
    main()

