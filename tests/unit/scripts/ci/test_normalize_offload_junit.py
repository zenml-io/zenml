"""Tests for offload JUnit normalization."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.ci.normalize_offload_junit import normalize_junit


def test_normalize_junit_rewrites_function_test_name(tmp_path: Path) -> None:
    """Pytest JUnit names are converted to collect node IDs."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
<testsuite>
  <testcase classname="tests.unit.foo.test_bar" name="test_baz" time="1" />
</testsuite>
"""
    )

    assert normalize_junit(junit) == 1

    testcase = next(ET.parse(junit).getroot().iter("testcase"))
    assert testcase.attrib["name"] == "tests/unit/foo/test_bar.py::test_baz"


def test_normalize_junit_rewrites_class_test_name(tmp_path: Path) -> None:
    """Class-based pytest names keep the class in the node ID."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
<testsuite>
  <testcase classname="tests.integration.foo.test_bar.TestThing" name="test_baz[x]" time="1" />
</testsuite>
"""
    )

    normalize_junit(junit)

    testcase = next(ET.parse(junit).getroot().iter("testcase"))
    assert (
        testcase.attrib["name"]
        == "tests/integration/foo/test_bar.py::TestThing::test_baz[x]"
    )
