"""Print a concise test summary from a JUnit XML file."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def print_summary(junit_path: Path) -> None:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    tests = int(root.get("tests", 0))
    failures = int(root.get("failures", 0))
    errors = int(root.get("errors", 0))
    time_s = float(root.get("time", 0))
    passed = tests - failures - errors

    print(
        f"Total: {tests}  Passed: {passed}  "
        f"Failed: {failures}  Errors: {errors}  Time: {time_s:.1f}s"
    )

    if not (failures or errors):
        return

    print("\nFailed tests:")
    for ts in root.iter("testsuite"):
        for tc in ts.iter("testcase"):
            fail = tc.find("failure")
            err = tc.find("error")
            if fail is not None:
                name = tc.get("name", "?")
                msg = (fail.get("message") or "")[:200]
                print(f"  FAIL  {name}")
                if msg:
                    print(f"        {msg}")
            elif err is not None:
                name = tc.get("name", "?")
                msg = (err.get("message") or "")[:200]
                print(f"  ERROR {name}")
                if msg:
                    print(f"        {msg}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <junit.xml>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    print_summary(path)
