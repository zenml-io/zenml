#!/usr/bin/env python3
"""Verify a release tag has a recent slow-CI qualification Check Run."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ci_matrix_hash import compute_matrix_hash

CHECK_NAME = "ci-slow-develop/qualification"


def _github_request(url: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _tagged_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD^{commit}"], text=True
    ).strip()


def _verify(repository: str, sha: str, max_age_hours: int) -> str:
    owner, repo = repository.split("/", 1)
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
        f"/check-runs?check_name={CHECK_NAME}&status=completed"
    )
    payload = _github_request(url)
    expected_hash = compute_matrix_hash(
        Path(".github/workflows/ci-slow-develop.yml")
    )

    for check_run in payload.get("check_runs", []):
        if check_run.get("conclusion") != "success":
            continue
        external_id = check_run.get("external_id") or ""
        try:
            run_id, matrix_hash, completed_at = external_id.split(":", 2)
        except ValueError:
            continue
        if matrix_hash != expected_hash:
            raise RuntimeError(
                "Matrix hash mismatch: "
                f"qualification={matrix_hash}, current={expected_hash}"
            )
        completed = dt.datetime.fromisoformat(
            completed_at.replace("Z", "+00:00")
        )
        age_hours = (
            dt.datetime.now(dt.timezone.utc) - completed
        ).total_seconds() / 3600
        if age_hours > max_age_hours:
            raise RuntimeError(
                f"Qualification too stale ({age_hours:.1f}h old)"
            )
        return f"Qualification OK: run {run_id}, {age_hours:.1f}h old"

    raise RuntimeError(f"No green {CHECK_NAME} Check Run found on {sha}")


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-age-hours", type=int, default=168)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    try:
        repository = os.environ["GITHUB_REPOSITORY"]
        message = _verify(repository, _tagged_sha(), args.max_age_hours)
        print(message)
    except Exception as exc:
        if args.warn_only:
            print(f"::warning::{exc}")
            return
        print(f"::error::{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
