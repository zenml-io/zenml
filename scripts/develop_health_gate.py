#!/usr/bin/env python3
"""Evaluate whether the merge queue can proceed while develop is healthy."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ci_matrix_hash import compute_matrix_hash

CHECK_NAME = "ci-slow-develop/qualification"
DEFAULT_MAX_AGE_HOURS = 30
DEFAULT_GRACE_AFTER_SCHEDULE_HOURS = 6
DEVELOP_BRANCH = "develop"
FIX_DEVELOP_LABEL = "fix-develop"


def _github_request(
    path: str, query: dict[str, str] | None = None
) -> dict[str, Any]:
    """Send an authenticated GitHub API request."""
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    query_string = urllib.parse.urlencode(query or {})
    suffix = f"?{query_string}" if query_string else ""
    url = f"https://api.github.com/repos/{repository}{path}{suffix}"
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


def _parse_datetime(value: str) -> dt.datetime:
    """Parse a GitHub timestamp."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _current_develop_sha() -> str:
    """Return the current develop branch SHA."""
    branch = _github_request(f"/branches/{DEVELOP_BRANCH}")
    return str(branch["commit"]["sha"])


def _commit_datetime(sha: str) -> dt.datetime:
    """Return the commit timestamp for a SHA."""
    commit = _github_request(f"/commits/{sha}")
    return _parse_datetime(str(commit["commit"]["committer"]["date"]))


def _qualification_check_runs(sha: str) -> list[dict[str, Any]]:
    """Return qualification Check Runs for a SHA, newest first."""
    payload = _github_request(
        f"/commits/{sha}/check-runs",
        {"check_name": CHECK_NAME, "status": "completed"},
    )
    check_runs = list(payload.get("check_runs", []))
    return sorted(
        check_runs,
        key=lambda item: item.get("completed_at") or "",
        reverse=True,
    )


def _extract_pr_numbers_from_event() -> set[int]:
    """Extract PR numbers from the current GitHub event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return set()

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    numbers: set[int] = set()

    for pr in event.get("pull_requests", []) or []:
        if number := pr.get("number"):
            numbers.add(int(number))

    merge_group = event.get("merge_group") or {}
    for candidate in [merge_group.get("head_ref"), merge_group.get("ref")]:
        if not candidate:
            continue
        match = re.search(r"/pr-(\d+)-", str(candidate))
        if match:
            numbers.add(int(match.group(1)))

    return numbers


def _labels_for_pr(number: int) -> set[str]:
    """Return labels for a PR number."""
    payload = _github_request(f"/issues/{number}/labels", {"per_page": "100"})
    return {str(label["name"]) for label in payload}


def _merge_group_labels() -> set[str]:
    """Return labels for PRs represented by the merge-group event."""
    labels: set[str] = set()
    for number in _extract_pr_numbers_from_event():
        labels.update(_labels_for_pr(number))
    return labels


def _latest_nightly_schedule(now: dt.datetime) -> dt.datetime:
    """Return the latest expected nightly slow-CI schedule time."""
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _external_id_parts(
    check_run: dict[str, Any],
) -> tuple[str, str, dt.datetime]:
    """Parse the qualification Check Run external ID."""
    external_id = str(check_run.get("external_id") or "")
    try:
        run_id, matrix_hash, completed_at = external_id.split(":", 2)
    except ValueError as exc:
        raise RuntimeError(
            f"Qualification Check Run has invalid external_id: {external_id!r}"
        ) from exc
    return run_id, matrix_hash, _parse_datetime(completed_at)


def _pass(message: str) -> None:
    """Pass the gate with a message."""
    print(message)


def _fail(message: str) -> None:
    """Fail the gate with a message."""
    print(f"::error::{message}")
    sys.exit(1)


def main() -> None:
    """Run the health gate."""
    max_age_hours = int(os.environ.get("MAX_AGE_HOURS", DEFAULT_MAX_AGE_HOURS))
    grace_hours = int(
        os.environ.get(
            "GRACE_AFTER_SCHEDULE_HOURS", DEFAULT_GRACE_AFTER_SCHEDULE_HOURS
        )
    )
    now = dt.datetime.now(dt.timezone.utc)
    develop_sha = _current_develop_sha()
    expected_matrix_hash = compute_matrix_hash(
        Path(".github/workflows/ci-slow-develop.yml")
    )
    check_runs = _qualification_check_runs(develop_sha)

    if not check_runs:
        latest_schedule = _latest_nightly_schedule(now)
        develop_commit_time = _commit_datetime(develop_sha)
        if develop_commit_time > latest_schedule:
            _pass(
                "No develop qualification exists yet, but develop HEAD is "
                "newer than the latest nightly schedule. Passing under grace."
            )
            return
        if now <= latest_schedule + dt.timedelta(hours=grace_hours):
            _pass(
                "No develop qualification exists yet, but the nightly grace "
                "window is still open. Passing under grace."
            )
            return
        _fail(
            f"No {CHECK_NAME} Check Run exists on develop SHA {develop_sha}."
        )

    latest = check_runs[0]
    conclusion = latest.get("conclusion")
    if conclusion == "failure":
        labels = _merge_group_labels()
        if FIX_DEVELOP_LABEL in labels:
            _pass("Develop is red, but this PR carries fix-develop.")
            return
        _fail(
            "Develop is red. Add fix-develop only to the PR that repairs "
            "the failing develop state."
        )

    if conclusion != "success":
        _fail(f"Latest {CHECK_NAME} conclusion is {conclusion!r}.")

    run_id, matrix_hash, completed_at = _external_id_parts(latest)
    if matrix_hash != expected_matrix_hash:
        _fail(
            "Slow-CI matrix hash changed since the latest develop "
            f"qualification. qualification={matrix_hash}, "
            f"current={expected_matrix_hash}"
        )

    age_hours = (now - completed_at).total_seconds() / 3600
    if age_hours > max_age_hours:
        _fail(
            f"Develop qualification is stale ({age_hours:.1f}h old). "
            "Trigger ci-slow-develop manually."
        )

    _pass(
        f"Develop qualification OK: sha={develop_sha}, run={run_id}, "
        f"age={age_hours:.1f}h."
    )


if __name__ == "__main__":
    main()
