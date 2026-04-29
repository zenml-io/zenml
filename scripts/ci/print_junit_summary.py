"""Print a concise test summary from a JUnit XML file."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.ci.print_junit_failures import print_failures  # noqa: E402


@dataclass(frozen=True)
class JUnitSummary:
    """Aggregate JUnit test counts."""

    tests: int
    failures: int
    errors: int
    skipped: int
    time_s: float

    @property
    def passed(self) -> int:
        """Return the number of passed tests."""
        return self.tests - self.failures - self.errors - self.skipped


def _int_attr(element: ET.Element, attr_name: str) -> int:
    return int(element.get(attr_name, "0"))


def _float_attr(element: ET.Element, attr_name: str) -> float:
    return float(element.get(attr_name, "0"))


def _summarize(root: ET.Element) -> JUnitSummary:
    suites = list(root.findall("testsuite"))
    if root.tag == "testsuites" and suites:
        return JUnitSummary(
            tests=sum(_int_attr(suite, "tests") for suite in suites),
            failures=sum(_int_attr(suite, "failures") for suite in suites),
            errors=sum(_int_attr(suite, "errors") for suite in suites),
            skipped=sum(_int_attr(suite, "skipped") for suite in suites),
            time_s=sum(_float_attr(suite, "time") for suite in suites),
        )

    return JUnitSummary(
        tests=_int_attr(root, "tests"),
        failures=_int_attr(root, "failures"),
        errors=_int_attr(root, "errors"),
        skipped=_int_attr(root, "skipped"),
        time_s=_float_attr(root, "time"),
    )


def parse_junit_summary(junit_path: Path) -> tuple[ET.Element, JUnitSummary]:
    """Parse a JUnit XML file and return its root plus aggregate summary."""
    root = ET.parse(junit_path).getroot()
    return root, _summarize(root)


def print_parsed_summary(root: ET.Element, summary: JUnitSummary) -> None:
    """Print a concise summary from already-parsed JUnit XML data."""
    print(
        f"Total: {summary.tests}  Passed: {summary.passed}  "
        f"Failed: {summary.failures}  Errors: {summary.errors}  "
        f"Skipped: {summary.skipped}  Time: {summary.time_s:.1f}s"
    )

    if summary.failures or summary.errors:
        print("\nFailed tests:")
        print_failures(root)


def print_summary(junit_path: Path) -> int:
    """Print a concise summary of a JUnit XML file."""
    try:
        root, summary = parse_junit_summary(junit_path)
    except (OSError, ET.ParseError) as exc:
        print(f"Failed to read JUnit XML {junit_path}: {exc}", file=sys.stderr)
        return 1

    print_parsed_summary(root, summary)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <junit.xml>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    sys.exit(print_summary(path))
