"""Print a concise test summary from a JUnit XML file."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.ci.print_junit_failures import print_failures


def _int_attr(element: ET.Element, attr_name: str) -> int:
    return int(element.get(attr_name, "0"))


def _float_attr(element: ET.Element, attr_name: str) -> float:
    return float(element.get(attr_name, "0"))


def _summarize(root: ET.Element) -> tuple[int, int, int, float]:
    suites = list(root.findall("testsuite"))
    if root.tag == "testsuites" and suites:
        tests = sum(_int_attr(suite, "tests") for suite in suites)
        failures = sum(_int_attr(suite, "failures") for suite in suites)
        errors = sum(_int_attr(suite, "errors") for suite in suites)
        time_s = sum(_float_attr(suite, "time") for suite in suites)
        return tests, failures, errors, time_s

    tests = _int_attr(root, "tests")
    failures = _int_attr(root, "failures")
    errors = _int_attr(root, "errors")
    time_s = _float_attr(root, "time")
    return tests, failures, errors, time_s


def print_summary(junit_path: Path) -> int:
    """Print a concise summary of a JUnit XML file."""

    try:
        root = ET.parse(junit_path).getroot()
    except (OSError, ET.ParseError) as exc:
        print(f"Failed to read JUnit XML {junit_path}: {exc}", file=sys.stderr)
        return 1

    tests, failures, errors, time_s = _summarize(root)
    passed = tests - failures - errors

    print(
        f"Total: {tests}  Passed: {passed}  "
        f"Failed: {failures}  Errors: {errors}  Time: {time_s:.1f}s"
    )

    if not (failures or errors):
        return 0

    print("\nFailed tests:")
    print_failures(root)
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
