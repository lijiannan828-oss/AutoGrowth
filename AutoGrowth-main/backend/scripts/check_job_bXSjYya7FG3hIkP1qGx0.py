#!/usr/bin/env python3
"""检查任务 bXSjYya7FG3hIkP1qGx0 的状态和日志"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.firestore import init_firestore, get_firestore_client
from google.cloud import logging as cloud_logging

def main():
    job_id = "bXSjYya7FG3hIkP1qGx0"
    
    # 初始化 Firestore
    init_firestore()
    firestore = get_firestore_client()
    
    # 检查任务状态
    job_ref = firestore.collection("pipeline_jobs").document(job_id)
    job_snapshot = job_ref.get()
    
    if job_snapshot.exists:
        job_data = job_snapshot.to_dict() or {}
        print(f"📋 Job {job_id} 状态:")
        print(f"  status: {job_data.get('status', 'N/A')}")
        print(f"  progress: {job_data.get('progress', 'N/A')}")
        print(f"  total_files: {job_data.get('total_files', 'N/A')}")
        print(f"  processed_files: {job_data.get('processed_files', 'N/A')}")
        print(f"  failed_files: {job_data.get('failed_files', 'N/A')}")
        print(f"  updated_at: {job_data.get('updated_at', 'N/A')}")
        
        # 检查任务文档
        tasks_ref = job_ref.collection("tasks")
        tasks = tasks_ref.stream()
        task_count = 0
        for task in tasks:
            task_count += 1
            task_data = task.to_dict() or {}
            print(f"\n  Task {task.id}:")
            print(f"    status: {task_data.get('status', 'N/A')}")
            print(f"    success_files: {len(task_data.get('success_files', []))}")
            print(f"    failed_files: {len(task_data.get('failed_files', []))}")
        print(f"\n  总任务数: {task_count}")
    else:
        print(f"❌ Job {job_id} 不存在")
    
    # 检查 Cloud Logging
    print(f"\n🔍 检查 Cloud Logging...")
    try:
        logging_client = cloud_logging.Client(project="fleet-blend-469520-n7")
        filter_str = f'resource.type="cloud_run_job" AND resource.labels.job_name="drama-processor-job" AND (textPayload=~"{job_id}" OR jsonPayload.job_id="{job_id}")'
        
        entries = logging_client.list_entries(
            filter_=filter_str,
            order_by=cloud_logging.DESCENDING,
            max_results=50
        )
        
        print(f"\n📝 最近的日志条目:")
        font_logs = []
        startup_logs = []
        pairing_logs = []
        
        for entry in entries:
            payload = entry.payload
            if isinstance(payload, dict):
                message = payload.get('message', '') or payload.get('textPayload', '')
            else:
                message = str(payload)
            
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            if '字体' in message or 'font' in message.lower() or 'fc-list' in message or 'TH' in message or 'HI' in message:
                font_logs.append(f"{timestamp}: {message}")
            if 'Worker' in message or '启动' in message or '执行' in message or 'Running' in message:
                startup_logs.append(f"{timestamp}: {message}")
            if '配对' in message or 'discover_file_pairs' in message or 'total_files' in message:
                pairing_logs.append(f"{timestamp}: {message}")
        
        print(f"\n🎨 字体相关日志 ({len(font_logs)} 条):")
        for log in font_logs[:10]:
            print(f"  {log}")
        
        print(f"\n🚀 启动相关日志 ({len(startup_logs)} 条):")
        for log in startup_logs[:10]:
            print(f"  {log}")
        
        print(f"\n📁 文件配对相关日志 ({len(pairing_logs)} 条):")
        for log in pairing_logs[:10]:
            print(f"  {log}")
            
    except Exception as e:
        print(f"⚠️ 无法读取 Cloud Logging: {e}")
        print("   请确保已设置 GOOGLE_APPLICATION_CREDENTIALS")

if __name__ == "__main__":
    main()

