#!/usr/bin/env python3
"""Analyze two Cloud Run Job executions to understand their creation and concurrency control."""

import sys
from pathlib import Path
from datetime import datetime, timezone

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore

EXECUTION_1 = "drama-processor-job-rbtgv"
EXECUTION_2 = "drama-processor-job-5q6gg"


def get_execution_times():
    """Get creation times for both executions."""
    import subprocess
    import json
    
    times = {}
    for exec_name in [EXECUTION_1, EXECUTION_2]:
        try:
            result = subprocess.run(
                ["gcloud", "run", "jobs", "executions", "describe", exec_name,
                 "--region=us-central1", "--format=json", "--project=fleet-blend-469520-n7"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                creation_time = data.get("metadata", {}).get("creationTimestamp", "")
                times[exec_name] = creation_time
        except Exception as e:
            print(f"⚠️  无法获取 {exec_name} 的创建时间: {e}")
    
    return times


def find_related_jobs():
    """Find Firestore jobs that might be related to these executions."""
    init_firestore()
    firestore_client = get_firestore_client()
    
    # Get all recent jobs
    jobs_collection = firestore_client.collection("pipeline_jobs")
    
    # Get jobs created in last 3 hours
    from datetime import timedelta
    three_hours_ago = datetime.now(timezone.utc) - timedelta(hours=3)
    
    related_jobs = []
    for doc in jobs_collection.stream():
        data = doc.to_dict() or {}
        created_at = data.get("created_at")
        if created_at:
            if hasattr(created_at, "timestamp"):
                if created_at.timestamp() > three_hours_ago.timestamp():
                    related_jobs.append((doc.id, data, created_at))
    
    # Sort by created_at
    related_jobs.sort(key=lambda x: x[2], reverse=True)
    
    return related_jobs


def check_concurrency_control():
    """Check concurrency control status."""
    init_firestore()
    firestore_client = get_firestore_client()
    
    control_ref = firestore_client.collection("system_config").document("concurrency_control")
    snapshot = control_ref.get()
    
    if snapshot.exists:
        data = snapshot.to_dict() or {}
        return {
            "max_concurrent": data.get("max_concurrent_jobs", 1),
            "running_jobs": data.get("running_jobs", 0),
            "running_job_ids": data.get("running_job_ids", []),
            "queue": data.get("queue", []),
            "updated_at": data.get("updated_at"),
        }
    return None


def main():
    """Main analysis."""
    print("=" * 60)
    print("🔍 分析两个 Cloud Run Job 执行")
    print("=" * 60)
    print(f"执行 1: {EXECUTION_1}")
    print(f"执行 2: {EXECUTION_2}")
    print("")
    
    # Get execution times
    print("1. 获取执行创建时间")
    print("-" * 60)
    exec_times = get_execution_times()
    for exec_name, creation_time in exec_times.items():
        print(f"  {exec_name}: {creation_time}")
    print("")
    
    # Find related jobs
    print("2. 查找相关的 Firestore 任务")
    print("-" * 60)
    related_jobs = find_related_jobs()
    print(f"找到 {len(related_jobs)} 个最近 3 小时内创建的任务")
    
    for job_id, data, created_at in related_jobs[:5]:
        drama_name = data.get("drama_name", "N/A")
        status = data.get("status", "N/A")
        job_type = data.get("type", "standard")
        created_by = data.get("created_by", {})
        user = created_by.get("user", "N/A") if isinstance(created_by, dict) else "N/A"
        last_event = data.get("last_event", {})
        event_type = last_event.get("type", "N/A") if isinstance(last_event, dict) else "N/A"
        
        print(f"\n  任务 ID: {job_id}")
        print(f"    剧集: {drama_name}")
        print(f"    状态: {status}")
        print(f"    类型: {job_type}")
        print(f"    创建时间: {created_at}")
        print(f"    创建者: {user}")
        print(f"    最后事件: {event_type}")
    
    print("")
    
    # Check concurrency control
    print("3. 检查并发控制状态")
    print("-" * 60)
    control_data = check_concurrency_control()
    if control_data:
        print(f"最大并发数: {control_data['max_concurrent']}")
        print(f"当前运行数: {control_data['running_jobs']}")
        print(f"运行中的任务: {control_data['running_job_ids']}")
        print(f"队列中的任务: {control_data['queue']}")
        print(f"更新时间: {control_data['updated_at']}")
        
        if len(control_data['running_job_ids']) > control_data['max_concurrent']:
            print("\n⚠️  违反并发控制限制！")
            print(f"   运行中的任务数 ({len(control_data['running_job_ids'])}) > 最大并发数 ({control_data['max_concurrent']})")
        else:
            print("\n✅ 符合并发控制限制")
    else:
        print("⚠️  并发控制文档不存在")
    
    print("")
    print("=" * 60)
    print("📊 分析总结")
    print("=" * 60)
    
    if exec_times:
        time1 = exec_times.get(EXECUTION_1, "")
        time2 = exec_times.get(EXECUTION_2, "")
        if time1 and time2:
            if time1 < time2:
                print(f"✅ {EXECUTION_1} 先创建（可能是手动触发）")
                print(f"✅ {EXECUTION_2} 后创建（可能是自动触发）")
            else:
                print(f"✅ {EXECUTION_2} 先创建（可能是手动触发）")
                print(f"✅ {EXECUTION_1} 后创建（可能是自动触发）")
    
    if control_data:
        if len(control_data['running_job_ids']) <= control_data['max_concurrent']:
            print("✅ 并发控制逻辑生效")
        else:
            print("❌ 并发控制逻辑未生效")


if __name__ == "__main__":
    main()


