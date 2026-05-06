"""Tests for offload result classification."""

from __future__ import annotations

from pathlib import Path

from scripts.ci.classify_offload_result import classify_offload_result

PASSING_JUNIT = '<testsuite tests="2" failures="0" errors="0" skipped="0" />'
FAILING_JUNIT = """
<testsuite tests="1" failures="1" errors="0">
  <testcase classname="tests.test_example" name="test_failure">
    <failure message="boom" />
  </testcase>
</testsuite>
"""


def test_classifies_success_when_junit_passes(tmp_path: Path) -> None:
    """Passing JUnit reports produce a success classification."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)

    result = classify_offload_result(exit_code=0, junit_path=junit)

    assert result.conclusion == "success"
    assert result.offload_infra_failed is False
    assert result.tests_failed is False


def test_classifies_junit_failures_as_test_failures(tmp_path: Path) -> None:
    """Failing JUnit reports are treated as test failures."""
    junit = tmp_path / "junit.xml"
    junit.write_text(FAILING_JUNIT)

    result = classify_offload_result(exit_code=1, junit_path=junit)

    assert result.conclusion == "test_failure"
    assert result.offload_infra_failed is False
    assert result.tests_failed is True


def test_exit_code_two_with_passing_junit_is_success(tmp_path: Path) -> None:
    """Offload exit code 2 means flakes passed on retry."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)

    result = classify_offload_result(exit_code=2, junit_path=junit)

    assert result.conclusion == "success"
    assert result.offload_infra_failed is False
    assert result.tests_failed is False


def test_missing_junit_is_infrastructure_failure(tmp_path: Path) -> None:
    """Missing JUnit output means the offload backend failed early."""
    log = tmp_path / "offload.log"
    log.write_text("Modal sandbox timeout")

    result = classify_offload_result(
        exit_code=1,
        junit_path=tmp_path / "missing.xml",
        log_path=log,
    )

    assert result.conclusion == "infra_failure"
    assert result.offload_infra_failed is True
    assert result.tests_failed is False


def test_setup_failure_is_infrastructure_failure(tmp_path: Path) -> None:
    """Driver setup failures trigger fallback instead of test failure."""
    result = classify_offload_result(
        exit_code=1,
        junit_path=tmp_path / "missing.xml",
        setup_failed=True,
    )

    assert result.conclusion == "infra_failure"
    assert result.offload_infra_failed is True
    assert result.tests_failed is False
