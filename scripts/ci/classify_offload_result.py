"""Classify Modal offload CI results for workflow status decisions."""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.ci.print_junit_summary import (  # noqa: E402
    JUnitSummary,
    parse_junit_summary,
    print_parsed_summary,
)

INFRA_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"Failed to prepare Default provider",
        r"Default prepare command failed",
        r"failed to run builder command",
        r"modal\.exception\.RemoteError",
        r"Image build .* failed",
        r"Failed to create sandboxes",
        r"Failed to execute command: Create command failed",
        r"Failed to spawn: .*modal_sandbox",
        r"Failed to discover tests",
        r"pytest --collect-only failed",
        r"No module named pytest",
        r"error: unexpected argument",
    )
)


@dataclass(frozen=True)
class Classification:
    """Workflow outputs derived from one Modal offload run."""

    modal_infra_failed: bool
    test_failed: bool
    junit_cache_safe: bool


@dataclass(frozen=True)
class JUnitValidation:
    """Freshness and parse result for a JUnit artifact."""

    fresh: bool
    summary: JUnitSummary | None
    root: ET.Element | None = None
    reason: str | None = None


def _is_failure_outcome(outcome: str | None) -> bool:
    return bool(outcome) and outcome != "success"


def _is_true(value: str | None) -> bool:
    return (value or "").lower() == "true"


def _parse_timestamp(value: str | None) -> float | None:
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        pass

    normalized = value.strip().replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.timestamp()


def _validate_junit(
    junit_file: Path, run_started_at: str | None
) -> JUnitValidation:
    run_started_ts = _parse_timestamp(run_started_at)
    if run_started_ts is None:
        return JUnitValidation(
            False, None, reason="run start timestamp is missing or invalid"
        )

    if not junit_file.exists():
        return JUnitValidation(
            False, None, reason=f"JUnit XML not found: {junit_file}"
        )

    try:
        stat = junit_file.stat()
    except OSError as exc:
        return JUnitValidation(
            False, None, reason=f"Could not stat JUnit XML {junit_file}: {exc}"
        )

    if stat.st_size == 0:
        return JUnitValidation(
            False, None, reason=f"JUnit XML is empty: {junit_file}"
        )

    if stat.st_mtime < run_started_ts:
        return JUnitValidation(
            False, None, reason=f"JUnit XML is stale: {junit_file}"
        )

    try:
        root, summary = parse_junit_summary(junit_file)
    except (OSError, ET.ParseError) as exc:
        return JUnitValidation(
            False,
            None,
            reason=f"JUnit XML is not parseable: {junit_file}: {exc}",
        )

    if root.tag not in {"testsuite", "testsuites"}:
        return JUnitValidation(
            False,
            None,
            reason=f"JUnit XML has unexpected root tag '{root.tag}': {junit_file}",
        )

    return JUnitValidation(True, summary, root=root)


def _log_matches_infra_pattern(offload_log: Path) -> bool:
    try:
        text = offload_log.read_text(errors="replace")
    except OSError:
        return False

    return any(pattern.search(text) for pattern in INFRA_PATTERNS)


def _infra_annotation_command(
    infra_policy: Literal["fallback", "fail"],
) -> Literal["warning", "error"]:
    return "warning" if infra_policy == "fallback" else "error"


def _write_github_outputs(classification: Classification) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return

    with Path(output_path).open("a") as output_file:
        output_file.write(
            f"modal_infra_failed={str(classification.modal_infra_failed).lower()}\n"
        )
        output_file.write(
            f"test_failed={str(classification.test_failed).lower()}\n"
        )
        output_file.write(
            f"junit_cache_safe={str(classification.junit_cache_safe).lower()}\n"
        )


def classify_offload_result(
    *,
    lane: str,
    infra_policy: Literal["fallback", "fail"],
    junit_file: Path,
    offload_log: Path,
    exit_code: str | None,
    run_started_at: str | None,
    setup_python_outcome: str | None = None,
    install_rust_outcome: str | None = None,
    prepare_outcome: str | None = None,
    prepare_modal_infra_failed: str | None = None,
    run_modal_enabled: str | None = None,
    provision_outcome: str | None = None,
) -> Classification:
    """Classify an offload run without deciding final workflow exit status."""
    infra_failed = any(
        (
            _is_failure_outcome(setup_python_outcome),
            _is_failure_outcome(install_rust_outcome),
            prepare_outcome == "failure",
            _is_true(prepare_modal_infra_failed),
            run_modal_enabled == "false",
            provision_outcome == "failure",
        )
    )

    junit = _validate_junit(junit_file, run_started_at)
    if junit.reason:
        print(f"{lane}: {junit.reason}")
    elif junit.fresh and junit.root is not None and junit.summary is not None:
        print_parsed_summary(junit.root, junit.summary)

    if not junit.fresh and _log_matches_infra_pattern(offload_log):
        infra_failed = True

    if infra_failed and not junit.fresh:
        annotation = _infra_annotation_command(infra_policy)
        print(
            f"::{annotation}::{lane}: classified as Modal infrastructure failure"
        )
        return Classification(
            modal_infra_failed=True,
            test_failed=False,
            junit_cache_safe=False,
        )

    try:
        parsed_exit_code = int(exit_code or "")
    except ValueError:
        parsed_exit_code = -1

    has_junit_failures = bool(
        junit.summary and (junit.summary.failures or junit.summary.errors)
    )

    if parsed_exit_code == 2 and junit.fresh and not has_junit_failures:
        print(f"::notice::{lane}: offload exited 2 but JUnit results passed")

    success_like_exit = parsed_exit_code in {0, 2}
    test_failed = False
    if not junit.fresh:
        test_failed = True
    elif has_junit_failures:
        test_failed = True
    elif not success_like_exit:
        test_failed = True
        print(
            f"::error::{lane}: offload exited {parsed_exit_code} "
            "but JUnit XML contains no failures or errors"
        )

    junit_cache_safe = bool(
        junit.fresh and success_like_exit and not has_junit_failures
    )
    return Classification(
        modal_infra_failed=infra_failed,
        test_failed=test_failed,
        junit_cache_safe=junit_cache_safe,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument(
        "--infra-policy", choices=("fallback", "fail"), required=True
    )
    parser.add_argument("--junit-file", type=Path, required=True)
    parser.add_argument("--offload-log", type=Path, required=True)
    parser.add_argument("--exit-code")
    parser.add_argument("--run-started-at")
    parser.add_argument("--setup-python-outcome")
    parser.add_argument("--install-rust-outcome")
    parser.add_argument("--prepare-outcome")
    parser.add_argument("--prepare-modal-infra-failed")
    parser.add_argument("--run-modal-enabled")
    parser.add_argument("--provision-outcome")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Classify a Modal offload result and write GitHub outputs."""
    args = _build_parser().parse_args(argv)
    classification = classify_offload_result(
        lane=args.lane,
        infra_policy=args.infra_policy,
        junit_file=args.junit_file,
        offload_log=args.offload_log,
        exit_code=args.exit_code,
        run_started_at=args.run_started_at,
        setup_python_outcome=args.setup_python_outcome,
        install_rust_outcome=args.install_rust_outcome,
        prepare_outcome=args.prepare_outcome,
        prepare_modal_infra_failed=args.prepare_modal_infra_failed,
        run_modal_enabled=args.run_modal_enabled,
        provision_outcome=args.provision_outcome,
    )
    _write_github_outputs(classification)
    print(
        "Classification: "
        f"modal_infra_failed={classification.modal_infra_failed} "
        f"test_failed={classification.test_failed} "
        f"junit_cache_safe={classification.junit_cache_safe}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
