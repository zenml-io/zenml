"""Classify offloaded CI results for workflow fallback decisions."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ci.github_outputs import write_github_outputs
    from scripts.ci.print_junit_summary import (
        JUnitSummary,
        parse_junit_summary,
        print_parsed_summary,
    )
except ModuleNotFoundError:
    from github_outputs import write_github_outputs
    from print_junit_summary import (  # type: ignore[no-redef]
        JUnitSummary,
        parse_junit_summary,
        print_parsed_summary,
    )

INFRA_PATTERN = re.compile(
    r"(modal|sandbox|offload|rate.?limit|timeout|connection|network|"
    r"image build|no space left|permission denied|authentication|credentials)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Classification:
    """Normalized offload lane classification."""

    conclusion: str
    offload_infra_failed: bool
    tests_failed: bool
    message: str
    junit_current: bool
    junit_cacheable: bool


def _is_true(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _read_junit_summary(junit_path: Path) -> JUnitSummary:
    summary = parse_junit_summary(junit_path)
    print_parsed_summary(summary)
    return summary


def _infra_failure(
    message: str, *, junit_current: bool = False
) -> Classification:
    return Classification(
        conclusion="infra_failure",
        offload_infra_failed=True,
        tests_failed=False,
        message=message,
        junit_current=junit_current,
        junit_cacheable=False,
    )


def _read_log(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def classify_offload_result(
    *,
    exit_code: int,
    junit_path: Path,
    log_path: Path | None = None,
    setup_failed: bool = False,
    junit_min_mtime_ns: int | None = None,
) -> Classification:
    """Classify offload output as success, test failure, or infrastructure failure."""
    if setup_failed:
        return _infra_failure("Offload setup failed before tests ran.")

    junit_exists = junit_path.exists()
    if junit_exists and junit_min_mtime_ns is not None:
        if junit_path.stat().st_mtime_ns <= junit_min_mtime_ns:
            junit_exists = False
            stale_message = (
                "Offload did not produce current JUnit XML; existing JUnit "
                "file is a restored duration seed or stale artifact."
            )
            return _infra_failure(stale_message)

    if junit_exists:
        try:
            summary = _read_junit_summary(junit_path)
            if summary.failed:
                return Classification(
                    conclusion="test_failure",
                    offload_infra_failed=False,
                    tests_failed=True,
                    message="Offloaded tests reported JUnit failures/errors.",
                    junit_current=True,
                    junit_cacheable=True,
                )
        except (ET.ParseError, ValueError) as exc:
            return _infra_failure(
                f"Offload produced invalid JUnit XML: {exc}",
                junit_current=True,
            )

        if exit_code in {0, 2}:
            if summary.tests == 0:
                return _infra_failure(
                    "Offload produced a JUnit report with zero tests "
                    "collected; treating as infrastructure failure rather "
                    "than success.",
                    junit_current=True,
                )
            message = "Offloaded tests passed."
            if exit_code == 2:
                message = "Offload reported flaky tests that passed on retry."
            return Classification(
                conclusion="success",
                offload_infra_failed=False,
                tests_failed=False,
                message=message,
                junit_current=True,
                junit_cacheable=True,
            )

        return _infra_failure(
            "Offload exited non-zero despite a passing JUnit report.",
            junit_current=True,
        )

    if exit_code == 0:
        return _infra_failure(
            "Offload exited successfully but did not produce JUnit XML."
        )

    log_text = _read_log(log_path)
    if INFRA_PATTERN.search(log_text):
        message = "Offload failed before producing JUnit XML; log matches infrastructure patterns."
    else:
        message = "Offload failed before producing JUnit XML."
    return _infra_failure(message)


def _write_github_outputs(classification: Classification) -> None:
    write_github_outputs(
        {
            "conclusion": classification.conclusion,
            "offload_infra_failed": str(
                classification.offload_infra_failed
            ).lower(),
            "tests_failed": str(classification.tests_failed).lower(),
            "junit_current": str(classification.junit_current).lower(),
            "junit_cacheable": str(classification.junit_cacheable).lower(),
        }
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--setup-failed", default="false")
    parser.add_argument("--junit-min-mtime-ns", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = _build_parser().parse_args(argv)
    classification = classify_offload_result(
        exit_code=args.exit_code,
        junit_path=args.junit,
        log_path=args.log,
        setup_failed=_is_true(args.setup_failed),
        junit_min_mtime_ns=args.junit_min_mtime_ns,
    )
    print(classification.message)
    _write_github_outputs(classification)
    return 0


if __name__ == "__main__":
    sys.exit(main())
