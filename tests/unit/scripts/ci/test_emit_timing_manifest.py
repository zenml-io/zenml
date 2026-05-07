"""Tests for offload timing manifest generation."""

from __future__ import annotations

from pathlib import Path

from scripts.ci.emit_timing_manifest import build_manifest


def test_build_manifest_includes_duration_and_artifacts(
    tmp_path: Path,
) -> None:
    """Manifest captures timing and artifact presence."""
    (tmp_path / "junit.xml").write_text("<testsuite />")
    (tmp_path / "junit.seed.xml").write_text("<testsuite />")
    (tmp_path / "junit.stale.xml").write_text("<testsuite />")
    (tmp_path / "run-start.marker").write_text("start")

    manifest = build_manifest(
        lane="default",
        output_dir=tmp_path,
        started_at="10",
        completed_at="15",
        classification="success",
        phases=["setup=1,3,success", "test_execution=3,15,exit_0"],
    )

    assert manifest["duration_seconds"] == 5
    assert manifest["classification"] == "success"
    assert manifest["phases"]["setup"]["duration_seconds"] == 2
    assert manifest["phases"]["test_execution"]["status"] == "exit_0"
    assert manifest["artifacts"]["junit_xml"]["exists"] is True
    assert manifest["artifacts"]["junit_seed_xml"]["exists"] is True
    assert manifest["artifacts"]["junit_stale_xml"]["exists"] is True
    assert manifest["artifacts"]["run_start_marker"]["exists"] is True
    assert manifest["artifacts"]["offload_log"]["exists"] is False
    assert manifest["cache"]["uv_cache_hit"] == ""
