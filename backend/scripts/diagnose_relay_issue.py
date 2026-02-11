#!/usr/bin/env python3
"""Diagnose why relay endpoint didn't trigger process job for a specific transfer job.

Usage:
    python scripts/diagnose_relay_issue.py --job-id cmSLOCznhQOxY4jozRXP
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import firestore, storage
from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore


def check_job_exists(job_id: str) -> dict | None:
    """Check if job exists in Firestore."""
    init_firestore()
    client = get_firestore_client()
    doc_ref = client.collection("pipeline_jobs").document(job_id)
    snapshot = doc_ref.get()
    
    if not snapshot.exists:
        return None
    
    return snapshot.to_dict()


def check_gcs_signal_file(drama_name: str, bucket_name: str) -> bool:
    """Check if _PROCESS_NOW.txt file exists in GCS."""
    client = storage.Client(project=settings.firestore_project_id)
    bucket = client.bucket(bucket_name)
    blob_path = f"{drama_name}/_PROCESS_NOW.txt"
    blob = bucket.blob(blob_path)
    return blob.exists()


def extract_drama_name(object_name: str | None) -> str | None:
    """Extract drama name from GCS object path (same logic as relay.py)."""
    if not object_name:
        return None
    segments = [part for part in object_name.split("/") if part]
    if not segments:
        return None
    return segments[0]


def find_matching_jobs(drama_name: str) -> list[dict]:
    """Find all jobs matching the drama_name."""
    init_firestore()
    client = get_firestore_client()
    query = (
        client.collection("pipeline_jobs")
        .where("drama_name", "==", drama_name)
        .limit(20)
    )
    
    results = []
    for snapshot in query.stream():
        data = snapshot.to_dict() or {}
        if not data:
            continue
        results.append({
            "job_id": snapshot.id,
            "drama_name": data.get("drama_name"),
            "transfer_completed": data.get("transfer_completed"),
            "stage": data.get("stage"),
            "status": data.get("status"),
            "updated_at": data.get("updated_at"),
        })
    
    return results


def check_relay_query_logic(drama_name: str) -> dict:
    """Simulate the relay endpoint's job finding logic."""
    matching_jobs = find_matching_jobs(drama_name)
    
    ready_jobs = []
    for job in matching_jobs:
        transfer_completed = bool(job.get("transfer_completed"))
        stage = job.get("stage")
        if transfer_completed and (stage == 1 or stage is None):
            ready_jobs.append(job)
    
    return {
        "drama_name": drama_name,
        "total_matching_jobs": len(matching_jobs),
        "ready_jobs": ready_jobs,
        "first_ready_job": ready_jobs[0] if ready_jobs else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Diagnose relay endpoint issue")
    parser.add_argument("--job-id", required=True, help="Transfer job ID")
    parser.add_argument("--bucket", default="vigloo_source", help="GCS bucket name")
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔍 Relay 端点问题诊断")
    print("=" * 80)
    print(f"\n任务 ID: {args.job_id}")
    print(f"GCS Bucket: {args.bucket}")
    
    # Step 1: Check if job exists
    print("\n" + "=" * 80)
    print("步骤 1: 检查 Firestore 中的 job")
    print("=" * 80)
    job_data = check_job_exists(args.job_id)
    if not job_data:
        print(f"❌ Job {args.job_id} 不存在于 Firestore")
        return 1
    
    print(f"✅ Job 存在")
    drama_name = job_data.get("drama_name")
    transfer_completed = job_data.get("transfer_completed")
    stage = job_data.get("stage")
    status = job_data.get("status")
    
    print(f"   Drama Name: {drama_name}")
    print(f"   Status: {status}")
    print(f"   transfer_completed: {transfer_completed}")
    print(f"   stage: {stage}")
    
    # Step 2: Check GCS signal file
    print("\n" + "=" * 80)
    print("步骤 2: 检查 GCS 中的 _PROCESS_NOW.txt 文件")
    print("=" * 80)
    if not drama_name:
        print("❌ Job 中缺少 drama_name")
        return 1
    
    expected_blob_path = f"{drama_name}/_PROCESS_NOW.txt"
    print(f"   期望路径: gs://{args.bucket}/{expected_blob_path}")
    
    signal_exists = check_gcs_signal_file(drama_name, args.bucket)
    if signal_exists:
        print(f"✅ _PROCESS_NOW.txt 文件存在")
    else:
        print(f"❌ _PROCESS_NOW.txt 文件不存在")
        print(f"   ⚠️  这可能是问题的根源：传输 worker 可能没有创建信号文件")
    
    # Step 3: Check relay query logic
    print("\n" + "=" * 80)
    print("步骤 3: 模拟 Relay 端点的查询逻辑")
    print("=" * 80)
    query_result = check_relay_query_logic(drama_name)
    
    print(f"   查询条件: drama_name == '{drama_name}'")
    print(f"   找到的匹配 job 数量: {query_result['total_matching_jobs']}")
    
    if query_result['ready_jobs']:
        print(f"   ✅ 找到 {len(query_result['ready_jobs'])} 个 ready job(s):")
        for i, job in enumerate(query_result['ready_jobs'], 1):
            print(f"      {i}. Job ID: {job['job_id']}")
            print(f"         transfer_completed: {job['transfer_completed']}")
            print(f"         stage: {job['stage']}")
            print(f"         status: {job['status']}")
        
        first_job = query_result['first_ready_job']
        if first_job['job_id'] == args.job_id:
            print(f"\n   ✅ 目标 job ({args.job_id}) 会被选中")
        else:
            print(f"\n   ⚠️  目标 job ({args.job_id}) 不会被选中")
            print(f"       Relay 会选择第一个 ready job: {first_job['job_id']}")
    else:
        print(f"   ❌ 没有找到 ready job")
        print(f"      条件: transfer_completed=True AND (stage=1 OR stage=None)")
    
    # Step 4: Check drama_name extraction
    print("\n" + "=" * 80)
    print("步骤 4: 检查 drama_name 提取逻辑")
    print("=" * 80)
    test_object_paths = [
        f"{drama_name}/_PROCESS_NOW.txt",
        f"{drama_name}/episodes/final/_PROCESS_NOW.txt",
        f"{drama_name}/subtitles/final/_PROCESS_NOW.txt",
    ]
    
    for obj_path in test_object_paths:
        extracted = extract_drama_name(obj_path)
        match = "✅" if extracted == drama_name else "❌"
        print(f"   {match} 对象路径: {obj_path}")
        print(f"      提取的 drama_name: {extracted}")
        print(f"      匹配: {extracted == drama_name}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 诊断总结")
    print("=" * 80)
    
    issues = []
    
    if not signal_exists:
        issues.append("❌ GCS 中缺少 _PROCESS_NOW.txt 文件（传输 worker 可能未创建）")
    
    if not query_result['ready_jobs']:
        issues.append("❌ Relay 查询逻辑找不到 ready job")
    elif query_result['first_ready_job']['job_id'] != args.job_id:
        issues.append(f"⚠️  Relay 会选择其他 job ({query_result['first_ready_job']['job_id']}) 而不是目标 job")
    
    if not transfer_completed:
        issues.append("❌ Job 的 transfer_completed 不为 True")
    
    if stage not in [1, None]:
        issues.append(f"⚠️  Job 的 stage ({stage}) 不是 1 或 None")
    
    if issues:
        print("\n发现的问题：")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ 所有检查通过，job 应该能被 relay 端点找到")
        print("   如果压制任务仍未触发，可能的原因：")
        print("   1. Eventarc 触发器未正确配置")
        print("   2. Relay 服务未收到 Eventarc 事件")
        print("   3. Relay 服务触发 process job 时出错")
        print("\n   建议检查：")
        print("   - Relay 服务日志")
        print("   - Eventarc 触发器配置")
        print("   - Process job 执行日志")
    
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())

