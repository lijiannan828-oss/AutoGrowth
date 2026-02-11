#!/usr/bin/env python3
"""
清理僵尸任务脚本

功能：
1. 查找所有 PROCESSING 状态的任务
2. 识别真实任务（通过 Cloud Run execution 检查）
3. 将其他僵尸任务的状态更新为 CANCELED
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess
import json

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load environment variables
env_file = backend_path / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

os.environ["APP_ENV"] = "production"

from app.core.firestore import init_firestore, get_firestore_client
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# Real job execution name (from user input)
REAL_EXECUTION_NAME = "drama-processor-job-gpnvt"
REAL_JOB_REGION = "us-central1"


def find_real_job_id(execution_name: str, region: str) -> str | None:
    """通过 Cloud Run execution 查找真实的 job_id"""
    try:
        result = subprocess.run(
            ["gcloud", "run", "jobs", "executions", "describe", execution_name,
             "--region", region,
             "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            exec_data = json.loads(result.stdout)
            containers = exec_data.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            for container in containers:
                env_vars = container.get("env", [])
                for env_var in env_vars:
                    if env_var.get("name") == "JOB_ID":
                        return env_var.get("value")
        return None
    except Exception as e:
        print(f"⚠️ 检查 execution 失败: {e}")
        return None


def list_zombie_jobs(dry_run: bool = True):
    """列出所有僵尸任务"""
    init_firestore()
    firestore = get_firestore_client()
    
    # Get running_job_ids from concurrency control
    control_ref = firestore.collection("system_config").document("concurrency_control")
    control_snapshot = control_ref.get()
    
    if control_snapshot.exists:
        control_data = control_snapshot.to_dict() or {}
        running_job_ids = set(control_data.get('running_job_ids', []))
    else:
        running_job_ids = set()
    
    # Find real job ID
    print(f"🔍 查找真实任务对应的 job_id (execution: {REAL_EXECUTION_NAME})...")
    real_job_id = find_real_job_id(REAL_EXECUTION_NAME, REAL_JOB_REGION)
    
    if real_job_id:
        print(f"✅ 找到真实任务: {real_job_id}")
    else:
        print("⚠️ 未找到真实任务对应的 job_id")
        print("   将使用 running_job_ids 中的任务作为真实任务")
        if running_job_ids:
            real_job_id = list(running_job_ids)[0]
            print(f"   使用: {real_job_id}")
        else:
            print("   ❌ running_job_ids 也为空，无法确定真实任务")
            return
    
    print()
    
    # Query all PROCESSING jobs
    jobs_ref = firestore.collection("pipeline_jobs")
    processing_jobs = list(jobs_ref.where("status", "==", "PROCESSING").stream())
    
    print("="*80)
    print("📋 所有 PROCESSING 状态的任务")
    print("="*80)
    print()
    
    zombie_jobs = []
    real_job_info = None
    
    for job in processing_jobs:
        job_id = job.id
        job_data = job.to_dict() or {}
        drama_name = job_data.get('drama_name', 'N/A')
        created_at = job_data.get('created_at', 'N/A')
        progress = job_data.get('progress', 'N/A')
        
        is_in_running = job_id in running_job_ids
        is_real = (real_job_id and job_id == real_job_id)
        
        if is_real:
            real_job_info = {
                'job_id': job_id,
                'drama_name': drama_name,
                'created_at': created_at,
                'progress': progress,
            }
            status_marker = "✅ 真实任务（将保留）"
        elif is_in_running:
            status_marker = "⚠️ 在 running_job_ids 中但可能不是真实任务"
            zombie_jobs.append({
                'job_id': job_id,
                'drama_name': drama_name,
                'created_at': created_at,
                'progress': progress,
                'reason': '在 running_job_ids 中但不是真实任务',
            })
        else:
            status_marker = "❌ 僵尸任务（将标记为 CANCELED）"
            zombie_jobs.append({
                'job_id': job_id,
                'drama_name': drama_name,
                'created_at': created_at,
                'progress': progress,
                'reason': '不在 running_job_ids 中',
            })
        
        print(f"Job ID: {job_id}")
        print(f"  状态: {status_marker}")
        print(f"  剧集: {drama_name}")
        print(f"  创建时间: {created_at}")
        print(f"  进度: {progress}")
        print()
    
    print("="*80)
    print("📊 总结")
    print("="*80)
    print()
    
    if real_job_info:
        print("✅ 真实任务（将保留）:")
        print(f"   Job ID: {real_job_info['job_id']}")
        print(f"   剧集: {real_job_info['drama_name']}")
        print()
    
    print(f"❌ 僵尸任务（将标记为 CANCELED）: {len(zombie_jobs)} 个")
    print()
    
    if zombie_jobs:
        print("僵尸任务列表:")
        for idx, job in enumerate(zombie_jobs, 1):
            print(f"  {idx}. {job['job_id']}")
            print(f"     剧集: {job['drama_name']}")
            print(f"     原因: {job['reason']}")
            print()
    
    if dry_run:
        print("="*80)
        print("ℹ️  这是预览模式（dry-run），不会实际修改数据")
        print("   要执行清理，请运行: python cleanup_zombie_jobs.py --execute")
        print("="*80)
        return zombie_jobs, real_job_id
    
    # Execute cleanup
    print("="*80)
    print("🚀 开始执行清理...")
    print("="*80)
    print()
    
    success_count = 0
    failed_count = 0
    
    for job in zombie_jobs:
        job_id = job['job_id']
        try:
            job_ref = firestore.collection("pipeline_jobs").document(job_id)
            job_ref.update({
                "status": "CANCELED",
                "progress": f"任务已取消（僵尸任务清理，原因: {job['reason']}）",
                "updated_at": SERVER_TIMESTAMP,
            })
            print(f"✅ {job_id}: 已标记为 CANCELED")
            success_count += 1
        except Exception as e:
            print(f"❌ {job_id}: 更新失败 - {e}")
            failed_count += 1
    
    print()
    print("="*80)
    print("📊 清理结果")
    print("="*80)
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    print()
    
    # Also clean up running_job_ids if needed
    if real_job_id and real_job_id not in running_job_ids:
        print("⚠️  真实任务不在 running_job_ids 中，更新并发控制文档...")
        try:
            control_ref.set({
                "running_job_ids": [real_job_id],
                "running_jobs": 1,
                "updated_at": SERVER_TIMESTAMP,
            }, merge=True)
            print("✅ 并发控制文档已更新")
        except Exception as e:
            print(f"❌ 更新并发控制文档失败: {e}")
    
    return zombie_jobs, real_job_id


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="清理僵尸任务")
    parser.add_argument("--execute", action="store_true", help="执行清理（默认是预览模式）")
    parser.add_argument("--yes", action="store_true", help="跳过确认提示（用于非交互式环境）")
    parser.add_argument("--execution", default=REAL_EXECUTION_NAME, help="真实任务的 execution 名称")
    parser.add_argument("--region", default=REAL_JOB_REGION, help="Cloud Run Job 区域")
    
    args = parser.parse_args()
    
    REAL_EXECUTION_NAME = args.execution
    REAL_JOB_REGION = args.region
    
    dry_run = not args.execute
    
    if dry_run:
        print("="*80)
        print("🔍 僵尸任务清理脚本（预览模式）")
        print("="*80)
        print()
    else:
        print("="*80)
        print("🚀 僵尸任务清理脚本（执行模式）")
        print("="*80)
        print()
        if not args.yes:
            try:
                response = input("⚠️  确认要执行清理吗？这将把僵尸任务标记为 CANCELED (yes/no): ")
                if response.lower() != "yes":
                    print("❌ 已取消")
                    sys.exit(0)
            except EOFError:
                print("⚠️  非交互式环境，使用 --yes 参数跳过确认")
                sys.exit(1)
        else:
            print("✅ 使用 --yes 参数，跳过确认")
        print()
    
    list_zombie_jobs(dry_run=dry_run)

