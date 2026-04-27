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


def test_modal_workflows_install_runner_collection_dependencies() -> None:
    """Keeps offload's local pytest collection from using a bare Python."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)

        assert "./.github/actions/setup_environment" not in workflow
        assert "scripts/install-zenml-dev.sh --system" not in workflow
        assert "actions/setup-python@" in workflow
        assert "runner_extras=" in workflow
        assert "dev,connectors-aws" in workflow
        assert (
            'uv pip install --system -e "$runner_extras" -r '
            "scripts/ci/modal_sandbox_requirements.txt"
        ) in workflow
        assert 'uv pip install --system "setuptools<82"' in workflow


def test_modal_batch_cap_targets_one_warm_wave() -> None:
    """Documents the batch cap used for sub-5-minute warm Modal runs."""
    assert "max_batch_duration_secs = 180" in _read_repo_file("offload.toml")
    assert "max_batch_duration_secs = 180" in _read_repo_file(
        "offload-modal-server-mysql.toml"
    )


def test_modal_workflows_restore_offload_image_cache_with_fallback() -> None:
    """Keeps Modal image cache restores warm across image-key churn."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )
    exact_key_pattern = re.compile(
        r"key: offload-image-v2-\$\{\{ runner\.os \}\}-"
        r"\$\{\{ inputs\.python-version \}\}-\$\{\{\s*\n"
        r"\s+hashFiles\('Dockerfile\.ci', 'pyproject\.toml', "
        r"'scripts/install-zenml-dev\.sh'\)\s*\n"
        r"\s+\}\}"
    )
    fallback_key = (
        "offload-image-v2-${{ runner.os }}-${{ inputs.python-version }}-"
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)
        restore_step = workflow.split(
            "      - name: Restore offload image cache\n", maxsplit=1
        )[1].split("      - name:", maxsplit=1)[0]

        assert "path: .offload-image-cache" in restore_step
        assert exact_key_pattern.search(restore_step) is not None
        assert "restore-keys: |" in restore_step
        assert fallback_key in restore_step


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


def test_modal_workflows_classify_collection_failures_as_infra() -> None:
    """Keeps local collect-only setup failures out of test-failure reports."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)

        assert 'touch -d "2000-01-01 00:00:00 UTC" "$junit_file"' in workflow
        assert "Failed to discover tests" in workflow
        assert "pytest --collect-only failed" in workflow
        assert "No module named pytest" in workflow
