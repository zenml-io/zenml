"""Print failed test cases from a parsed JUnit XML tree."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _case_label(testcase: ET.Element) -> str:
    classname = testcase.get("classname")
    name = testcase.get("name") or "?"
    if classname:
        return f"{classname}::{name}"
    return name


def _print_outcome(
    testcase: ET.Element,
    outcome_tag: str,
    label: str,
) -> None:
    outcome = testcase.find(outcome_tag)
    if outcome is None:
        return

    message = (outcome.get("message") or "").strip()
    status = "FAIL" if outcome_tag == "failure" else "ERROR"
    print(f"  {status:<5} {label}")
    if message:
        print(f"        {message[:200]}")


def print_failures(root: ET.Element) -> None:
    """Print a concise list of failing JUnit test cases."""

    for testcase in root.iter("testcase"):
        label = _case_label(testcase)
        _print_outcome(testcase, "failure", label)
        _print_outcome(testcase, "error", label)


def main(argv: list[str]) -> int:
    """Print failures from a JUnit XML file path."""

    if len(argv) != 2:
        print(f"Usage: {argv[0]} <junit.xml>", file=sys.stderr)
        return 1

    junit_path = Path(argv[1])
    if not junit_path.exists():
        print(f"File not found: {junit_path}", file=sys.stderr)
        return 1

    try:
        root = ET.parse(junit_path).getroot()
    except (OSError, ET.ParseError) as exc:
        print(f"Failed to read JUnit XML {junit_path}: {exc}", file=sys.stderr)
        return 1

    print_failures(root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
