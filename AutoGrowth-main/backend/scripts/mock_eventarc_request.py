#!/usr/bin/env python3
"""Send a mock CloudEvents payload to the relay endpoint for local testing."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import requests


def build_payload(drama_name: str, bucket: str, sub_path: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    object_name = f"{drama_name}/{sub_path.strip('/')}/_PROCESS_NOW.txt"
    return {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": f"//storage.googleapis.com/projects/_/buckets/{bucket}",
        "id": f"mock-{drama_name}-{int(datetime.now().timestamp())}",
        "time": now,
        "subject": f"objects/{object_name}",
        "data": {
            "bucket": bucket,
            "name": object_name,
            "metageneration": "1",
            "timeCreated": now,
            "updated": now,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger relay endpoint locally.")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/api/v1/relay/event",
        help="Relay endpoint URL",
    )
    parser.add_argument("--drama", required=True, help="Program/Drama directory name")
    parser.add_argument("--bucket", default="vigloo_source", help="GCS bucket name")
    parser.add_argument(
        "--sub-path",
        default="Episodes",
        help="Sub path leading to the signal file (default: Episodes)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print response JSON",
    )
    args = parser.parse_args()

    payload = build_payload(args.drama, args.bucket, args.sub_path)

    response = requests.post(args.endpoint, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
    except json.JSONDecodeError:
        print(response.text)
        return

    if args.pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)


if __name__ == "__main__":
    main()

