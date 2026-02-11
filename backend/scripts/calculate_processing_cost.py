#!/usr/bin/env python3
"""Calculate processing cost for video processing job."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.firestore import init_firestore, get_firestore_client

# GCP Pricing (as of 2024, us-central1 region)
# Source: https://cloud.google.com/run/pricing

# Cloud Run Jobs Pricing (us-central1)
# Source: https://cloud.google.com/run/pricing
CPU_PRICE_PER_VCPU_SECOND = 0.00002400  # $0.00002400 per vCPU-second
CPU_PRICE_PER_VCPU_HOUR = CPU_PRICE_PER_VCPU_SECOND * 3600  # $0.0864 per vCPU-hour
MEMORY_PRICE_PER_GB_SECOND = 0.00000250  # $0.00000250 per GB-second
MEMORY_PRICE_PER_GB_HOUR = MEMORY_PRICE_PER_GB_SECOND * 3600  # $0.009 per GB-hour
MINIMUM_BILLING_TIME = 100  # Minimum 100ms billing

# GCS Pricing (us-central1)
STORAGE_PRICE_PER_GB_MONTH = 0.020  # Standard storage, $0.020 per GB per month
NETWORK_EGRESS_PRICE_PER_GB = 0.12  # Egress to internet, first 10TB free per month
NETWORK_INGRESS_FREE = True  # Ingress is free

# Estimated file sizes (for cost calculation)
AVERAGE_VIDEO_SIZE_MB = 500  # Average video file size in MB
AVERAGE_OUTPUT_SIZE_MB = 450  # Average output file size in MB (compressed)


def calculate_cloud_run_cost(cpu: float, memory_gb: float, duration_hours: float, task_count: int, parallelism: int):
    """Calculate Cloud Run Jobs cost.
    
    Args:
        cpu: Number of vCPUs per task
        memory_gb: Memory in GB per task
        duration_hours: Total execution duration in hours
        task_count: Total number of tasks
        parallelism: Maximum concurrent tasks
    """
    # Cloud Run Jobs bills for actual vCPU-seconds and memory-seconds used
    # For parallel execution, we need to account for concurrent tasks
    
    # Calculate effective concurrent time
    # If parallelism=50 and task_count=100, we have 2 batches
    # Each batch runs sequentially, so total duration = batch_duration × batches
    batches = (task_count + parallelism - 1) // parallelism  # Ceiling division
    batch_duration_hours = duration_hours / batches if batches > 0 else duration_hours
    batch_duration_seconds = batch_duration_hours * 3600
    
    # Total vCPU-seconds = parallelism × cpu × batch_duration_seconds × batches
    # This accounts for sequential batches: each batch runs for batch_duration
    total_vcpu_seconds = parallelism * cpu * batch_duration_seconds * batches
    
    # Total memory-GB-seconds = parallelism × memory_gb × batch_duration_seconds × batches
    total_memory_gb_seconds = parallelism * memory_gb * batch_duration_seconds * batches
    
    # Calculate costs (using per-second pricing)
    cpu_cost = total_vcpu_seconds * CPU_PRICE_PER_VCPU_SECOND
    memory_cost = total_memory_gb_seconds * MEMORY_PRICE_PER_GB_SECOND
    
    total_cost = cpu_cost + memory_cost
    
    return {
        "cpu_seconds": total_vcpu_seconds,
        "cpu_hours": total_vcpu_seconds / 3600,
        "memory_gb_seconds": total_memory_gb_seconds,
        "memory_gb_hours": total_memory_gb_seconds / 3600,
        "cpu_cost": cpu_cost,
        "memory_cost": memory_cost,
        "total_cost": total_cost,
        "batches": batches,
        "batch_duration_hours": batch_duration_hours,
    }


def calculate_gcs_cost(file_count: int, input_size_mb: float, output_size_mb: float):
    """Calculate GCS storage and network costs.
    
    Args:
        file_count: Number of files processed
        input_size_mb: Average input file size in MB
        output_size_mb: Average output file size in MB
    """
    # Storage cost (assuming files stored for 1 month)
    total_input_gb = (file_count * input_size_mb) / 1024
    total_output_gb = (file_count * output_size_mb) / 1024
    
    # Storage cost (per month, pro-rated for processing time)
    # Assuming files are stored for processing duration only
    storage_cost = (total_input_gb + total_output_gb) * STORAGE_PRICE_PER_GB_MONTH / 30  # Per day
    
    # Network egress cost (downloading input, uploading output)
    # Input: downloading from source bucket (if different region, but usually free)
    # Output: uploading to processed bucket (ingress is free)
    # Egress: only if downloading to external (usually internal, so minimal)
    network_cost = 0  # Usually minimal for internal transfers
    
    return {
        "input_storage_gb": total_input_gb,
        "output_storage_gb": total_output_gb,
        "storage_cost": storage_cost,
        "network_cost": network_cost,
        "total_gcs_cost": storage_cost + network_cost,
    }


def main():
    """Main cost calculation."""
    print("=" * 80)
    print("  视频压制成本核算")
    print("=" * 80)
    print()
    
    job_id = "akln3K9gWpb6dJdJuWbE"
    
    # Get job data
    init_firestore()
    firestore = get_firestore_client()
    job_ref = firestore.collection("pipeline_jobs").document(job_id)
    job_data = job_ref.get().to_dict() or {}
    
    total_files = job_data.get("total_files", 0)
    processed_files = job_data.get("processed_files", 0)
    created_at = job_data.get("created_at")
    updated_at = job_data.get("updated_at")
    
    print(f"Job ID: {job_id}")
    print(f"Total Files: {total_files}")
    print(f"Processed Files: {processed_files}")
    print()
    
    # Calculate duration
    if created_at and updated_at and isinstance(created_at, datetime) and isinstance(updated_at, datetime):
        elapsed = (updated_at - created_at).total_seconds()
        elapsed_hours = elapsed / 3600
        
        # Estimate total duration based on current progress
        if processed_files > 0:
            files_per_hour = processed_files / elapsed_hours if elapsed_hours > 0 else 0
            estimated_total_hours = total_files / files_per_hour if files_per_hour > 0 else 0
        else:
            estimated_total_hours = elapsed_hours
        
        print(f"已用时间: {elapsed_hours:.2f} 小时")
        if processed_files > 0:
            print(f"预计总时间: {estimated_total_hours:.2f} 小时")
        print()
    else:
        estimated_total_hours = 2.0  # Default estimate
        print("⚠️  无法获取准确时间，使用估算值")
        print()
    
    # Cloud Run Job configuration
    cpu = 2.0  # vCPUs per task
    memory_gb = 4.0  # GB per task
    task_count = 100
    parallelism = 50
    
    print("Cloud Run Job 配置:")
    print(f"  CPU: {cpu} vCPU per task")
    print(f"  Memory: {memory_gb} GB per task")
    print(f"  Task Count: {task_count}")
    print(f"  Parallelism: {parallelism}")
    print()
    
    # Calculate Cloud Run cost
    cloud_run_cost = calculate_cloud_run_cost(
        cpu=cpu,
        memory_gb=memory_gb,
        duration_hours=estimated_total_hours,
        task_count=task_count,
        parallelism=parallelism,
    )
    
    print("Cloud Run Jobs 成本:")
    print(f"  总 vCPU-秒: {cloud_run_cost['cpu_seconds']:.0f} ({cloud_run_cost['cpu_hours']:.2f} 小时)")
    print(f"  总内存-GB-秒: {cloud_run_cost['memory_gb_seconds']:.0f} ({cloud_run_cost['memory_gb_hours']:.2f} GB-小时)")
    print(f"  CPU 成本: ${cloud_run_cost['cpu_cost']:.4f}")
    print(f"  内存成本: ${cloud_run_cost['memory_cost']:.4f}")
    print(f"  Cloud Run 总成本: ${cloud_run_cost['total_cost']:.4f}")
    print(f"  执行批次: {cloud_run_cost['batches']} (每批 {cloud_run_cost['batch_duration_hours']:.2f} 小时)")
    print()
    
    # Calculate GCS cost
    gcs_cost = calculate_gcs_cost(
        file_count=total_files,
        input_size_mb=AVERAGE_VIDEO_SIZE_MB,
        output_size_mb=AVERAGE_OUTPUT_SIZE_MB,
    )
    
    print("GCS 存储成本 (估算):")
    print(f"  输入存储: {gcs_cost['input_storage_gb']:.2f} GB")
    print(f"  输出存储: {gcs_cost['output_storage_gb']:.2f} GB")
    print(f"  存储成本: ${gcs_cost['storage_cost']:.4f} (按天计算)")
    print(f"  网络成本: ${gcs_cost['network_cost']:.4f}")
    print(f"  GCS 总成本: ${gcs_cost['total_gcs_cost']:.4f}")
    print()
    
    # Total cost
    total_cost = cloud_run_cost['total_cost'] + gcs_cost['total_gcs_cost']
    
    print("=" * 80)
    print("  总成本估算")
    print("=" * 80)
    print(f"  Cloud Run Jobs: ${cloud_run_cost['total_cost']:.4f}")
    print(f"  GCS 存储: ${gcs_cost['total_gcs_cost']:.4f}")
    print(f"  总计: ${total_cost:.4f}")
    print()
    print(f"  每文件成本: ${total_cost / total_files:.6f}")
    print(f"  每小时成本: ${total_cost / estimated_total_hours:.4f}")
    print()
    
    # Cost breakdown
    print("成本构成:")
    cloud_run_pct = (cloud_run_cost['total_cost'] / total_cost * 100) if total_cost > 0 else 0
    gcs_pct = (gcs_cost['total_gcs_cost'] / total_cost * 100) if total_cost > 0 else 0
    print(f"  Cloud Run: {cloud_run_pct:.1f}%")
    print(f"  GCS: {gcs_pct:.1f}%")
    print()
    
    # Note
    print("注意:")
    print("  - 价格基于 GCP 官方定价 (us-central1)")
    print("  - Cloud Run Jobs 按实际使用时间计费")
    print("  - GCS 存储成本按天估算（实际可能更少）")
    print("  - 网络传输成本通常很低（内部传输）")
    print("  - 实际成本可能因文件大小、处理时间等因素有所不同")


if __name__ == "__main__":
    main()

