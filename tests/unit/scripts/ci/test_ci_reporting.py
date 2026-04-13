"""Unit tests for CI reporting helpers."""

from pathlib import Path

import pytest

from scripts.ci.print_junit_summary import print_summary


def test_print_summary_handles_testsuites_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Summarizes wrapped pytest JUnit output correctly."""

    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        """
        <testsuites>
          <testsuite tests="2" failures="1" errors="0" time="1.5">
            <testcase classname="suite" name="passes" />
            <testcase classname="suite" name="fails">
              <failure message="boom">trace</failure>
            </testcase>
          </testsuite>
        </testsuites>
        """.strip()
    )

    assert print_summary(junit_path) == 0

    captured = capsys.readouterr()
    assert "Total: 2  Passed: 1  Failed: 1  Errors: 0  Time: 1.5s" in captured.out
    assert "FAIL  suite::fails" in captured.out


def test_print_summary_rejects_corrupt_xml(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Returns nonzero and prints a useful error for corrupt XML."""

    junit_path = tmp_path / "junit.xml"
    junit_path.write_text("<testsuite")

    assert print_summary(junit_path) == 1

    captured = capsys.readouterr()
    assert f"Failed to read JUnit XML {junit_path}" in captured.err
