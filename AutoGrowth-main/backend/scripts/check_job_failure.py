#!/usr/bin/env python3
"""Check failure details for a specific processing job.

Usage:
    python scripts/check_job_failure.py --job-id 6zKeRnWRLsgaxIDwR4HD
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import firestore
from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore


def check_job_details(job_id: str) -> Dict | None:
    """Get job details from Firestore."""
    init_firestore()
    client = get_firestore_client()
    doc_ref = client.collection("pipeline_jobs").document(job_id)
    snapshot = doc_ref.get()
    
    if not snapshot.exists:
        return None
    
    return snapshot.to_dict()


def check_failures(job_id: str) -> List[Dict]:
    """Get all failure records for a job."""
    init_firestore()
    client = get_firestore_client()
    failure_collection = client.collection("processing_failures")
    
    query = failure_collection.where("job_id", "==", job_id)
    failures = []
    for doc in query.stream():
        failures.append({
            "failure_id": doc.id,
            **doc.to_dict()
        })
    
    return sorted(failures, key=lambda x: (x.get("episode", ""), x.get("language", "")))


def analyze_failures(failures: List[Dict]) -> Dict:
    """Analyze failure patterns."""
    if not failures:
        return {}
    
    analysis = {
        "total_failures": len(failures),
        "unique_episodes": len(set(f.get("episode") for f in failures)),
        "unique_languages": len(set(f.get("language") for f in failures)),
        "error_patterns": {},
        "episode_range": None,
        "failure_distribution": {},
    }
    
    # Analyze error patterns
    for failure in failures:
        error_msg = failure.get("error_message", "")
        if error_msg:
            # Extract first line of error as pattern
            first_line = error_msg.split("\n")[0].strip()[:150]
            if first_line:
                analysis["error_patterns"][first_line] = analysis["error_patterns"].get(first_line, 0) + 1
    
    # Episode range
    episodes = []
    for failure in failures:
        episode = failure.get("episode", "")
        if episode and episode.isdigit():
            episodes.append(int(episode))
    
    if episodes:
        episodes.sort()
        analysis["episode_range"] = {
            "first": episodes[0],
            "last": episodes[-1],
            "count": len(episodes),
        }
    
    # Failure distribution by episode
    for failure in failures:
        episode = failure.get("episode", "unknown")
        analysis["failure_distribution"][episode] = analysis["failure_distribution"].get(episode, 0) + 1
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description="Check job failure details")
    parser.add_argument("--job-id", required=True, help="Job ID")
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"🔍 检查 Job 失败详情")
    print("=" * 80)
    print(f"\nJob ID: {args.job_id}")
    
    # Step 1: Check job details
    print("\n" + "=" * 80)
    print("步骤 1: Job 基本信息")
    print("=" * 80)
    job_data = check_job_details(args.job_id)
    if not job_data:
        print(f"❌ Job {args.job_id} 不存在")
        return 1
    
    print(f"✅ Job 存在")
    print(f"   Drama Name: {job_data.get('drama_name')}")
    print(f"   Status: {job_data.get('status')}")
    print(f"   Stage: {job_data.get('stage')}")
    print(f"   Progress: {job_data.get('progress')}")
    print(f"   Processed: {job_data.get('processed_files', 0)}/{job_data.get('processed_total', 0)}")
    print(f"   Created At: {job_data.get('created_at')}")
    print(f"   Updated At: {job_data.get('updated_at')}")
    
    # Check last_event for failure info
    last_event = job_data.get("last_event", {})
    if last_event:
        print(f"\n   最后事件:")
        print(f"     Type: {last_event.get('type')}")
        if last_event.get("error"):
            print(f"     Error: {last_event.get('error')}")
    
    # Step 2: Check failures
    print("\n" + "=" * 80)
    print("步骤 2: 失败记录详情")
    print("=" * 80)
    failures = check_failures(args.job_id)
    
    if not failures:
        print("⚠️  没有找到失败记录（processing_failures 集合中）")
        print("\n可能的原因：")
        print("1. Job 在失败前没有记录失败详情（可能在配对阶段失败）")
        print("2. Job 因为其他原因失败（如超时、内存不足、容器崩溃等）")
        print("3. 失败记录写入失败")
    else:
        print(f"✅ 找到 {len(failures)} 个失败记录\n")
        
        # Analyze failures
        analysis = analyze_failures(failures)
        
        print(f"失败统计:")
        print(f"  总失败数: {analysis['total_failures']}")
        print(f"  失败集数: {analysis['unique_episodes']}")
        print(f"  失败语言: {analysis['unique_languages']}")
        
        if analysis.get("episode_range"):
            ep_range = analysis["episode_range"]
            print(f"\n失败集数范围:")
            print(f"  第一个失败: EP{ep_range['first']:03d}")
            print(f"  最后一个失败: EP{ep_range['last']:03d}")
            print(f"  失败集数总数: {ep_range['count']}")
            
            # Check if 185th failure exists
            if len(failures) >= 185:
                failure_185 = failures[184]  # 0-indexed
                print(f"\n第185个失败记录:")
                print(f"  Episode: {failure_185.get('episode')}")
                print(f"  Language: {failure_185.get('language')}")
                print(f"  Video: {failure_185.get('video_gcs_path', 'N/A')}")
                print(f"  Subtitle: {failure_185.get('subtitle_gcs_path', 'N/A')}")
                error_msg = failure_185.get('error_message', 'N/A')
                print(f"  Error (前500字符):")
                print(f"    {error_msg[:500]}")
                if len(error_msg) > 500:
                    print(f"    ... (还有 {len(error_msg) - 500} 字符)")
        
        # Error patterns
        if analysis.get("error_patterns"):
            print("\n" + "=" * 80)
            print("步骤 3: 错误模式分析")
            print("=" * 80)
            
            print(f"\n最常见的错误类型（前10个）:")
            sorted_patterns = sorted(analysis["error_patterns"].items(), key=lambda x: -x[1])
            for i, (error, count) in enumerate(sorted_patterns[:10], 1):
                percentage = (count / len(failures)) * 100
                print(f"\n{i}. {count} 次 ({percentage:.1f}%):")
                print(f"   {error}")
        
        # Show sample failures with full error messages
        print("\n" + "=" * 80)
        print("步骤 4: 失败记录样本（前5个，完整错误信息）")
        print("=" * 80)
        
        for i, failure in enumerate(failures[:5], 1):
            print(f"\n{'='*80}")
            print(f"{i}. Episode: {failure.get('episode')} | Language: {failure.get('language')}")
            print(f"   Video: {failure.get('video_gcs_path', 'N/A')}")
            print(f"   Subtitle: {failure.get('subtitle_gcs_path', 'N/A')}")
            error_msg = failure.get('error_message', 'N/A')
            print(f"\n   完整错误信息:")
            print(f"   {'-'*76}")
            if error_msg:
                # Print error message with indentation
                for line in error_msg.split('\n'):
                    print(f"   {line}")
            else:
                print(f"   N/A")
            print(f"   {'-'*76}")
    
    # Step 3: Summary
    print("\n" + "=" * 80)
    print("📊 总结")
    print("=" * 80)
    
    status = job_data.get("status")
    processed = job_data.get("processed_files", 0)
    total = job_data.get("processed_total", 0)
    
    print(f"\n1. 任务整体失败原因:")
    if status == "FAILED":
        progress_msg = job_data.get("progress", "Unknown")
        print(f"   ❌ Job 状态: FAILED")
        print(f"   失败消息: {progress_msg}")
        
        if not failures:
            print(f"\n   ⚠️  没有找到 processing_failures 记录，可能的原因：")
            print(f"   - Job 在配对阶段失败（配对失败不会记录到 processing_failures）")
            print(f"   - Job 因为系统级错误失败（超时、内存不足、容器崩溃等）")
            print(f"   - 失败记录写入失败")
        else:
            print(f"\n   ✅ 找到 {len(failures)} 个失败记录")
            if processed < total:
                print(f"   - 成功处理: {processed}/{total}")
                print(f"   - 失败数量: {total - processed}")
                print(f"   - 失败率: {((total - processed) / total * 100):.1f}%")
    elif status == "COMPLETE":
        if processed < total:
            print(f"   ⚠️  Job 状态: COMPLETE，但只处理了 {processed}/{total} 个文件")
        else:
            print(f"   ✅ Job 状态: COMPLETE")
    else:
        print(f"   ℹ️  Job 状态: {status}")
    
    if failures:
        print(f"\n2. 多个视频压制失败的原因:")
        analysis = analyze_failures(failures)
        
        if analysis.get("error_patterns"):
            sorted_patterns = sorted(analysis["error_patterns"].items(), key=lambda x: -x[1])
            top_error = sorted_patterns[0]
            top_error_count = top_error[1]
            top_error_percentage = (top_error_count / len(failures)) * 100
            
            print(f"   主要错误类型（占 {top_error_percentage:.1f}% 的失败）:")
            print(f"   {top_error[0]}")
            
            if top_error_percentage > 50:
                print(f"\n   ✅ 这是主要错误类型，建议优先解决此问题")
            else:
                print(f"\n   ⚠️  错误类型较分散，可能有多个原因")
                print(f"   前3个错误类型:")
                for i, (error, count) in enumerate(sorted_patterns[:3], 1):
                    percentage = (count / len(failures)) * 100
                    print(f"     {i}. {count} 次 ({percentage:.1f}%): {error[:100]}")
        else:
            print(f"   ⚠️  无法分析错误模式（错误信息为空）")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

