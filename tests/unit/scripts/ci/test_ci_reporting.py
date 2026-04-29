"""Unit tests for CI reporting helpers."""

import os
from pathlib import Path

import pytest
from scripts.ci.print_junit_summary import parse_junit_summary, print_summary
from scripts.ci.validate_xml_artifact import (
    ArtifactValidationError,
    validate_xml_artifact,
)


def test_print_summary_handles_testsuites_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Summarizes wrapped pytest JUnit output correctly."""
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        """
        <testsuites>
          <testsuite tests="3" failures="1" errors="0" skipped="1" time="1.5">
            <testcase classname="suite" name="passes" />
            <testcase classname="suite" name="skips"><skipped /></testcase>
            <testcase classname="suite" name="fails">
              <failure message="boom">trace</failure>
            </testcase>
          </testsuite>
        </testsuites>
        """.strip()
    )

    assert print_summary(junit_path) == 0

    captured = capsys.readouterr()
    assert (
        "Total: 3  Passed: 1  Failed: 1  Errors: 0  Skipped: 1  Time: 1.5s"
        in captured.out
    )
    assert "FAIL  suite::fails" in captured.out


def test_parse_junit_summary_counts_skipped_testsuite_root(
    tmp_path: Path,
) -> None:
    """Includes skipped tests when summarizing a single testsuite root."""
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        '<testsuite tests="4" failures="0" errors="1" skipped="2" time="3.0" />'
    )

    _, summary = parse_junit_summary(junit_path)

    assert summary.tests == 4
    assert summary.errors == 1
    assert summary.skipped == 2
    assert summary.passed == 1


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


def test_validate_xml_artifact_accepts_expected_root(tmp_path: Path) -> None:
    """Accepts a parseable XML artifact with an allowed root tag."""
    artifact = tmp_path / "coverage.xml"
    artifact.write_text("<coverage />")

    validate_xml_artifact(
        artifact,
        label="coverage XML",
        allowed_root_tags={"coverage"},
    )


def test_validate_xml_artifact_rejects_stale_file(tmp_path: Path) -> None:
    """Rejects artifacts older than the requested lower bound."""
    artifact = tmp_path / "coverage.xml"
    artifact.write_text("<coverage />")
    os.utime(artifact, (100, 100))

    with pytest.raises(ArtifactValidationError, match="stale"):
        validate_xml_artifact(
            artifact,
            label="coverage XML",
            allowed_root_tags={"coverage"},
            mtime_after=101,
        )


def test_validate_xml_artifact_rejects_unexpected_root(tmp_path: Path) -> None:
    """Rejects parseable XML with the wrong artifact root tag."""
    artifact = tmp_path / "coverage.xml"
    artifact.write_text("<testsuite />")

    with pytest.raises(ArtifactValidationError, match="unexpected root tag"):
        validate_xml_artifact(
            artifact,
            label="coverage XML",
            allowed_root_tags={"coverage"},
        )
