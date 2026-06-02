#!/usr/bin/env python3
"""Publish slow-CI qualification results to GitHub Checks."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from ci_matrix_hash import compute_matrix_hash
from ci_qualification_ids import format_external_id

CHECK_NAME = "ci-slow-develop/qualification"

TARGET_TITLES = {
    "develop": "develop",
    "pr": "PR ref",
}


def _github_request(url: str, method: str, payload: dict) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _current_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--conclusion", choices=["success", "failure"], required=True
    )
    parser.add_argument("--incident", action="store_true")
    parser.add_argument(
        "--target", choices=sorted(TARGET_TITLES), default="develop"
    )
    args = parser.parse_args()
    if args.incident and args.target != "develop":
        parser.error("--incident can only be used with --target develop")

    repository = os.environ["GITHUB_REPOSITORY"]
    owner, repo = repository.split("/", 1)
    run_id = os.environ["GITHUB_RUN_ID"]
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    completed_at = (
        dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    )
    matrix_hash = compute_matrix_hash(
        Path(".github/workflows/ci-slow-develop.yml")
    )
    sha = _current_sha()
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}"

    target_title = TARGET_TITLES[args.target]
    result_verb = "passed" if args.conclusion == "success" else "failed"
    title = f"Slow CI {result_verb} on {target_title}"
    summary = "\n".join(
        [
            "| Field | Value |",
            "| --- | --- |",
            f"| SHA | `{sha}` |",
            f"| Run | [{run_id}]({run_url}) |",
            f"| Matrix hash | `{matrix_hash}` |",
            f"| Completed at | `{completed_at}` |",
        ]
    )

    _github_request(
        f"https://api.github.com/repos/{owner}/{repo}/check-runs",
        "POST",
        {
            "name": CHECK_NAME,
            "head_sha": sha,
            "status": "completed",
            "conclusion": args.conclusion,
            "completed_at": completed_at,
            "external_id": format_external_id(
                run_id=run_id,
                matrix_hash=matrix_hash,
                completed_at=completed_at,
            ),
            "details_url": run_url,
            "output": {"title": title, "summary": summary},
        },
    )

    if args.incident and args.conclusion == "failure":
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        body = "\n".join(
            [
                f"Nightly slow CI failed on `{sha}`.",
                "",
                f"Workflow run: {run_url}",
                f"Matrix hash: `{matrix_hash}`",
                "",
                (
                    "Please triage failing jobs, identify the suspect PR "
                    "range from the last green qualification, and update "
                    "this issue with the owner and remediation plan."
                ),
            ]
        )
        _github_request(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            "POST",
            {
                "title": f"develop is red — {today} — slow CI failed",
                "body": body,
                "labels": ["develop-red", "incident", "priority/critical"],
            },
        )


if __name__ == "__main__":
    main()
