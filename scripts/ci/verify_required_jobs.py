"""Verify GitHub Actions dependency results for required CI rollup jobs."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

_ALLOWED_RESULTS = {"success", "skipped"}


def find_failed_jobs(needs_context: dict[str, Any]) -> list[str]:
    """Return required dependency jobs that did not pass or skip by design."""
    failed: list[str] = []
    for name, data in needs_context.items():
        result = data["result"]
        if result not in _ALLOWED_RESULTS:
            failed.append(f"{name}: {result}")
    return failed


def main() -> int:
    """Validate required dependency jobs from a serialized needs context."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True)
    parser.add_argument("--needs-json", required=True)
    args = parser.parse_args()

    failed = find_failed_jobs(json.loads(args.needs_json))
    if failed:
        print(f"{args.lane} CI dependencies failed:")
        print("\n".join(failed))
        return 1

    print(
        f"All {args.lane.lower()} CI dependencies passed or were skipped by design."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
