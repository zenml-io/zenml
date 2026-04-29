"""Unit tests for Modal timing manifest emission."""

import json
import time
from pathlib import Path

import pytest
from scripts.ci.emit_timing_manifest import build_manifest, main


def test_build_manifest_records_phase_durations_and_artifacts(
    tmp_path: Path,
) -> None:
    """Valid phase data produces manifest-ready duration metadata."""
    junit_file = tmp_path / "junit.xml"
    offload_log = tmp_path / "offload.log"
    junit_file.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0" time="1.0" />'
    )
    offload_log.write_text("[BATCH START]\n[BATCH COMPLETE fused=true]\n")

    manifest = build_manifest(
        lane="modal-sqlite-fast-ci",
        output_dir=tmp_path,
        junit_file=junit_file,
        offload_log=offload_log,
        classification="success",
        classification_reason="none",
        classification_diagnostic="passed",
        failed_phase="none",
        failed_tests="[]",
        modal_infra_failed="false",
        test_failed="false",
        harness_failed="false",
        junit_cache_safe="true",
        phases=["offload_run=10,15,success"],
    )

    assert manifest["schema_version"] == 1
    assert manifest["lane"] == "modal-sqlite-fast-ci"
    assert manifest["started_at"] == "1970-01-01T00:00:10+00:00"
    assert manifest["ended_at"] == "1970-01-01T00:00:15+00:00"
    assert manifest["total_duration_s"] == 5.0
    assert manifest["classification"] == {
        "result": "success",
        "kind": "success",
        "reason": "none",
        "diagnostic": "passed",
        "failed_phase": "none",
        "modal_infra_failed": False,
        "test_failed": False,
        "harness_failed": False,
        "junit_cache_safe": True,
        "failed_tests": [],
    }
    assert manifest["cache"]["junit_cache_safe"] is True
    assert manifest["cache"]["junit_file"]["exists"] is True
    assert manifest["tests"]["total"] == 1
    assert manifest["tests"]["passed"] == 1
    assert manifest["batches"]["started"] == 1
    assert manifest["batches"]["completed"] == 1
    assert manifest["phases"] == {"offload_run_s": 5.0}
    assert manifest["phase_details"]["offload_run"]["outcome"] == "success"
    assert manifest["warnings"] == []


def test_missing_artifacts_do_not_block_manifest(tmp_path: Path) -> None:
    """Infra failures can still emit a manifest without JUnit or logs."""
    manifest = build_manifest(
        lane="modal-server-rest-mysql-ci",
        output_dir=tmp_path,
        junit_file=tmp_path / "missing-junit.xml",
        offload_log=tmp_path / "missing-offload.log",
        classification="modal_infra_failure",
        classification_reason="provision_failed",
        classification_diagnostic="server provisioning failed",
        failed_phase="server_provision",
        failed_tests="[]",
        modal_infra_failed="true",
        test_failed="false",
        harness_failed="true",
        junit_cache_safe="false",
        phases=[],
    )

    assert manifest["cache"]["junit_file"] == {
        "path": str(tmp_path / "missing-junit.xml"),
        "exists": False,
        "size_bytes": None,
        "mtime": None,
    }
    assert manifest["batches"]["offload_log"]["exists"] is False
    assert manifest["classification"]["failed_phase"] == "server_provision"
    assert manifest["classification"]["modal_infra_failed"] is True
    assert manifest["classification"]["test_failed"] is False
    assert manifest["classification"]["harness_failed"] is True


def test_missing_phase_timestamps_emit_warnings() -> None:
    """Incomplete workflow outputs are warnings, not hard failures."""
    manifest = build_manifest(
        lane="modal-sqlite-fast-ci",
        output_dir=Path("test-results/modal-sqlite-fast-ci"),
        junit_file=Path("junit.xml"),
        offload_log=Path("offload.log"),
        classification="unknown",
        classification_reason="unknown",
        classification_diagnostic="",
        failed_phase=None,
        failed_tests=None,
        modal_infra_failed=None,
        test_failed=None,
        harness_failed=None,
        junit_cache_safe=None,
        phases=["prepare=,not-a-time,failure"],
    )

    assert manifest["phase_details"]["prepare"]["started_at"] is None
    assert manifest["phase_details"]["prepare"]["ended_at"] is None
    assert manifest["phases"] == {"prepare_s": None}
    assert manifest["warnings"] == [
        "phase 'prepare' is missing a valid start timestamp",
        "phase 'prepare' is missing a valid end timestamp",
    ]


def test_invalid_phase_format_fails(tmp_path: Path) -> None:
    """Malformed phase values fail fast with a CLI error."""
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--lane",
                "modal-sqlite-fast-ci",
                "--output-dir",
                str(tmp_path),
                "--junit-file",
                str(tmp_path / "junit.xml"),
                "--offload-log",
                str(tmp_path / "offload.log"),
                "--phase",
                "prepare:1,2,success",
            ]
        )

    assert exc_info.value.code == 2


def test_main_writes_manifest_json(tmp_path: Path) -> None:
    """The CLI writes manifest.json under the requested output directory."""
    started_at = str(time.time())
    ended_at = str(float(started_at) + 3)

    assert (
        main(
            [
                "--lane",
                "modal-sqlite-fast-ci",
                "--output-dir",
                str(tmp_path),
                "--junit-file",
                str(tmp_path / "junit.xml"),
                "--offload-log",
                str(tmp_path / "offload.log"),
                "--classification",
                "success",
                "--classification-reason",
                "none",
                "--classification-diagnostic",
                "passed",
                "--modal-infra-failed",
                "false",
                "--test-failed",
                "false",
                "--harness-failed",
                "false",
                "--junit-cache-safe",
                "true",
                "--phase",
                f"classify={started_at},{ended_at},success",
            ]
        )
        == 0
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["lane"] == "modal-sqlite-fast-ci"
    assert manifest["phases"] == {"classify_s": 3.0}
    assert manifest["cache"]["junit_cache_safe"] is True
