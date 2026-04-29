"""Emit timing and classification manifests for Modal CI lanes."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.ci.print_junit_summary import parse_junit_summary  # noqa: E402
from scripts.ci.timing_utils import (  # noqa: E402
    parse_timestamp,
    timestamp_to_iso,
)

FAILED_TESTS_LIMIT = 20
GITHUB_ENV_KEYS = {
    "workflow": "GITHUB_WORKFLOW",
    "job": "GITHUB_JOB",
    "run_attempt": "GITHUB_RUN_ATTEMPT",
    "ref": "GITHUB_REF",
    "event_name": "GITHUB_EVENT_NAME",
}


def _file_manifest(path: Path) -> dict[str, Any]:
    """Return lightweight metadata for an artifact path."""
    try:
        stat = path.stat()
    except OSError:
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": None,
            "mtime": None,
        }

    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime": timestamp_to_iso(stat.st_mtime),
    }


def _parse_bool(value: str | None) -> bool | None:
    """Parse optional GitHub-output booleans."""
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return None


def _parse_failed_tests(value: str | None) -> list[str]:
    """Parse capped failed tests from classifier output."""
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [part.strip() for part in value.split(",") if part.strip()]

    if not isinstance(parsed, list):
        return []

    return [str(item) for item in parsed[:FAILED_TESTS_LIMIT]]


def _parse_phase(value: str) -> tuple[str, dict[str, Any], list[str]]:
    """Parse one --phase value into manifest-ready phase data."""
    if "=" not in value:
        raise ValueError(
            "phase must use NAME=STARTED_AT,ENDED_AT,OUTCOME format"
        )

    name, payload = value.split("=", maxsplit=1)
    name = name.strip()
    parts = [part.strip() for part in payload.split(",")]
    if not name or len(parts) != 3:
        raise ValueError(
            "phase must use NAME=STARTED_AT,ENDED_AT,OUTCOME format"
        )

    started_ts = parse_timestamp(parts[0])
    ended_ts = parse_timestamp(parts[1])
    outcome = parts[2] or None
    warnings: list[str] = []
    if started_ts is None:
        warnings.append(f"phase '{name}' is missing a valid start timestamp")
    if ended_ts is None:
        warnings.append(f"phase '{name}' is missing a valid end timestamp")

    duration_s = None
    if started_ts is not None and ended_ts is not None:
        duration_s = max(0.0, ended_ts - started_ts)

    return (
        name,
        {
            "started_at": timestamp_to_iso(started_ts),
            "ended_at": timestamp_to_iso(ended_ts),
            "duration_s": duration_s,
            "outcome": outcome,
        },
        warnings,
    )


def _read_junit_tests(
    junit_file: Path, failed_tests: list[str]
) -> dict[str, Any]:
    """Return JUnit-derived test counts when the artifact is available."""
    result: dict[str, Any] = {
        "junit": _file_manifest(junit_file),
        "total": None,
        "passed": None,
        "failures": None,
        "errors": None,
        "skipped": None,
        "time_s": None,
        "failed_tests": failed_tests,
    }
    try:
        root, summary = parse_junit_summary(junit_file)
    except (OSError, ET.ParseError):
        return result

    result.update(
        {
            "total": summary.tests,
            "passed": summary.passed,
            "failures": summary.failures,
            "errors": summary.errors,
            "skipped": summary.skipped,
            "time_s": summary.time_s,
        }
    )
    if not failed_tests:
        result["failed_tests"] = _collect_failed_tests(root)
    return result


def _collect_failed_tests(root: ET.Element) -> list[str]:
    """Collect capped failed/errored testcase identifiers from JUnit XML."""
    failed_tests: list[str] = []
    for testcase in root.iter("testcase"):
        if testcase.find("failure") is None and testcase.find("error") is None:
            continue
        classname = testcase.get("classname", "").strip()
        name = testcase.get("name", "").strip()
        failed_tests.append(
            "::".join(part for part in (classname, name) if part)
            or "<unknown>"
        )
        if len(failed_tests) >= FAILED_TESTS_LIMIT:
            break
    return failed_tests


def _read_batch_summary(offload_log: Path) -> dict[str, Any]:
    """Return lightweight offload batch counts when logs are available."""
    result: dict[str, Any] = {
        "offload_log": _file_manifest(offload_log),
        "started": None,
        "completed": None,
        "failed": None,
    }
    try:
        log_text = offload_log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result

    result.update(
        {
            "started": len(re.findall(r"\[BATCH START\]", log_text)),
            "completed": len(re.findall(r"\[BATCH COMPLETE", log_text)),
            "failed": len(re.findall(r"\[BATCH FAILED", log_text)),
        }
    )
    return result


def build_manifest(
    *,
    lane: str,
    output_dir: Path,
    junit_file: Path,
    offload_log: Path,
    classification: str,
    classification_reason: str,
    classification_diagnostic: str,
    failed_phase: str | None,
    failed_tests: str | None,
    modal_infra_failed: str | None,
    test_failed: str | None,
    harness_failed: str | None,
    junit_cache_safe: str | None,
    phases: list[str],
) -> dict[str, Any]:
    """Build a Modal lane timing manifest."""
    phase_details: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    started_values: list[float] = []
    ended_values: list[float] = []
    for phase in phases:
        phase_name, phase_detail, phase_warnings = _parse_phase(phase)
        phase_details[phase_name] = phase_detail
        warnings.extend(phase_warnings)

        started_ts = parse_timestamp(phase_detail["started_at"])
        ended_ts = parse_timestamp(phase_detail["ended_at"])
        if started_ts is not None:
            started_values.append(started_ts)
        if ended_ts is not None:
            ended_values.append(ended_ts)

    started_at_ts = min(started_values) if started_values else None
    ended_at_ts = max(ended_values) if ended_values else None
    total_duration_s = None
    if started_at_ts is not None and ended_at_ts is not None:
        total_duration_s = max(0.0, ended_at_ts - started_at_ts)

    parsed_failed_tests = _parse_failed_tests(failed_tests)
    tests = _read_junit_tests(junit_file, parsed_failed_tests)
    manifest_failed_tests = parsed_failed_tests or tests["failed_tests"]
    result = classification
    return {
        "schema_version": 1,
        "lane": lane,
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "sha": os.getenv("GITHUB_SHA"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": timestamp_to_iso(started_at_ts),
        "ended_at": timestamp_to_iso(ended_at_ts),
        "total_duration_s": total_duration_s,
        "phases": {
            f"{name}_s": detail["duration_s"]
            for name, detail in phase_details.items()
        },
        "phase_details": phase_details,
        "cache": {
            "junit_cache_safe": _parse_bool(junit_cache_safe),
            "junit_file": _file_manifest(junit_file),
        },
        "tests": tests,
        "batches": _read_batch_summary(offload_log),
        "classification": {
            "result": result,
            "kind": classification,
            "reason": classification_reason,
            "diagnostic": classification_diagnostic,
            "failed_phase": failed_phase or "none",
            "modal_infra_failed": _parse_bool(modal_infra_failed),
            "test_failed": _parse_bool(test_failed),
            "harness_failed": _parse_bool(harness_failed),
            "junit_cache_safe": _parse_bool(junit_cache_safe),
            "failed_tests": manifest_failed_tests,
        },
        "github": {
            key: os.getenv(env_key) for key, env_key in GITHUB_ENV_KEYS.items()
        },
        "warnings": warnings,
        "output_dir": str(output_dir),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--junit-file", type=Path, required=True)
    parser.add_argument("--offload-log", type=Path, required=True)
    parser.add_argument("--classification", default="unknown")
    parser.add_argument("--classification-reason", default="unknown")
    parser.add_argument("--classification-diagnostic", default="")
    parser.add_argument("--failed-phase")
    parser.add_argument("--failed-tests")
    parser.add_argument("--modal-infra-failed")
    parser.add_argument("--test-failed")
    parser.add_argument("--harness-failed")
    parser.add_argument("--junit-cache-safe")
    parser.add_argument(
        "--phase",
        action="append",
        default=[],
        help="Phase timing in NAME=STARTED_AT,ENDED_AT,OUTCOME format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Write the timing manifest and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(
            lane=args.lane,
            output_dir=args.output_dir,
            junit_file=args.junit_file,
            offload_log=args.offload_log,
            classification=args.classification,
            classification_reason=args.classification_reason,
            classification_diagnostic=args.classification_diagnostic,
            failed_phase=args.failed_phase,
            failed_tests=args.failed_tests,
            modal_infra_failed=args.modal_infra_failed,
            test_failed=args.test_failed,
            harness_failed=args.harness_failed,
            junit_cache_safe=args.junit_cache_safe,
            phases=args.phase,
        )
    except ValueError as exc:
        parser.error(str(exc))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"Wrote timing manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
