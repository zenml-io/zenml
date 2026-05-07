"""Run offload pytest batches with per-test environment routing."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def _extract_args(argv: list[str]) -> tuple[list[str], list[str], Path]:
    common_args: list[str] = []
    test_ids: list[str] = []
    junit_path: Path | None = None
    index = 0

    while index < len(argv):
        arg = argv[index]
        if arg.startswith("--junitxml="):
            junit_path = Path(arg.split("=", 1)[1])
        elif arg == "--junitxml":
            index += 1
            junit_path = Path(argv[index])
        elif arg == "--environment":
            index += 1
        elif arg.startswith("--environment="):
            pass
        elif arg.startswith("tests/"):
            test_ids.append(arg)
        else:
            common_args.append(arg)
        index += 1

    if junit_path is None:
        raise ValueError("Expected --junitxml in pytest arguments.")
    return common_args, test_ids, junit_path


def _run_pytest(
    *,
    common_args: list[str],
    test_ids: list[str],
    environment: str,
    junit_path: Path,
) -> int:
    if not test_ids:
        return 0

    command = [
        sys.executable,
        "-m",
        "pytest",
        *common_args,
        "--environment",
        environment,
        f"--junitxml={junit_path}",
        *test_ids,
    ]
    return subprocess.run(command).returncode


def _merge_junit(output_path: Path, input_paths: list[Path]) -> None:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    total_time = 0.0
    merged = ET.Element("testsuite", {"name": "offload-batch"})

    for path in input_paths:
        if not path.exists():
            continue
        root = ET.parse(path).getroot()
        suites = list(root.iter("testsuite")) if root.tag != "testsuite" else [root]
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.attrib.get(key, "0") or 0)
            total_time += float(suite.attrib.get("time", "0") or 0)
            for testcase in suite.findall("testcase"):
                merged.append(testcase)

    for key, value in totals.items():
        merged.set(key, str(value))
    merged.set("time", f"{total_time:.3f}")
    ET.ElementTree(merged).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )


def main(argv: list[str] | None = None) -> int:
    """Route unit tests to default and integration tests to remote MySQL."""
    common_args, test_ids, junit_path = _extract_args(argv or sys.argv[1:])
    unit_tests = [test_id for test_id in test_ids if test_id.startswith("tests/unit/")]
    integration_tests = [
        test_id for test_id in test_ids if test_id.startswith("tests/integration/")
    ]
    other_tests = [
        test_id
        for test_id in test_ids
        if not test_id.startswith(("tests/unit/", "tests/integration/"))
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        unit_junit = temp_path / "unit.xml"
        integration_junit = temp_path / "integration.xml"
        other_junit = temp_path / "other.xml"

        exit_codes = [
            _run_pytest(
                common_args=common_args,
                test_ids=unit_tests,
                environment="default",
                junit_path=unit_junit,
            ),
            _run_pytest(
                common_args=common_args,
                test_ids=integration_tests,
                environment="remote-mysql-modal",
                junit_path=integration_junit,
            ),
            _run_pytest(
                common_args=common_args,
                test_ids=other_tests,
                environment="default",
                junit_path=other_junit,
            ),
        ]
        _merge_junit(junit_path, [unit_junit, integration_junit, other_junit])

    return 1 if any(exit_codes) else 0


if __name__ == "__main__":
    sys.exit(main())
