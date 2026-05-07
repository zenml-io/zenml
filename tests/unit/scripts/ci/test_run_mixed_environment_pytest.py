"""Tests for mixed-environment pytest routing."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.ci import run_mixed_environment_pytest


def test_extract_args_routes_test_ids_and_environment() -> None:
    """Wrapper strips the caller environment and keeps common pytest args."""
    common_args, test_ids, junit_path = run_mixed_environment_pytest._extract_args(
        [
            "-p",
            "no:pytest_postgresql",
            "--environment",
            "default",
            "--junitxml=/tmp/result.xml",
            "tests/unit/test_a.py::test_a",
            "tests/integration/test_b.py::test_b",
        ]
    )

    assert common_args == ["-p", "no:pytest_postgresql"]
    assert test_ids == [
        "tests/unit/test_a.py::test_a",
        "tests/integration/test_b.py::test_b",
    ]
    assert junit_path == Path("/tmp/result.xml")


def test_merge_junit_combines_testcases(tmp_path: Path) -> None:
    """Split pytest invocations still produce one offload JUnit file."""
    first = tmp_path / "first.xml"
    first.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0" time="1">'
        '<testcase classname="a" name="test_a" time="1" />'
        "</testsuite>"
    )
    second = tmp_path / "second.xml"
    second.write_text(
        '<testsuite tests="1" failures="1" errors="0" skipped="0" time="2">'
        '<testcase classname="b" name="test_b" time="2"><failure /></testcase>'
        "</testsuite>"
    )
    output = tmp_path / "merged.xml"

    run_mixed_environment_pytest._merge_junit(output, [first, second])

    root = ET.parse(output).getroot()
    assert root.attrib["tests"] == "2"
    assert root.attrib["failures"] == "1"
    assert len(list(root.iter("testcase"))) == 2
