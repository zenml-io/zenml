"""Regression tests for the Modal offload CI harness."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def _read_toml_string(contents: str, key: str) -> str:
    match = re.search(
        rf'^{re.escape(key)}\s*=\s*"(?P<value>[^"]*)"$',
        contents,
        re.MULTILINE,
    )
    assert match is not None
    return match.group("value")


def test_modal_server_create_command_passes_resolved_sandbox_helper() -> None:
    """Ensures the wrapper never tries to spawn a literal @ helper path."""
    config = _read_repo_file("offload-modal-server-mysql.toml")
    create_command = _read_toml_string(config, "create_command")

    assert create_command == (
        "bash scripts/ci/create_modal_server_mysql_sandbox.sh "
        "@modal_sandbox.py {image_id}"
    )

    wrapper = _read_repo_file(
        "scripts/ci/create_modal_server_mysql_sandbox.sh"
    )
    assert "uv run @modal_sandbox.py" not in wrapper
    assert 'uv run "$modal_sandbox_script" create "$image_id"' in wrapper


def test_modal_fast_ci_wall_clock_exceeds_offload_timeout() -> None:
    """Keeps GitHub from killing offload before it can report an exit code."""
    workflow = _read_repo_file(".github/workflows/linux-fast-modal.yml")
    offload_config = _read_repo_file("offload.toml")

    job_start = workflow.index("  modal-fast-ci:\n")
    next_job_start = workflow.index("  fallback-unit-test:\n", job_start)
    job_config = workflow[job_start:next_job_start]

    workflow_timeout = re.search(
        r"^\s{4}timeout-minutes:\s*(?P<minutes>\d+)$",
        job_config,
        re.MULTILINE,
    )
    offload_timeout = re.search(
        r"^test_timeout_secs\s*=\s*(?P<seconds>\d+)$",
        offload_config,
        re.MULTILINE,
    )
    assert workflow_timeout is not None
    assert offload_timeout is not None

    workflow_timeout_secs = int(workflow_timeout.group("minutes")) * 60
    offload_timeout_secs = int(offload_timeout.group("seconds"))

    assert workflow_timeout_secs >= offload_timeout_secs + 10 * 60


def test_modal_fast_ci_uses_lightweight_runner_setup() -> None:
    """Keeps warm Modal runs from paying for a local ZenML dev install."""
    workflow = _read_repo_file(".github/workflows/linux-fast-modal.yml")

    assert "./.github/actions/setup_environment" not in workflow
    assert "scripts/install-zenml-dev.sh --system" not in workflow
    assert "actions/setup-python@" in workflow
    assert (
        "uv pip install --system -r scripts/ci/modal_sandbox_requirements.txt"
        in workflow
    )


def test_modal_batch_cap_targets_one_warm_wave() -> None:
    """Documents the batch cap used for sub-5-minute warm Modal runs."""
    assert "max_batch_duration_secs = 180" in _read_repo_file("offload.toml")
    assert "max_batch_duration_secs = 180" in _read_repo_file(
        "offload-modal-server-mysql.toml"
    )


def test_modal_workflows_classify_sandbox_create_failures() -> None:
    """Keeps sandbox creation failures from looking like test failures."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)

        assert "Failed to create sandboxes" in workflow
        assert "Failed to execute command: Create command failed" in workflow
        assert "Failed to spawn: .*modal_sandbox" in workflow
