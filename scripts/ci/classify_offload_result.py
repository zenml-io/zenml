"""Classify Modal offload CI results for workflow status decisions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
from scripts.ci.timing_utils import parse_timestamp  # noqa: E402

FAILED_TESTS_LIMIT = 20

INFRA_PATTERN = re.compile(
    "|".join(
        f"(?:{pattern})"
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
)

INFRA_SIGNAL_PHASES = {
    "setup_python_failed": "modal_prepare",
    "install_rust_failed": "modal_prepare",
    "prepare_failed": "modal_prepare",
    "prepare_marked_modal_infra_failed": "modal_prepare",
    "modal_disabled": "modal_prepare",
    "provision_failed": "server_provision",
    "infra_log_pattern": "sandbox_create",
}


@dataclass(frozen=True)
class Classification:
    """Workflow outputs derived from one Modal offload run."""

    modal_infra_failed: bool
    test_failed: bool
    harness_failed: bool
    junit_cache_safe: bool
    classification: Literal["success", "modal_infra_failure", "test_failure"]
    reason: str
    diagnostic: str
    failed_phase: str = "none"
    failed_tests: tuple[str, ...] = ()


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


def _validate_junit(
    junit_file: Path, run_started_at: str | None
) -> JUnitValidation:
    run_started_ts = parse_timestamp(run_started_at)
    if run_started_ts is None:
        return JUnitValidation(
            False, None, reason="run start timestamp is missing or invalid"
        )

    try:
        stat = junit_file.stat()
    except FileNotFoundError:
        return JUnitValidation(
            False, None, reason=f"JUnit XML not found: {junit_file}"
        )
    except OSError as exc:
        return JUnitValidation(
            False, None, reason=f"Could not stat JUnit XML {junit_file}: {exc}"
        )

    if stat.st_size <= 0:
        return JUnitValidation(
            False, None, reason=f"JUnit XML is empty: {junit_file}"
        )
    if stat.st_mtime < run_started_ts:
        return JUnitValidation(
            False, None, reason=f"JUnit XML is stale: {junit_file}"
        )

    try:
        root, summary = parse_junit_summary(junit_file)
    except ET.ParseError as exc:
        return JUnitValidation(
            False,
            None,
            reason=f"JUnit XML is not parseable XML: {junit_file}: {exc}",
        )
    except OSError as exc:
        return JUnitValidation(
            False, None, reason=f"Could not read JUnit XML {junit_file}: {exc}"
        )

    if root.tag not in {"testsuite", "testsuites"}:
        return JUnitValidation(
            False,
            None,
            reason=(
                f"JUnit XML has unexpected root tag '{root.tag}' in "
                f"{junit_file}; expected testsuite, testsuites"
            ),
        )

    return JUnitValidation(True, summary, root=root)


def _log_matches_infra_pattern(offload_log: Path) -> bool:
    try:
        with offload_log.open(encoding="utf-8", errors="replace") as log_file:
            return any(INFRA_PATTERN.search(line) for line in log_file)
    except OSError:
        return False


def _single_line(value: str) -> str:
    """Collapse diagnostics so they are safe for GitHub output files."""
    return " ".join(value.split())


def _infra_signals(
    *,
    setup_python_outcome: str | None,
    install_rust_outcome: str | None,
    prepare_outcome: str | None,
    prepare_modal_infra_failed: str | None,
    run_modal_enabled: str | None,
    provision_outcome: str | None,
) -> list[str]:
    """Return stable reason slugs for explicit infrastructure signals."""
    signals: list[str] = []
    if _is_failure_outcome(setup_python_outcome):
        signals.append("setup_python_failed")
    if _is_failure_outcome(install_rust_outcome):
        signals.append("install_rust_failed")
    if prepare_outcome == "failure":
        signals.append("prepare_failed")
    if _is_true(prepare_modal_infra_failed):
        signals.append("prepare_marked_modal_infra_failed")
    if run_modal_enabled == "false":
        signals.append("modal_disabled")
    if provision_outcome == "failure":
        signals.append("provision_failed")
    return signals


def _failed_test_names(
    root: ET.Element | None, limit: int = FAILED_TESTS_LIMIT
) -> tuple[str, ...]:
    """Return capped JUnit testcase identifiers that failed or errored."""
    if root is None:
        return ()

    failed_tests: list[str] = []
    for testcase in root.iter("testcase"):
        if testcase.find("failure") is None and testcase.find("error") is None:
            continue
        classname = testcase.get("classname", "").strip()
        name = testcase.get("name", "").strip()
        identifier = "::".join(part for part in (classname, name) if part)
        failed_tests.append(identifier or "<unknown>")
        if len(failed_tests) >= limit:
            break
    return tuple(failed_tests)


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
            f"harness_failed={str(classification.harness_failed).lower()}\n"
        )
        output_file.write(
            f"junit_cache_safe={str(classification.junit_cache_safe).lower()}\n"
        )
        output_file.write(f"classification={classification.classification}\n")
        output_file.write(f"reason={classification.reason}\n")
        output_file.write(f"failed_phase={classification.failed_phase}\n")
        output_file.write(
            f"failed_tests={json.dumps(list(classification.failed_tests))}\n"
        )
        output_file.write(
            f"diagnostic={_single_line(classification.diagnostic)}\n"
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
    infra_signals = _infra_signals(
        setup_python_outcome=setup_python_outcome,
        install_rust_outcome=install_rust_outcome,
        prepare_outcome=prepare_outcome,
        prepare_modal_infra_failed=prepare_modal_infra_failed,
        run_modal_enabled=run_modal_enabled,
        provision_outcome=provision_outcome,
    )

    junit = _validate_junit(junit_file, run_started_at)
    if junit.reason:
        print(f"{lane}: {junit.reason}")
    elif junit.fresh and junit.root is not None and junit.summary is not None:
        print_parsed_summary(junit.root, junit.summary)

    if not junit.fresh and _log_matches_infra_pattern(offload_log):
        infra_signals.append("infra_log_pattern")

    if infra_signals and not junit.fresh:
        annotation = _infra_annotation_command(infra_policy)
        reason = infra_signals[0]
        diagnostic = _single_line(
            f"{lane}: Modal infrastructure signal '{reason}' with "
            f"unusable JUnit: {junit.reason or 'JUnit XML is missing'}"
        )
        print(
            f"::{annotation}::{lane}: classified as Modal infrastructure "
            f"failure ({reason})"
        )
        return Classification(
            modal_infra_failed=True,
            test_failed=False,
            harness_failed=True,
            junit_cache_safe=False,
            classification="modal_infra_failure",
            reason=reason,
            diagnostic=diagnostic,
            failed_phase=INFRA_SIGNAL_PHASES.get(reason, "harness_failure"),
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
    harness_failed = False
    failed_phase = "none"
    failed_tests: tuple[str, ...] = ()
    reason = "none"
    diagnostic = f"{lane}: offload completed with passing JUnit results"
    if not junit.fresh:
        test_failed = True
        harness_failed = True
        failed_phase = "junit_invalid"
        reason = "junit_not_fresh"
        diagnostic = f"{lane}: {junit.reason or 'JUnit XML is missing'}"
    elif has_junit_failures:
        test_failed = True
        failed_phase = "test_execution"
        failed_tests = _failed_test_names(junit.root)
        reason = "junit_failures"
        assert junit.summary is not None
        diagnostic = (
            f"{lane}: JUnit reported {junit.summary.failures} failures "
            f"and {junit.summary.errors} errors"
        )
    elif not success_like_exit:
        test_failed = True
        harness_failed = True
        failed_phase = "harness_failure"
        reason = "offload_exit_code"
        diagnostic = (
            f"{lane}: offload exited {parsed_exit_code} but JUnit XML "
            "contains no failures or errors"
        )
        print(f"::error::{diagnostic}")

    junit_cache_safe = bool(
        junit.fresh and success_like_exit and not has_junit_failures
    )
    return Classification(
        modal_infra_failed=False,
        test_failed=test_failed,
        harness_failed=harness_failed,
        junit_cache_safe=junit_cache_safe,
        classification="test_failure" if test_failed else "success",
        reason=reason,
        diagnostic=_single_line(diagnostic),
        failed_phase=failed_phase,
        failed_tests=failed_tests,
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
        f"harness_failed={classification.harness_failed} "
        f"junit_cache_safe={classification.junit_cache_safe} "
        f"classification={classification.classification} "
        f"reason={classification.reason} "
        f"failed_phase={classification.failed_phase} "
        f"failed_tests={list(classification.failed_tests)} "
        f"diagnostic={classification.diagnostic}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
