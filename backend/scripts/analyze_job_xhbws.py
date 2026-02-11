"""分析 Job xhbws 的文件配对和日志

使用方法:
    python -m backend.scripts.analyze_job_xhbws
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.firestore import get_firestore_client, init_firestore
from app.services.pipeline_discovery_service import discover_file_pairs

job_id = 'JOTGhe9omCEXXwbzdyvx'
drama_name = "US044P01S01_Runaway Prince's Secret Vacation"

def analyze_file_pairs():
    """分析文件配对"""
    print("=" * 60)
    print("分析文件配对")
    print("=" * 60)
    
    init_firestore()
    
    try:
        pairs = discover_file_pairs(
            drama_name=drama_name,
            source_bucket="vigloo_source",
            allowed_languages={'th', 'hi'}  # 只查询 th 和 hi
        )
        
        print(f"\n找到 {len(pairs)} 个配对")
        
        # 按语言统计
        lang_count = {}
        ep_count = {}
        ep_lang_count = {}
        
        for pair in pairs:
            lang = pair.language
            ep = pair.episode
            lang_count[lang] = lang_count.get(lang, 0) + 1
            ep_count[ep] = ep_count.get(ep, 0) + 1
            
            key = f"{ep}_{lang}"
            ep_lang_count[key] = ep_lang_count.get(key, 0) + 1
        
        print(f"\n按语言统计:")
        for lang, count in sorted(lang_count.items()):
            print(f"  {lang}: {count} 个配对")
        
        print(f"\n按集数统计:")
        sorted_eps = sorted(ep_count.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        for ep in sorted_eps[:30]:
            lang_for_ep = [k.split('_')[1] for k in ep_lang_count.keys() if k.startswith(f"{ep}_")]
            print(f"  ep{ep}: {ep_count[ep]} 个配对 ({', '.join(set(lang_for_ep))})")
        
        if len(sorted_eps) > 30:
            print(f"  ... 还有 {len(sorted_eps) - 30} 个集数")
        
        print(f"\n总集数: {len(ep_count)}")
        print(f"总配对: {len(pairs)}")
        
        # 检查重复配对
        pair_keys = {}
        duplicates = []
        for pair in pairs:
            key = f"{pair.episode}_{pair.language}"
            if key in pair_keys:
                duplicates.append((key, pair.video_path, pair.subtitle_path))
            pair_keys[key] = pair_keys.get(key, 0) + 1
        
        if duplicates:
            print(f"\n⚠️  发现 {len(set(duplicates))} 个重复配对:")
            for key, video, subtitle in set(duplicates)[:10]:
                print(f"  {key}:")
                print(f"    video: {video}")
                print(f"    subtitle: {subtitle}")
        
        # 分析为什么是 108 个
        if len(ep_count) == 50:
            print(f"\n分析:")
            print(f"  50集 × 平均 {len(pairs)/50:.2f} 个配对/集 = {len(pairs)} 个配对")
            if len(pairs) == 108:
                print(f"  108 = 50集 × 2.16 个配对/集")
                print(f"  可能原因:")
                print(f"    - 50集 × 2个语言 (th, hi) = 100 个配对")
                print(f"    - 某些集有额外的字幕文件 = 108 个配对")
                print(f"    - 或者某些集有多个字幕版本")
        
        return pairs
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def check_job_status():
    """检查 Job 状态"""
    print("\n" + "=" * 60)
    print("检查 Job 状态")
    print("=" * 60)
    
    init_firestore()
    firestore_client = get_firestore_client()
    
    job_ref = firestore_client.collection("pipeline_jobs").document(job_id)
    job_doc = job_ref.get()
    
    if job_doc.exists:
        job_data = job_doc.to_dict() or {}
        
        print(f"\nJob 信息:")
        print(f"  状态: {job_data.get('status', 'N/A')}")
        print(f"  总文件数: {job_data.get('total_files', 0)}")
        print(f"  已处理: {job_data.get('processed_files', 0)}")
        print(f"  失败: {job_data.get('failed_files', 0)}")
        print(f"  处理语言: {job_data.get('process_languages', [])}")
        
        # 查询任务文档
        task_count = job_data.get('task_count', 0)
        print(f"\n任务数量: {task_count}")
        
        # 查询失败的任务
        failed_tasks = []
        for task_num in range(min(task_count, 20)):
            task_id = f"{job_id}-task-{task_num}"
            task_ref = firestore_client.collection("pipeline_jobs").document(task_id)
            task_doc = task_ref.get()
            
            if task_doc.exists:
                task_data = task_doc.to_dict() or {}
                status = task_data.get('status', 'UNKNOWN')
                if status == 'FAILED':
                    failed_tasks.append((task_num, task_data.get('error', '')))
        
        if failed_tasks:
            print(f"\n失败的任务 ({len(failed_tasks)} 个):")
            for task_num, error in failed_tasks[:5]:
                print(f"  任务 {task_num}: {error[:200]}")


if __name__ == '__main__':
    pairs = analyze_file_pairs()
    check_job_status()
    
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)
    print(f"\n建议:")
    print(f"  1. 查看 GCP Console 日志查找 FFmpeg 错误")
    print(f"  2. 检查字体是否正确加载")
    print(f"  3. 验证输出文件中的泰语字幕")

