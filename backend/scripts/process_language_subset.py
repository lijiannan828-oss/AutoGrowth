#!/usr/bin/env python3
"""
Helper script to run the process worker against a limited set of languages/episodes.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.core.firestore import get_firestore_client, init_firestore
from app.workers.process.main import COLLECTION_NAME, DramaProcessWorker, _log


def _ensure_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少必要的环境变量：{name}")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run drama processor on a limited set of languages/episodes."
    )
    parser.add_argument(
        "--drama-name",
        default="KR065P01S01_죽여야하는,로맨스",
        help="GCS prefix under vigloo_source to process.",
    )
    parser.add_argument(
        "--gdrive-path",
        default="KR Programs/KR065P01S01_죽여야하는,로맨스",
        help="Optional Drive path reference for the job document.",
    )
    parser.add_argument(
        "--source-bucket",
        default="vigloo_source",
        help="Source bucket that contains original media.",
    )
    parser.add_argument(
        "--processed-bucket",
        default="vigloo_processed",
        help="Target bucket for processed media.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["en", "ko", "ja_translated", "es_translated"],
        help="Languages to process (match folder names under Subtitles).",
    )
    parser.add_argument(
        "--pairs",
        type=int,
        default=5,
        help="Max number of episode pairs to process per language.",
    )
    parser.add_argument(
        "--job-id",
        help="Existing Firestore job document ID to reuse. If omitted, a new doc will be created.",
    )
    parser.add_argument(
        "--app-env",
        default=os.environ.get("APP_ENV", "development"),
        help="APP_ENV value to run with (default: development).",
    )
    return parser.parse_args()


def _prepare_job_document(args: argparse.Namespace) -> str:
    init_firestore()
    client = get_firestore_client()
    collection = client.collection(COLLECTION_NAME)

    payload = {
        "drama_name": args.drama_name,
        "gdrive_path": args.gdrive_path,
        "gcs_source_bucket": args.source_bucket,
        "gcs_processed_bucket": args.processed_bucket,
        "status": "QUEUED",
        "stage": 2,
        "process_languages": args.languages,
        "max_pairs_per_language": args.pairs,
        "manual_test": True,
        "notes": "Language subset test run",
        "updated_at": SERVER_TIMESTAMP,
        "created_at": SERVER_TIMESTAMP,
    }

    if args.job_id:
        doc_ref = collection.document(args.job_id)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            raise RuntimeError(f"指定的 JOB_ID {args.job_id} 不存在")
        doc_ref.update(payload)
        job_id = args.job_id
    else:
        doc_ref = collection.document()
        doc_ref.set(payload)
        job_id = doc_ref.id

    _log(
        f"🗂️ Firestore Job Ready: {job_id} | Languages={args.languages} | "
        f"MaxPairsPerLang={args.pairs}"
    )
    return job_id


def main() -> None:
    args = _parse_args()
    _ensure_env("GOOGLE_APPLICATION_CREDENTIALS")
    os.environ["APP_ENV"] = args.app_env

    job_id = _prepare_job_document(args)
    os.environ["JOB_ID"] = job_id

    _log(
        "🚀 Starting DramaProcessWorker for subset validation "
        f"(JOB_ID={job_id}, APP_ENV={args.app_env})"
    )
    worker = DramaProcessWorker()
    try:
        worker.run()
    except Exception as exc:  # noqa: BLE001
        _log(f"❌ Worker 执行失败: {exc}")
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(f"[process-worker] ❌ 脚本执行失败: {error}", file=sys.stderr)
        sys.exit(1)


