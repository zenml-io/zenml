"""Unit tests for Modal offload result classification."""

import os
import time
from pathlib import Path
from typing import Literal

from scripts.ci.classify_offload_result import classify_offload_result, main


def _write_junit(
    path: Path,
    *,
    tests: int = 1,
    failures: int = 0,
    errors: int = 0,
    skipped: int = 0,
    body: str = "",
) -> float:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<testsuite tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}" time="1.0">{body}</testsuite>'
    )
    now = time.time()
    os.utime(path, (now, now))
    return now - 1


def _classify(
    tmp_path: Path,
    *,
    exit_code: str = "0",
    infra_policy: Literal["fallback", "fail"] = "fallback",
    run_started_at: str | None = None,
    offload_log_text: str = "",
    **kwargs: str,
):
    junit_path = tmp_path / "junit.xml"
    offload_log = tmp_path / "offload.log"
    offload_log.write_text(offload_log_text)
    if run_started_at is None and junit_path.exists():
        run_started_at = str(junit_path.stat().st_mtime - 1)

    return classify_offload_result(
        lane="modal-sqlite-fast-ci",
        infra_policy=infra_policy,
        junit_file=junit_path,
        offload_log=offload_log,
        exit_code=exit_code,
        run_started_at=run_started_at,
        **kwargs,
    )


def test_success_with_fresh_passing_junit_is_cache_safe(
    tmp_path: Path,
    capsys,
) -> None:
    """A clean exit and fresh passing JUnit can update duration caches."""
    start = _write_junit(tmp_path / "junit.xml")

    classification = _classify(tmp_path, run_started_at=str(start))

    assert not classification.modal_infra_failed
    assert not classification.test_failed
    assert not classification.harness_failed
    assert classification.junit_cache_safe
    assert classification.classification == "success"
    assert classification.reason == "none"
    assert classification.failed_phase == "none"
    assert classification.failed_tests == ()
    assert "Total: 1  Passed: 1" in capsys.readouterr().out


def test_exit_code_two_with_passing_junit_is_cache_safe(
    tmp_path: Path,
    capsys,
) -> None:
    """Offload exit code 2 is treated as flaky success with passing JUnit."""
    start = _write_junit(tmp_path / "junit.xml")

    classification = _classify(
        tmp_path, exit_code="2", run_started_at=str(start)
    )

    assert not classification.test_failed
    assert classification.junit_cache_safe
    assert "::notice::" in capsys.readouterr().out


def test_junit_failures_classify_as_test_failure(
    tmp_path: Path,
    capsys,
) -> None:
    """Failing JUnit output is a test failure regardless of offload exit code."""
    start = _write_junit(
        tmp_path / "junit.xml",
        tests=1,
        failures=1,
        body=(
            '<testcase classname="suite" name="test">'
            '<failure message="assertion failed" />'
            "</testcase>"
        ),
    )

    classification = _classify(
        tmp_path, exit_code="0", run_started_at=str(start)
    )

    assert not classification.modal_infra_failed
    assert classification.test_failed
    assert not classification.harness_failed
    assert not classification.junit_cache_safe
    assert classification.classification == "test_failure"
    assert classification.reason == "junit_failures"
    assert classification.failed_phase == "test_execution"
    assert classification.failed_tests == ("suite::test",)
    output = capsys.readouterr().out
    assert "Total: 1  Passed: 0  Failed: 1" in output
    assert "Failed tests:" in output
    assert "FAIL  suite::test" in output
    assert "assertion failed" in output


def test_failed_tests_output_is_capped(tmp_path: Path) -> None:
    """Failed testcase identifiers are capped for stable GitHub outputs."""
    body = "".join(
        f'<testcase classname="suite" name="test_{index}">'
        '<failure message="failed" /></testcase>'
        for index in range(25)
    )
    start = _write_junit(
        tmp_path / "junit.xml",
        tests=25,
        failures=25,
        body=body,
    )

    classification = _classify(tmp_path, run_started_at=str(start))

    assert len(classification.failed_tests) == 20
    assert classification.failed_tests[0] == "suite::test_0"
    assert classification.failed_tests[-1] == "suite::test_19"


def test_missing_junit_with_infra_log_pattern_is_infra_failure(
    tmp_path: Path,
    capsys,
) -> None:
    """Known Modal preparation log patterns classify missing JUnit as infra."""
    classification = _classify(
        tmp_path,
        exit_code="1",
        run_started_at=str(time.time()),
        offload_log_text="Failed to prepare Default provider",
    )

    assert classification.modal_infra_failed
    assert not classification.test_failed
    assert classification.harness_failed
    assert not classification.junit_cache_safe
    assert classification.classification == "modal_infra_failure"
    assert classification.reason == "infra_log_pattern"
    assert classification.failed_phase == "sandbox_create"
    assert "::warning::" in capsys.readouterr().out


def test_fail_policy_reports_infra_failures_as_errors(
    tmp_path: Path,
    capsys,
) -> None:
    """The strict Modal lane annotates infra failures as errors."""
    classification = _classify(
        tmp_path,
        exit_code="1",
        infra_policy="fail",
        run_started_at=str(time.time()),
        offload_log_text="Failed to prepare Default provider",
    )

    assert classification.modal_infra_failed
    assert not classification.test_failed
    assert "::error::" in capsys.readouterr().out


def test_missing_junit_without_infra_pattern_is_test_failure(
    tmp_path: Path,
) -> None:
    """A run without JUnit is not infra unless a clear infra signal exists."""
    classification = _classify(
        tmp_path,
        exit_code="1",
        run_started_at=str(time.time()),
        offload_log_text="pytest failed",
    )

    assert not classification.modal_infra_failed
    assert classification.test_failed
    assert classification.harness_failed
    assert not classification.junit_cache_safe
    assert classification.classification == "test_failure"
    assert classification.reason == "junit_not_fresh"
    assert classification.failed_phase == "junit_invalid"


def test_corrupt_junit_is_test_failure(tmp_path: Path) -> None:
    """Corrupt fresh JUnit XML is treated as a test/reporting failure."""
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text("<testsuite")
    now = time.time()
    os.utime(junit_path, (now, now))

    classification = _classify(
        tmp_path, exit_code="1", run_started_at=str(now - 1)
    )

    assert not classification.modal_infra_failed
    assert classification.test_failed
    assert not classification.junit_cache_safe


def test_prepare_failure_without_junit_is_infra_failure(
    tmp_path: Path,
) -> None:
    """Explicit preparation failures are classified as Modal infra failures."""
    classification = _classify(
        tmp_path,
        exit_code="1",
        run_started_at=str(time.time()),
        prepare_outcome="failure",
    )

    assert classification.modal_infra_failed
    assert not classification.test_failed
    assert classification.harness_failed
    assert classification.classification == "modal_infra_failure"
    assert classification.reason == "prepare_failed"
    assert classification.failed_phase == "modal_prepare"


def test_provision_failure_without_junit_is_attributed_to_infra(
    tmp_path: Path,
) -> None:
    """REST server provisioning failures get a stable infra reason."""
    classification = _classify(
        tmp_path,
        exit_code="1",
        infra_policy="fail",
        run_started_at=str(time.time()),
        provision_outcome="failure",
    )

    assert classification.modal_infra_failed
    assert not classification.test_failed
    assert classification.harness_failed
    assert classification.classification == "modal_infra_failure"
    assert classification.reason == "provision_failed"
    assert classification.failed_phase == "server_provision"
    assert "provision_failed" in classification.diagnostic


def test_main_writes_github_outputs(tmp_path: Path, monkeypatch) -> None:
    """The CLI appends classification fields to GITHUB_OUTPUT."""
    start = _write_junit(tmp_path / "junit.xml")
    offload_log = tmp_path / "offload.log"
    offload_log.write_text("")
    output_path = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))

    assert (
        main(
            [
                "--lane",
                "modal-sqlite-fast-ci",
                "--infra-policy",
                "fallback",
                "--junit-file",
                str(tmp_path / "junit.xml"),
                "--offload-log",
                str(offload_log),
                "--exit-code",
                "0",
                "--run-started-at",
                str(start),
            ]
        )
        == 0
    )

    assert output_path.read_text() == (
        "modal_infra_failed=false\n"
        "test_failed=false\n"
        "harness_failed=false\n"
        "junit_cache_safe=true\n"
        "classification=success\n"
        "reason=none\n"
        "failed_phase=none\n"
        "failed_tests=[]\n"
        "diagnostic=modal-sqlite-fast-ci: offload completed with "
        "passing JUnit results\n"
    )
