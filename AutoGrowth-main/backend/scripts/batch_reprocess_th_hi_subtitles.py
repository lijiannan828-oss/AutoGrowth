#!/usr/bin/env python3
"""批量重新处理所有剧集的泰语和印地语字幕

脚本逻辑：
1. 获取所有剧集列表
2. 对每个剧集：
   - 选择 episodes 目录下的所有文件
   - 选择 subtitles/final 下的 th_translated, hi_translated, th, hi（如果存在）
3. 触发手动处理任务（在生产环境 Cloud Run 中执行）
4. 报告结果

⚠️  重要：此脚本必须在生产环境执行，或确保 APP_ENV=production
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Set
from google.cloud import storage

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# ⚠️  重要：强制设置为生产环境，确保任务在 Cloud Run 中执行
# 必须在导入 settings 之前设置
os.environ["APP_ENV"] = "production"
# 设置 PROCESSOR_JOB_NAME（如果未设置）
# 格式：projects/{project_id}/locations/{region}/jobs/{job_name}
if not os.environ.get("PROCESSOR_JOB_NAME"):
    # 默认值：根据项目配置
    project_id = "fleet-blend-469520-n7"
    region = "us-central1"
    job_name = "drama-processor-job"
    os.environ["PROCESSOR_JOB_NAME"] = f"projects/{project_id}/locations/{region}/jobs/{job_name}"

from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore
from app.services.pipeline_process_service import PipelineProcessService
from app.schemas.auth import AuthenticatedUser

# 目标字幕目录（相对路径）
TARGET_SUBTITLE_DIRS = [
    "subtitles/final/th_translated",
    "subtitles/final/hi_translated",
    "subtitles/final/th",
    "subtitles/final/hi",
]

# Episodes 目录
EPISODES_DIR = "episodes"


def get_all_dramas() -> List[str]:
    """从 GCS 获取所有剧集列表"""
    print("🔍 正在获取所有剧集列表...")
    
    bucket_name = settings.pipeline_gcs_source_bucket
    storage_client = storage.Client()
    
    dramas: Set[str] = set()
    
    # 使用 delimiter 列出顶级前缀（剧集目录）
    iterator = storage_client.list_blobs(
        bucket_name,
        delimiter="/",
        max_results=1000  # 限制结果数量
    )
    
    # 获取前缀列表
    prefixes = set()
    for page in iterator.pages:
        prefixes.update(page.prefixes)
    
    for prefix in prefixes:
        # 前缀格式: "drama_name/"
        drama_name = prefix.rstrip("/")
        if drama_name:
            dramas.add(drama_name)
    
    # 如果使用 pages 没有获取到前缀，尝试直接列出所有 blob 并提取前缀
    if not dramas:
        print("   ⚠️  使用 delimiter 未找到前缀，尝试直接列出文件...")
        blobs = storage_client.list_blobs(bucket_name, max_results=1000)
        for blob in blobs:
            # 提取第一个路径段作为剧集名
            parts = blob.name.split("/")
            if len(parts) > 1 and parts[0]:
                dramas.add(parts[0])
    
    drama_list = sorted(list(dramas))
    print(f"✅ 找到 {len(drama_list)} 个剧集")
    if drama_list:
        print(f"   示例: {drama_list[:5]}")
    return drama_list


def check_directory_exists(bucket_name: str, drama_name: str, dir_path: str) -> bool:
    """检查目录是否存在"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # 检查是否有以该路径开头的文件
    prefix = f"{drama_name}/{dir_path}/"
    blobs = list(bucket.list_blobs(prefix=prefix, max_results=1))
    return len(blobs) > 0


def get_selected_paths(drama_name: str) -> List[str]:
    """获取要选择的路径列表"""
    bucket_name = settings.pipeline_gcs_source_bucket
    selected_paths: List[str] = []
    
    # 1. 总是选择 episodes 目录
    if check_directory_exists(bucket_name, drama_name, EPISODES_DIR):
        selected_paths.append(EPISODES_DIR)
        print(f"   ✅ 找到: {EPISODES_DIR}")
    else:
        print(f"   ⚠️  未找到: {EPISODES_DIR}")
    
    # 2. 检查并选择目标字幕目录
    for sub_dir in TARGET_SUBTITLE_DIRS:
        if check_directory_exists(bucket_name, drama_name, sub_dir):
            selected_paths.append(sub_dir)
            print(f"   ✅ 找到: {sub_dir}")
        else:
            print(f"   ⚠️  未找到: {sub_dir}")
    
    return selected_paths


def main():
    print("="*80)
    print("🔄 批量重新处理泰语和印地语字幕")
    print("="*80)
    print()
    
    # 初始化
    init_firestore()
    
    # 验证环境设置
    current_env = os.environ.get("APP_ENV", "development")
    settings_env = settings.app_env
    print(f"📋 环境变量 APP_ENV: {current_env}")
    print(f"📋 settings.app_env: {settings_env}")
    print()
    
    if current_env != "production" or settings_env != "production":
        print("❌ 错误: 必须在生产环境执行此脚本！")
        print("   请设置环境变量: export APP_ENV=production")
        print("   或使用: APP_ENV=production python3 scripts/batch_reprocess_th_hi_subtitles.py")
        sys.exit(1)
    
    print("✅ 确认在生产环境执行，任务将在 Cloud Run 中运行")
    print()
    
    # 创建用户（用于触发任务）
    # 注意：is_dev_user=False 确保任务在 Cloud Run 中执行（不在本地 subprocess）
    user = AuthenticatedUser(
        email="system@autogrowth.com",
        email_prefix="system",
        name="Batch Reprocess Script",
        picture=None,
        user_id="batch-reprocess-script",
        is_dev_user=False,  # 重要：设置为 False 以确保在生产环境 Cloud Run 中执行
        auth_token="batch-script-token",
    )
    
    # 获取所有剧集
    dramas = get_all_dramas()
    
    if not dramas:
        print("❌ 未找到任何剧集")
        return
    
    print()
    print(f"📋 将处理 {len(dramas)} 个剧集")
    print()
    
    # 创建服务实例
    service = PipelineProcessService()
    
    # 存储结果
    results: List[Dict] = []
    success_count = 0
    skip_count = 0
    error_count = 0
    
    # 处理每个剧集
    for idx, drama_name in enumerate(dramas, 1):
        print(f"\n[{idx}/{len(dramas)}] 处理剧集: {drama_name}")
        print("-" * 80)
        
        try:
            # 获取要选择的路径
            selected_paths = get_selected_paths(drama_name)
            
            if not selected_paths:
                print(f"   ⚠️  跳过：未找到任何目标目录")
                skip_count += 1
                results.append({
                    "drama_name": drama_name,
                    "status": "skipped",
                    "job_id": None,
                    "selected_paths": [],
                    "reason": "未找到任何目标目录"
                })
                continue
            
            # 触发手动处理任务
            # 注意：trigger_manual_process_job 会自动提取语言并设置 allowed_languages
            # 这样确保只处理 th 和 hi 语言的字幕
            print(f"   🚀 触发处理任务，选择路径: {selected_paths}")
            print(f"   📝 预期语言: th, hi")
            job_id = service.trigger_manual_process_job(
                drama_name=drama_name,
                file_paths=selected_paths,
                current_user=user
            )
            
            print(f"   ✅ 任务已创建: {job_id}")
            success_count += 1
            results.append({
                "drama_name": drama_name,
                "status": "queued",
                "job_id": job_id,
                "selected_paths": selected_paths,
            })
            
        except Exception as e:
            print(f"   ❌ 处理失败: {e}")
            error_count += 1
            results.append({
                "drama_name": drama_name,
                "status": "error",
                "job_id": None,
                "selected_paths": [],
                "error": str(e)
            })
            import traceback
            traceback.print_exc()
    
    # 打印汇总
    print()
    print("="*80)
    print("📊 处理结果汇总")
    print("="*80)
    print()
    print(f"总剧集数: {len(dramas)}")
    print(f"✅ 成功排队: {success_count}")
    print(f"⚠️  跳过: {skip_count}")
    print(f"❌ 失败: {error_count}")
    print()
    
    # 打印详细结果
    print("="*80)
    print("📋 详细结果")
    print("="*80)
    print()
    
    queued_results = [r for r in results if r["status"] == "queued"]
    
    if queued_results:
        print(f"✅ 已排队的剧集 ({len(queued_results)} 个):")
        print()
        for result in queued_results:
            print(f"剧集: {result['drama_name']}")
            print(f"  任务 ID: {result['job_id']}")
            print(f"  选择路径:")
            for path in result['selected_paths']:
                print(f"    - {path}")
            print()
    else:
        print("⚠️  没有成功排队的剧集")
        print()
    
    if skip_count > 0:
        skipped_results = [r for r in results if r["status"] == "skipped"]
        print(f"⚠️  跳过的剧集 ({skip_count} 个):")
        for result in skipped_results:
            print(f"  - {result['drama_name']}: {result.get('reason', 'N/A')}")
        print()
    
    if error_count > 0:
        error_results = [r for r in results if r["status"] == "error"]
        print(f"❌ 失败的剧集 ({error_count} 个):")
        for result in error_results:
            print(f"  - {result['drama_name']}: {result.get('error', 'N/A')}")
        print()
    
    # 保存结果到文件
    import json
    output_file = Path(__file__).parent / "batch_reprocess_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"📄 详细结果已保存到: {output_file}")
    print()
    
    print("="*80)
    print("✅ 批量处理完成")
    print("="*80)


if __name__ == "__main__":
    main()

