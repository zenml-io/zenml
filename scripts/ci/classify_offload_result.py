"""Classify offloaded CI results for workflow fallback decisions."""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ci.print_junit_summary import (
        parse_junit_summary,
        print_parsed_summary,
    )
except ModuleNotFoundError:
    from print_junit_summary import parse_junit_summary, print_parsed_summary

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


def _is_true(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _has_junit_failures(junit_path: Path) -> bool:
    summary = parse_junit_summary(junit_path)
    print_parsed_summary(summary)
    return summary.failures > 0 or summary.errors > 0


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
) -> Classification:
    """Classify offload output as success, test failure, or infrastructure failure."""
    if setup_failed:
        return Classification(
            conclusion="infra_failure",
            offload_infra_failed=True,
            tests_failed=False,
            message="Offload setup failed before tests ran.",
        )

    if junit_path.exists():
        try:
            if _has_junit_failures(junit_path):
                return Classification(
                    conclusion="test_failure",
                    offload_infra_failed=False,
                    tests_failed=True,
                    message="Offloaded tests reported JUnit failures/errors.",
                )
        except (ET.ParseError, ValueError) as exc:
            return Classification(
                conclusion="infra_failure",
                offload_infra_failed=True,
                tests_failed=False,
                message=f"Offload produced invalid JUnit XML: {exc}",
            )

        if exit_code in {0, 2}:
            message = "Offloaded tests passed."
            if exit_code == 2:
                message = "Offload reported flaky tests that passed on retry."
            return Classification(
                conclusion="success",
                offload_infra_failed=False,
                tests_failed=False,
                message=message,
            )

        return Classification(
            conclusion="infra_failure",
            offload_infra_failed=True,
            tests_failed=False,
            message="Offload exited non-zero despite a passing JUnit report.",
        )

    if exit_code == 0:
        return Classification(
            conclusion="infra_failure",
            offload_infra_failed=True,
            tests_failed=False,
            message="Offload exited successfully but did not produce JUnit XML.",
        )

    log_text = _read_log(log_path)
    if INFRA_PATTERN.search(log_text):
        message = "Offload failed before producing JUnit XML; log matches infrastructure patterns."
    else:
        message = "Offload failed before producing JUnit XML."
    return Classification(
        conclusion="infra_failure",
        offload_infra_failed=True,
        tests_failed=False,
        message=message,
    )


def _write_github_outputs(classification: Classification) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write(f"conclusion={classification.conclusion}\n")
        output_file.write(
            f"offload_infra_failed={str(classification.offload_infra_failed).lower()}\n"
        )
        output_file.write(
            f"tests_failed={str(classification.tests_failed).lower()}\n"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--setup-failed", default="false")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = _build_parser().parse_args(argv)
    classification = classify_offload_result(
        exit_code=args.exit_code,
        junit_path=args.junit,
        log_path=args.log,
        setup_failed=_is_true(args.setup_failed),
    )
    print(classification.message)
    _write_github_outputs(classification)
    return 0


if __name__ == "__main__":
    sys.exit(main())
