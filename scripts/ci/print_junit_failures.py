"""Print failed test cases from JUnit XML files."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _case_label(case: ET.Element) -> str:
    classname = case.attrib.get("classname", "")
    name = case.attrib.get("name", "<unknown>")
    return f"{classname}.{name}" if classname else name


def _print_outcome(case: ET.Element, outcome: ET.Element) -> None:
    message = outcome.attrib.get("message", "")
    outcome_type = outcome.attrib.get("type", outcome.tag)
    print(f"- {_case_label(case)} [{outcome_type}] {message}".rstrip())
    if outcome.text and outcome.text.strip():
        print(outcome.text.strip())


def print_failures(path: str | Path, *, limit: int = 50) -> int:
    """Print failed and errored test cases and return the number printed."""
    root = ET.parse(path).getroot()
    printed = 0
    for case in root.iter("testcase"):
        for outcome in list(case):
            if outcome.tag not in {"failure", "error"}:
                continue
            if printed == 0:
                print("Failed tests:")
            if printed >= limit:
                print(f"... truncated after {limit} failures/errors")
                return printed
            _print_outcome(case, outcome)
            printed += 1
    return printed


def main(argv: list[str]) -> int:
    """CLI entrypoint."""
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <junit.xml>", file=sys.stderr)
        return 2
    print_failures(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
