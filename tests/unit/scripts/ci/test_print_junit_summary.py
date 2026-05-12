"""Tests for JUnit summary parsing."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.ci.print_junit_summary import parse_junit_summary


def test_parse_single_testsuite(tmp_path: Path) -> None:
    """A single testsuite root is parsed directly."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuite tests="3" failures="1" errors="0" skipped="1" time="2.5" />'
    )

    summary = parse_junit_summary(junit)

    assert summary.tests == 3
    assert summary.failures == 1
    assert summary.errors == 0
    assert summary.skipped == 1
    assert summary.time == 2.5


def test_parse_testsuites(tmp_path: Path) -> None:
    """Multiple testsuite children are aggregated."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
        <testsuites>
          <testsuite tests="2" failures="0" errors="1" skipped="0" time="1.0" />
          <testsuite tests="4" failures="1" errors="0" skipped="2" time="3.0" />
        </testsuites>
        """
    )

    summary = parse_junit_summary(junit)

    assert summary.tests == 6
    assert summary.failures == 1
    assert summary.errors == 1
    assert summary.skipped == 2
    assert summary.time == 4.0


@pytest.mark.parametrize(
    "attribute",
    ["tests", "failures", "errors", "skipped", "time"],
)
def test_parse_rejects_malformed_numeric_attributes(
    tmp_path: Path, attribute: str
) -> None:
    """Malformed aggregate counters make the JUnit summary invalid."""
    attrs = {
        "tests": "1",
        "failures": "0",
        "errors": "0",
        "skipped": "0",
        "time": "1.0",
    }
    attrs[attribute] = "not-a-number"
    junit = tmp_path / "junit.xml"
    junit.write_text(
        "<testsuite "
        + " ".join(f'{name}="{value}"' for name, value in attrs.items())
        + " />"
    )

    with pytest.raises(ValueError, match=attribute):
        parse_junit_summary(junit)
