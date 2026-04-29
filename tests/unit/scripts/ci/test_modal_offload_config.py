"""Regression tests for the Modal offload CI harness."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]


@cache
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


def _read_workflow_step(workflow: str, step_name: str) -> dict[str, Any]:
    parsed_workflow: dict[str, Any] = yaml.safe_load(workflow)
    for job in parsed_workflow["jobs"].values():
        for step in job.get("steps", []):
            if step.get("name") == step_name:
                return step

    raise AssertionError(f"Workflow step not found: {step_name}")


def _read_workflow_step_run(workflow: str, step_name: str) -> str:
    step = _read_workflow_step(workflow, step_name)
    run = step.get("run", "")
    assert isinstance(run, str)
    return run


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
    assert "--env ZENML_TESTS_AUTO_ISOLATE=1" in wrapper
    assert "ZENML_TESTS_AUTO_ISOLATE" not in _read_repo_file("offload.toml")
    assert "ZENML_MODAL_SERVER_USERNAME must be set." in wrapper
    assert "ZENML_MODAL_SERVER_PASSWORD must be set." in wrapper
    assert (
        '--env "ZENML_MODAL_SERVER_USERNAME=${ZENML_MODAL_SERVER_USERNAME}"'
        in wrapper
    )
    assert (
        '--env "ZENML_MODAL_SERVER_PASSWORD=${ZENML_MODAL_SERVER_PASSWORD}"'
        in wrapper
    )


def test_modal_workflows_use_ci_modal_environment() -> None:
    """Keeps Modal apps pinned to the CI Modal environment."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)
        assert "MODAL_ENVIRONMENT: ci" in workflow


def test_modal_sqlite_ci_wall_clock_exceeds_offload_timeout() -> None:
    """Keeps GitHub from killing offload before it reports an exit code."""
    workflow = _read_repo_file(".github/workflows/linux-fast-modal.yml")
    offload_config = _read_repo_file("offload.toml")

    job_start = workflow.index("  modal-sqlite-fast-ci:\n")
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


def test_modal_scheduler_parallelism_targets_one_warm_wave() -> None:
    """Guards the sandbox concurrency used for warm Modal runs."""
    assert "max_parallel = 32" in _read_repo_file("offload.toml")
    assert "max_parallel = 32" in _read_repo_file(
        "offload-modal-server-mysql.toml"
    )


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
    cache_key_files = (
        "Dockerfile.ci",
        ".dockerignore",
        "pyproject.toml",
        "scripts/install-zenml-dev.sh",
        "offload.toml",
        "offload-modal-server-mysql.toml",
    )
    fallback_key = (
        "offload-image-v2-${{ runner.os }}-${{ inputs.python-version }}-"
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)
        restore_step = _read_workflow_step(
            workflow, "Restore offload image cache"
        )
        restore_config = restore_step["with"]
        cache_key = restore_config["key"]

        assert restore_config["path"] == ".offload-image-cache"
        for cache_key_file in cache_key_files:
            assert cache_key_file in cache_key
        assert fallback_key in restore_config["restore-keys"]


def test_modal_workflows_use_shared_classifier() -> None:
    """Avoids duplicated shell classification drifting between lanes."""
    classifier = _read_repo_file("scripts/ci/classify_offload_result.py")
    workflow_expectations = {
        ".github/workflows/linux-fast-modal.yml": (
            "modal-sqlite-fast-ci",
            "--infra-policy fallback",
        ),
        ".github/workflows/linux-modal-server-mysql.yml": (
            "modal-server-rest-mysql-ci",
            "--infra-policy fail",
        ),
    }

    for workflow_path, (lane, policy) in workflow_expectations.items():
        workflow = _read_repo_file(workflow_path)
        classify_step = _read_workflow_step_run(
            workflow,
            "Classify Modal result"
            if workflow_path.endswith("linux-fast-modal.yml")
            else "Classify offload result",
        )

        assert "scripts/ci/classify_offload_result.py" in classify_step
        assert f"--lane {lane}" in classify_step
        assert policy in classify_step
        assert "is_offload_prepare_failure()" not in workflow
        assert "grep -Eq" not in workflow

    assert "Failed to create sandboxes" in classifier
    assert "Failed to execute command: Create command failed" in classifier
    assert "Failed to spawn: .*modal_sandbox" in classifier
    assert "Failed to discover tests" in classifier
    assert "pytest --collect-only failed" in classifier
    assert "No module named pytest" in classifier
    assert "classification=" in classifier
    assert "failed_phase=" in classifier
    assert "diagnostic=" in classifier


def test_modal_run_steps_defer_status_to_classifier() -> None:
    """Allows SQLite infra fallback while still failing classified test errors."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)
        run_step = _read_workflow_step_run(workflow, "Run tests via offload")

        assert "continue-on-error: true" not in run_step
        assert 'echo "exit_code=$exit_code" >> "$GITHUB_OUTPUT"' in run_step
        assert 'exit "$exit_code"' not in run_step
        assert 'touch -d "2000-01-01 00:00:00 UTC" "$junit_file"' in run_step


def test_server_workflow_passes_credentials_and_restores_offload_config() -> (
    None
):
    """Keeps the REST server lane strict without surprising cache hashes."""
    workflow = _read_repo_file(
        ".github/workflows/linux-modal-server-mysql.yml"
    )
    run_step = _read_workflow_step_run(workflow, "Run tests via offload")

    assert (
        "ZENML_MODAL_SERVER_URL: ${{ steps.provision.outputs.server_url }}"
        in workflow
    )
    assert (
        "ZENML_MODAL_SERVER_USERNAME: ${{ steps.provision.outputs.server_username }}"
        in workflow
    )
    assert (
        "ZENML_MODAL_SERVER_PASSWORD: ${{ steps.provision.outputs.server_password }}"
        in workflow
    )
    assert 'original_offload="$(mktemp)"' in run_step
    assert "trap finish_run EXIT" in run_step
    assert "cp offload-modal-server-mysql.toml offload.toml" in run_step
    assert 'cp "$original_offload" offload.toml' in run_step


def test_modal_workflows_emit_timing_manifests_in_uploaded_dirs() -> None:
    """Ensures PR1 observability manifests are uploaded with lane artifacts."""
    workflow_expectations = {
        ".github/workflows/linux-fast-modal.yml": (
            "modal-sqlite-fast-ci",
            ("modal_prepare", "test_execution", "classification"),
        ),
        ".github/workflows/linux-modal-server-mysql.yml": (
            "modal-server-rest-mysql-ci",
            (
                "modal_prepare",
                "server_provision",
                "test_execution",
                "classification",
                "teardown",
            ),
        ),
    }

    for workflow_path, (lane, phase_names) in workflow_expectations.items():
        workflow = _read_repo_file(workflow_path)
        manifest_step = _read_workflow_step_run(
            workflow, "Emit timing manifest"
        )

        assert "scripts/ci/emit_timing_manifest.py" in manifest_step
        assert f"--lane {lane}" in manifest_step
        assert f"--output-dir test-results/{lane}" in manifest_step
        assert f"--junit-file test-results/{lane}/junit.xml" in manifest_step
        assert "--modal-infra-failed" in manifest_step
        assert "--test-failed" in manifest_step
        assert "--harness-failed" in manifest_step
        assert "--junit-cache-safe" in manifest_step
        assert (
            f"--offload-log test-results/{lane}/offload.log" in manifest_step
        )
        assert f"path: test-results/{lane}/**" in workflow
        for phase_name in phase_names:
            assert f'--phase "{phase_name}=' in manifest_step
        assert (
            "exit_${{ steps.run.outputs.exit_code || 'missing' }}"
            in manifest_step
        )
