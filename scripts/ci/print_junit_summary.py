"""Print concise summaries for JUnit XML files."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from scripts.ci.print_junit_failures import print_failures


@dataclass(frozen=True)
class JUnitSummary:
    """Aggregated JUnit counts."""

    tests: int
    failures: int
    errors: int
    skipped: int
    time: float

    @property
    def failed(self) -> bool:
        """Whether the summary contains failed or errored tests."""
        return self.failures > 0 or self.errors > 0


def _int_attr(element: ET.Element, name: str) -> int:
    value = element.attrib.get(name, "0")
    try:
        return int(value)
    except ValueError:
        return 0


def _float_attr(element: ET.Element, name: str) -> float:
    value = element.attrib.get(name, "0")
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_junit_summary(path: str | Path) -> JUnitSummary:
    """Parse aggregate counts from a JUnit XML file."""
    root = ET.parse(path).getroot()
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.iter("testsuite"))
    else:
        raise ValueError(f"Unsupported JUnit root tag: {root.tag}")

    return JUnitSummary(
        tests=sum(_int_attr(suite, "tests") for suite in suites),
        failures=sum(_int_attr(suite, "failures") for suite in suites),
        errors=sum(_int_attr(suite, "errors") for suite in suites),
        skipped=sum(_int_attr(suite, "skipped") for suite in suites),
        time=sum(_float_attr(suite, "time") for suite in suites),
    )


def print_parsed_summary(summary: JUnitSummary) -> None:
    """Print a human-readable JUnit summary."""
    print(
        "JUnit summary: "
        f"tests={summary.tests}, failures={summary.failures}, "
        f"errors={summary.errors}, skipped={summary.skipped}, "
        f"time={summary.time:.2f}s"
    )


def print_summary(path: str | Path) -> JUnitSummary:
    """Parse and print a JUnit summary plus failure details."""
    summary = parse_junit_summary(path)
    print_parsed_summary(summary)
    if summary.failed:
        print_failures(path)
    return summary


def main(argv: list[str]) -> int:
    """CLI entrypoint."""
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <junit.xml>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2
    print_summary(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
