"""Verify GitHub Actions dependency results for required CI rollup jobs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from typing import Any

_ALLOWED_RESULTS = {"success"}


def parse_allowed_skips(values: Iterable[str]) -> set[str]:
    """Parse repeated or comma-separated skipped-job allowlist values."""
    allowed: set[str] = set()
    for value in values:
        allowed.update(
            name.strip() for name in value.split(",") if name.strip()
        )
    return allowed


def find_failed_jobs(
    needs_context: dict[str, Any],
    allowed_skipped_jobs: Iterable[str] = (),
) -> list[str]:
    """Return required dependency jobs that did not pass."""
    failed: list[str] = []
    allowed_skips = set(allowed_skipped_jobs)
    for name, data in needs_context.items():
        result = data["result"]
        if result == "skipped" and name in allowed_skips:
            continue
        if result not in _ALLOWED_RESULTS:
            failed.append(f"{name}: {result}")
    return failed


def main() -> int:
    """Validate required dependency jobs from a serialized needs context."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True)
    parser.add_argument("--needs-json", required=True)
    parser.add_argument(
        "--allow-skipped",
        action="append",
        default=[],
        help="Allow a skipped dependency job by name; repeat or comma-separate.",
    )
    args = parser.parse_args()

    failed = find_failed_jobs(
        json.loads(args.needs_json),
        allowed_skipped_jobs=parse_allowed_skips(args.allow_skipped),
    )
    if failed:
        print(f"{args.lane} CI dependencies failed:")
        print("\n".join(failed))
        return 1

    print(f"All {args.lane.lower()} CI dependencies passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
