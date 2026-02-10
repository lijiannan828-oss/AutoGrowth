#!/usr/bin/env python3
"""Detailed diagnosis of complete flow: transfer → trigger → process queue."""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore

TRANSFER_JOB_ID = "9coW3RXB9WHhQKa1FioF"


def check_transfer_job():
    """Check transfer job status."""
    print("=" * 60)
    print("1. 传输任务状态")
    print("=" * 60)
    
    firestore_client = get_firestore_client()
    job_ref = firestore_client.collection("pipeline_jobs").document(TRANSFER_JOB_ID)
    snapshot = job_ref.get()
    
    if not snapshot.exists:
        print(f"❌ 传输任务 {TRANSFER_JOB_ID} 不存在")
        return None
    
    data = snapshot.to_dict() or {}
    drama_name = data.get("drama_name")
    status = data.get("status")
    stage = data.get("stage")
    transfer_completed = data.get("transfer_completed")
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    progress = data.get("progress")
    last_event = data.get("last_event", {})
    
    print(f"✅ 传输任务存在")
    print(f"  任务 ID: {TRANSFER_JOB_ID}")
    print(f"  剧集: {drama_name}")
    print(f"  状态: {status}")
    print(f"  阶段: {stage}")
    print(f"  传输完成: {transfer_completed}")
    print(f"  创建时间: {created_at}")
    print(f"  更新时间: {updated_at}")
    print(f"  进度: {progress}")
    print(f"  最后事件: {last_event.get('type') if isinstance(last_event, dict) else last_event}")
    
    if status == "COMPLETE" and transfer_completed:
        print("\n✅ 传输任务已完成")
    elif status == "PROCESSING":
        print("\n⏳ 传输任务进行中")
    else:
        print(f"\n⚠️  传输任务状态异常: {status}")
    
    return {"drama_name": drama_name, "status": status, "transfer_completed": transfer_completed}


def check_signal_file(drama_name):
    """Check if _PROCESS_NOW.txt exists."""
    print("\n" + "=" * 60)
    print("2. 信号文件检查")
    print("=" * 60)
    
    import subprocess
    
    signal_path = f"gs://vigloo_source/{drama_name}/_PROCESS_NOW.txt"
    
    try:
        result = subprocess.run(
            ["gsutil", "ls", signal_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"✅ 信号文件存在: {signal_path}")
            # Get file creation time
            stat_result = subprocess.run(
                ["gsutil", "stat", signal_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if stat_result.returncode == 0:
                for line in stat_result.stdout.split("\n"):
                    if "Creation time:" in line:
                        print(f"  创建时间: {line.split('Creation time:')[1].strip()}")
            return True
        else:
            print(f"❌ 信号文件不存在: {signal_path}")
            return False
    except Exception as exc:
        print(f"⚠️  无法检查信号文件: {exc}")
        return None


def check_relay_service_logs(drama_name):
    """Check Relay Service logs."""
    print("\n" + "=" * 60)
    print("3. Relay Service 日志")
    print("=" * 60)
    
    import subprocess
    
    # Check for relay service logs
    try:
        result = subprocess.run(
            [
                "gcloud", "logging", "read",
                f'resource.type=cloud_run_revision AND resource.labels.service_name="drama-processor-relay-service" AND (textPayload=~"{TRANSFER_JOB_ID}" OR textPayload=~"{drama_name}")',
                "--limit=20",
                "--format=value(timestamp,textPayload)",
                "--project=fleet-blend-469520-n7"
            ],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print("✅ 找到 Relay Service 日志:")
            lines = result.stdout.strip().split("\n")
            for i, line in enumerate(lines[:10], 1):
                if len(line) > 200:
                    print(f"  {i}. {line[:200]}...")
                else:
                    print(f"  {i}. {line}")
            return True
        else:
            print("⚠️  未找到相关 Relay Service 日志")
            return False
    except Exception as exc:
        print(f"⚠️  无法获取 Relay Service 日志: {exc}")
        return None


def check_process_job(drama_name):
    """Check process job status."""
    print("\n" + "=" * 60)
    print("4. 压制任务状态")
    print("=" * 60)
    
    firestore_client = get_firestore_client()
    jobs_collection = firestore_client.collection("pipeline_jobs")
    query = jobs_collection.where("drama_name", "==", drama_name).where("stage", "==", 2)
    
    process_jobs = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        process_jobs.append((doc.id, data))
    
    if process_jobs:
        print(f"✅ 找到 {len(process_jobs)} 个压制任务:")
        for job_id, data in process_jobs:
            print(f"\n  任务 ID: {job_id}")
            print(f"    状态: {data.get('status')}")
            print(f"    类型: {data.get('type')}")
            print(f"    创建时间: {data.get('created_at')}")
            print(f"    更新时间: {data.get('updated_at')}")
            print(f"    进度: {data.get('progress')}")
            print(f"    total_files: {data.get('total_files')}")
            print(f"    processed_files: {data.get('processed_files')}")
            print(f"    failed_files: {data.get('failed_files')}")
        
        return process_jobs[0][0]  # Return first job ID
    else:
        print("❌ 没有找到压制任务")
        return None


def check_queue_position(process_job_id):
    """Check queue position."""
    print("\n" + "=" * 60)
    print("5. 队列位置")
    print("=" * 60)
    
    firestore_client = get_firestore_client()
    control_ref = firestore_client.collection("system_config").document("concurrency_control")
    snapshot = control_ref.get()
    
    if not snapshot.exists:
        print("⚠️  并发控制文档不存在")
        return
    
    data = snapshot.to_dict() or {}
    running_jobs = data.get("running_jobs", 0)
    running_job_ids = data.get("running_job_ids", [])
    queue = data.get("queue", [])
    max_concurrent = data.get("max_concurrent_jobs", 1)
    
    print(f"最大并发数: {max_concurrent}")
    print(f"当前运行数: {running_jobs}")
    print(f"运行中的任务: {running_job_ids}")
    print(f"队列中的任务: {queue}")
    print("")
    
    if process_job_id in queue:
        position = queue.index(process_job_id) + 1
        print(f"✅ 压制任务在队列中")
        print(f"   位置: 第 {position} 位")
        print(f"   前面有 {position - 1} 个任务在等待")
    elif process_job_id in running_job_ids:
        print(f"✅ 压制任务正在运行中")
    else:
        print(f"⚠️  压制任务不在队列中，也不在运行中")
        print(f"   可能原因:")
        print(f"   1. 任务还未被触发")
        print(f"   2. 任务已完成或失败")
        print(f"   3. 任务状态异常")


def main():
    """Run complete diagnosis."""
    print("=" * 60)
    print("🔍 完整流程诊断")
    print("=" * 60)
    print(f"传输任务 ID: {TRANSFER_JOB_ID}")
    print("")
    
    init_firestore()
    
    # Step 1: Check transfer job
    transfer_info = check_transfer_job()
    if not transfer_info:
        return
    
    drama_name = transfer_info.get("drama_name")
    if not drama_name:
        print("❌ 无法获取 drama_name")
        return
    
    # Step 2: Check signal file
    signal_exists = check_signal_file(drama_name)
    
    # Step 3: Check Relay Service logs
    relay_logs = check_relay_service_logs(drama_name)
    
    # Step 4: Check process job
    process_job_id = check_process_job(drama_name)
    
    # Step 5: Check queue position
    if process_job_id:
        check_queue_position(process_job_id)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 诊断总结")
    print("=" * 60)
    
    issues = []
    
    if transfer_info.get("status") != "COMPLETE":
        issues.append("传输任务未完成")
    
    if not signal_exists:
        issues.append("信号文件不存在")
    
    if not relay_logs:
        issues.append("未找到 Relay Service 日志")
    
    if not process_job_id:
        issues.append("未找到压制任务")
    
    if issues:
        print("⚠️  发现的问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ 所有环节正常")


if __name__ == "__main__":
    main()


