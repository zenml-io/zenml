"""Emit lightweight timing metadata for offloaded CI lanes."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _phase_manifest(phases: list[str]) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for phase in phases:
        name, separator, payload = phase.partition("=")
        if not separator:
            continue
        started_raw, _, remainder = payload.partition(",")
        completed_raw, _, status = remainder.partition(",")
        started = _parse_timestamp(started_raw)
        completed = _parse_timestamp(completed_raw)
        manifest[name] = {
            "started_at_unix": started,
            "completed_at_unix": completed,
            "duration_seconds": completed - started
            if started is not None
            and completed is not None
            and completed >= started
            else None,
            "status": status,
        }
    return manifest


def _parse_timestamp(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _file_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at_utc": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat(),
    }


def build_manifest(
    *,
    lane: str,
    output_dir: Path,
    started_at: str | None,
    completed_at: str | None,
    classification: str,
    phases: list[str] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable timing manifest."""
    started = _parse_timestamp(started_at)
    completed = _parse_timestamp(completed_at)
    duration_seconds = (
        completed - started
        if started is not None
        and completed is not None
        and completed >= started
        else None
    )

    return {
        "schema_version": "ci-offload-timing/v1",
        "lane": lane,
        "classification": classification,
        "started_at_unix": started,
        "completed_at_unix": completed,
        "duration_seconds": duration_seconds,
        "phases": _phase_manifest(phases or []),
        "github": {
            "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "job": os.environ.get("GITHUB_JOB", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
            "event_name": os.environ.get("GITHUB_EVENT_NAME", ""),
        },
        "artifacts": {
            "junit_xml": _file_metadata(output_dir / "junit.xml"),
            "coverage_xml": _file_metadata(output_dir / "coverage.xml"),
            "offload_log": _file_metadata(output_dir / "offload.log"),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--started-at")
    parser.add_argument("--completed-at")
    parser.add_argument("--classification", default="unknown")
    parser.add_argument(
        "--phase",
        action="append",
        default=[],
        help="Phase timing as name=start_unix,end_unix,status.",
    )
    return parser


def main() -> None:
    """Run the CLI."""
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        lane=args.lane,
        output_dir=args.output_dir,
        started_at=args.started_at,
        completed_at=args.completed_at,
        classification=args.classification,
        phases=args.phase,
    )
    (args.output_dir / "timing-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
