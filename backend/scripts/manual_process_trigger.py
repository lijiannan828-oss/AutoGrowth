#!/usr/bin/env python3
"""Manually trigger drama-processor Cloud Run Job for existing Firestore job IDs."""

from __future__ import annotations

import argparse
import json
from typing import Iterable, List

import google.auth
from google.auth.transport.requests import AuthorizedSession

RUN_API_BASE = "https://run.googleapis.com/v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trigger drama-processor Cloud Run Job for specific Firestore job IDs.",
    )
    parser.add_argument(
        "job_ids",
        nargs="+",
        help="Firestore pipeline_jobs document IDs that should be processed.",
    )
    parser.add_argument(
        "--job-name",
        default="projects/fleet-blend-469520-n7/locations/us-central1/jobs/drama-processor-job",
        help="Fully-qualified Cloud Run Job resource name (projects/.../jobs/...). "
        "Defaults to the production processor job.",
    )
    parser.add_argument(
        "--extra-env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional additional environment variables (besides JOB_ID) to inject.",
    )
    return parser.parse_args()


def parse_env_pairs(pairs: Iterable[str]) -> List[dict]:
    env_list: List[dict] = []
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Invalid env override '{item}', expected KEY=VALUE format")
        key, value = item.split("=", 1)
        env_list.append({"name": key.strip(), "value": value})
    return env_list


def trigger_job(session: AuthorizedSession, job_name: str, job_id: str, extra_env: List[dict]) -> None:
    payload = {
        "overrides": {
            "containerOverrides": [
                {
                    "env": [{"name": "JOB_ID", "value": job_id}, *extra_env],
                }
            ]
        }
    }
    url = f"{RUN_API_BASE}/{job_name}:run"
    response = session.post(url, json=payload, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Failed to trigger job for JOB_ID={job_id}: "
            f"status={response.status_code}, body={response.text}"
        )
    op_name = response.json().get("name", "<unknown>")
    print(f"✅ Triggered {job_name} for JOB_ID={job_id}, operation={op_name}")


def main() -> None:
    args = parse_args()
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    extra_env = parse_env_pairs(args.extra_env)

    for job_id in args.job_ids:
        trigger_job(session, args.job_name, job_id, extra_env)


if __name__ == "__main__":
    main()



