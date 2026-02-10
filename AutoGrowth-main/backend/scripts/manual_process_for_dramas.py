#!/usr/bin/env python3
"""Create Firestore jobs and trigger drama-processor for specific GCS dramas."""

from __future__ import annotations

from typing import List

from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.config import settings
from app.core.firestore import get_firestore_client, init_firestore
from app.services.pipeline_process_service import PipelineProcessService

TARGET_DRAMAS: List[str] = [
    "KR069P12S01_아무 짝에 쓸모 없는 사랑",
    "KR051P07S01_김대표의 엽기적인 부인",
]


def create_pipeline_job(drama_name: str) -> str:
    firestore_client = get_firestore_client()
    doc_ref = firestore_client.collection("pipeline_jobs").document()
    body = {
        "drama_name": drama_name,
        "gdrive_path": f"KR Programs/{drama_name}",
        "status": "QUEUED",
        "stage": 1,
        "progress": "等待压制（手动创建任务）",
        "transfer_completed": True,
        "gcs_source_bucket": settings.pipeline_gcs_source_bucket,
        "gcs_processed_bucket": settings.pipeline_gcs_processed_bucket,
        "auth_mode": "manual",
        "type": "manual",
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
        "last_event": {
            "type": "MANUAL_PROCESS_REQUESTED",
            "timestamp": SERVER_TIMESTAMP,
        },
    }
    doc_ref.set(body)
    print(f"📝 Firestore job created for {drama_name} (job_id={doc_ref.id})")
    return doc_ref.id


def main() -> None:
    init_firestore()
    service = PipelineProcessService()
    job_ids: List[str] = []
    for drama in TARGET_DRAMAS:
        job_id = create_pipeline_job(drama)
        job_ids.append(job_id)
        service._trigger_process_worker(job_id)
        print(f"🚀 Triggered processor job for {drama} (job_id={job_id})")

    print("✅ All requested dramas have been enqueued:", ", ".join(job_ids))


if __name__ == "__main__":
    main()



