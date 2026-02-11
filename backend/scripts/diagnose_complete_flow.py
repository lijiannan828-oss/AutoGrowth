#!/usr/bin/env python3
"""Complete flow diagnosis for transfer job."""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import firestore, storage
from app.core.firestore import get_firestore_client, init_firestore

TRANSFER_JOB_ID = "aFLbs1HIRDMt3aBjHzGV"


def check_transfer_job():
    """Check transfer job status in Firestore."""
    print("=" * 60)
    print("1. 检查传输任务数据库状态")
    print("=" * 60)
    
    firestore_client = get_firestore_client()
    job_ref = firestore_client.collection("pipeline_jobs").document(TRANSFER_JOB_ID)
    snapshot = job_ref.get()
    
    if not snapshot.exists:
        print(f"❌ Job {TRANSFER_JOB_ID} 不存在")
        return None
    
    data = snapshot.to_dict() or {}
    print(f"✅ Job {TRANSFER_JOB_ID} 存在")
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
            if signal_ts >= transfer_ts - 10:  # Allow 10 seconds tolerance
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
    print("3. 检查 Eventarc 触发情况")
    print("=" * 60)
    
    if not blob:
        print("⚠️  无法检查：信号文件不存在")
        return
    
    signal_time = blob.time_created
    print(f"信号文件创建时间: {signal_time}")
    print(f"搜索时间范围: {signal_time} 之后 5 分钟")
    print("\n⚠️  注意：Eventarc 日志需要通过 GCP Console 或 gcloud 命令查看")
    print("   查询条件:")
    print(f"   resource.type=eventarc_trigger")
    print(f"   resource.labels.trigger_id=drama-processor-trigger")
    print(f"   timestamp>=\"{signal_time.isoformat()}\"")


def check_relay_service_logs(job_data, blob):
    """Check Relay Service logs."""
    print("\n" + "=" * 60)
    print("4. 检查 Relay Service 日志")
    print("=" * 60)
    
    if not job_data or not blob:
        print("⚠️  无法检查：缺少必要信息")
        return
    
    drama_name = job_data.get("drama_name")
    signal_time = blob.time_created
    
    print(f"信号文件创建时间: {signal_time}")
    print(f"搜索时间范围: {signal_time} 之后 10 分钟")
    print("\n⚠️  注意：Relay Service 日志需要通过 gcloud 命令查看")
    print("   查询条件:")
    print(f"   resource.type=cloud_run_revision")
    print(f"   resource.labels.service_name=drama-processor-relay-service")
    print(f"   textPayload=~\"{drama_name}\" OR textPayload=~\"{TRANSFER_JOB_ID}\" OR textPayload=~\"RELAY-\"")
    print(f"   timestamp>=\"{signal_time.isoformat()}\"")


def check_process_jobs(job_data):
    """Check if process jobs were created."""
    print("\n" + "=" * 60)
    print("5. 检查压制任务创建情况")
    print("=" * 60)
    
    if not job_data:
        print("⚠️  无法检查：缺少 job_data")
        return
    
    drama_name = job_data.get("drama_name")
    transfer_completed_time = job_data.get("updated_at")
    
    firestore_client = get_firestore_client()
    jobs_collection = firestore_client.collection("pipeline_jobs")
    
    # Query for process jobs (stage=2) that match this drama_name
    query = jobs_collection.where("drama_name", "==", drama_name).where("stage", "==", 2)
    
    process_jobs = []
    for doc in query.stream():
        doc_data = doc.to_dict() or {}
        created_at = doc_data.get("created_at")
        
        if created_at and transfer_completed_time:
            if hasattr(created_at, 'timestamp') and hasattr(transfer_completed_time, 'timestamp'):
                if created_at.timestamp() >= transfer_completed_time.timestamp():
                    process_jobs.append((doc.id, doc_data))
    
    if process_jobs:
        print(f"✅ 找到 {len(process_jobs)} 个压制任务:")
        for job_id, job_data in process_jobs:
            print(f"\n  Job ID: {job_id}")
            print(f"    status: {job_data.get('status')}")
            print(f"    created_at: {job_data.get('created_at')}")
            print(f"    updated_at: {job_data.get('updated_at')}")
            print(f"    total_files: {job_data.get('total_files')}")
            print(f"    processed_files: {job_data.get('processed_files')}")
            print(f"    failed_files: {job_data.get('failed_files')}")
            print(f"    progress: {job_data.get('progress')}")
            
            # Calculate delay
            if transfer_completed_time and job_data.get('created_at'):
                delay = job_data.get('created_at').timestamp() - transfer_completed_time.timestamp()
                print(f"    延迟: {delay/60:.1f} 分钟")
        
        return process_jobs[0][0] if process_jobs else None
    else:
        print("❌ 没有找到压制任务")
        return None


def check_sharding_execution(process_job_id):
    """Check sharding execution details."""
    print("\n" + "=" * 60)
    print("6. 检查压制任务分片执行情况")
    print("=" * 60)
    
    if not process_job_id:
        print("⚠️  无法检查：没有找到压制任务")
        return
    
    firestore_client = get_firestore_client()
    job_ref = firestore_client.collection("pipeline_jobs").document(process_job_id)
    job_snapshot = job_ref.get()
    
    if not job_snapshot.exists:
        print(f"❌ Process job {process_job_id} 不存在")
        return
    
    job_data = job_snapshot.to_dict() or {}
    total_files = job_data.get("total_files", 0)
    processed_files = job_data.get("processed_files", 0)
    failed_files = job_data.get("failed_files", 0)
    
    print(f"总文件数: {total_files}")
    print(f"已处理: {processed_files}")
    print(f"失败: {failed_files}")
    
    # Check task documents
    tasks_collection = job_ref.collection("tasks")
    tasks = list(tasks_collection.stream())
    
    if tasks:
        print(f"\n✅ 找到 {len(tasks)} 个 Task 文档:")
        
        completed_tasks = 0
        running_tasks = 0
        total_assigned = 0
        total_success = 0
        total_failed = 0
        
        for task_doc in tasks:
            task_data = task_doc.to_dict() or {}
            task_index = task_data.get("task_index", task_doc.id)
            status = task_data.get("status", "UNKNOWN")
            total_count = task_data.get("total_count", 0)
            progress_count = task_data.get("progress_count", 0)
            success_files = task_data.get("success_files", [])
            failed_files_list = task_data.get("failed_files", [])
            
            total_assigned += total_count
            total_success += len(success_files)
            total_failed += len(failed_files_list)
            
            if status == "COMPLETED":
                completed_tasks += 1
            elif status == "RUNNING":
                running_tasks += 1
            
            print(f"\n  Task {task_index}:")
            print(f"    status: {status}")
            print(f"    total_count: {total_count}")
            print(f"    progress_count: {progress_count}")
            print(f"    success_files: {len(success_files)}")
            print(f"    failed_files: {len(failed_files_list)}")
            if task_data.get("current_file"):
                print(f"    current_file: {task_data.get('current_file')}")
        
        print(f"\n📊 汇总:")
        print(f"  总 Task 数: {len(tasks)}")
        print(f"  已完成: {completed_tasks}")
        print(f"  运行中: {running_tasks}")
        print(f"  总分配文件数: {total_assigned}")
        print(f"  总成功文件数: {total_success}")
        print(f"  总失败文件数: {total_failed}")
        
        # Check if all files are assigned
        if total_assigned == total_files:
            print(f"  ✅ 所有文件都已分配")
        else:
            print(f"  ⚠️  文件分配不完整: {total_assigned}/{total_files}")
    else:
        print("⚠️  没有找到 Task 文档（可能任务还未开始或使用旧版本）")


def main():
    """Run all checks."""
    print("=" * 60)
    print("🔍 完整流程诊断")
    print("=" * 60)
    print(f"传输任务 ID: {TRANSFER_JOB_ID}")
    print("")
    
    init_firestore()
    
    # Step 1: Check transfer job
    job_data = check_transfer_job()
    
    # Step 2: Check signal file
    blob = check_signal_file(job_data)
    
    # Step 3: Check Eventarc logs
    check_eventarc_logs(blob)
    
    # Step 4: Check Relay Service logs
    check_relay_service_logs(job_data, blob)
    
    # Step 5: Check process jobs
    process_job_id = check_process_jobs(job_data)
    
    # Step 6: Check sharding execution
    check_sharding_execution(process_job_id)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 诊断总结")
    print("=" * 60)
    
    if job_data and job_data.get("transfer_completed"):
        print("✅ 1. 数据库写入成功")
    else:
        print("❌ 1. 数据库写入失败或未完成")
    
    if blob:
        print("✅ 2. 信号文件已生成")
    else:
        print("❌ 2. 信号文件未生成")
    
    print("⚠️  3. Eventarc 触发情况需要查看 GCP 日志")
    
    print("⚠️  4. Relay Service 接收情况需要查看 GCP 日志")
    
    if process_job_id:
        print("✅ 5. 压制任务已创建")
    else:
        print("❌ 5. 压制任务未创建")
    
    if process_job_id:
        print("✅ 6. 分片执行情况已检查（见上方详情）")


if __name__ == "__main__":
    main()


