#!/usr/bin/env python3
"""Check Relay Service detailed logs."""

import sys
from pathlib import Path
from datetime import datetime, timezone

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import logging as cloud_logging

def main():
    client = cloud_logging.Client(project="fleet-blend-469520-n7")
    
    # Query for Relay Service logs around the time
    query = f"""
        resource.type=cloud_run_revision
        resource.labels.service_name=drama-processor-relay-service
        timestamp>="2025-11-23T10:42:00Z"
        timestamp<="2025-11-23T11:20:00Z"
    """
    
    print("=" * 60)
    print("Relay Service 详细日志")
    print("=" * 60)
    
    entries = client.list_entries(filter_=query, max_results=100)
    
    relevant_entries = []
    for entry in entries:
        payload = entry.payload
        if isinstance(payload, dict):
            message = payload.get('message', '')
        else:
            message = str(payload)
        
        # Filter for relevant messages
        if any(keyword in message.lower() for keyword in [
            'eventarc', 'relay', 'us032p03s01', 'fnfoqa3u32u0o8jug1qh',
            '匹配到', '未找到', 'queued', 'triggered', 'drama', 'job'
        ]):
            relevant_entries.append((entry.timestamp, message))
    
    if relevant_entries:
        print(f"找到 {len(relevant_entries)} 条相关日志:\n")
        for timestamp, message in relevant_entries[:50]:
            print(f"{timestamp}: {message}")
    else:
        print("未找到相关日志")
        print("\n尝试获取所有日志...")
        entries = client.list_entries(filter_=query, max_results=50)
        count = 0
        for entry in entries:
            count += 1
            payload = entry.payload
            if isinstance(payload, dict):
                message = payload.get('message', '')
            else:
                message = str(payload)
            print(f"{entry.timestamp}: {message[:200]}")
            if count >= 20:
                break

if __name__ == "__main__":
    main()


