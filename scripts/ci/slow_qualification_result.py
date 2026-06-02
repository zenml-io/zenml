"""Derive the slow-CI qualification conclusion from GitHub Actions needs."""

from __future__ import annotations

import argparse
import json
from typing import Any

try:
    from scripts.ci.github_outputs import write_github_outputs
    from scripts.ci.verify_required_jobs import find_failed_jobs
except ModuleNotFoundError:
    from github_outputs import write_github_outputs
    from verify_required_jobs import find_failed_jobs


def qualification_result(
    needs_context: dict[str, Any],
) -> tuple[str, list[str]]:
    """Return the qualification conclusion and failing dependencies."""
    failed_jobs = find_failed_jobs(needs_context)
    conclusion = "failure" if failed_jobs else "success"
    return conclusion, failed_jobs


def _write_github_outputs(conclusion: str, failed_jobs: list[str]) -> None:
    write_github_outputs(
        {
            "conclusion": conclusion,
            "failed_jobs_count": len(failed_jobs),
        }
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--needs-json", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    conclusion, failed_jobs = qualification_result(json.loads(args.needs_json))

    print(f"Slow-CI qualification conclusion: {conclusion}")
    if failed_jobs:
        print("Failed dependencies:")
        print("\n".join(failed_jobs))

    _write_github_outputs(conclusion, failed_jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
