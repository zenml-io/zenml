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


def _read_workflow_step(workflow: str, step_name: str) -> str:
    return workflow.split(
        f"      - name: {step_name}\n",
        maxsplit=1,
    )[1].split("      - name:", maxsplit=1)[0]


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
    assert "--env ZENML_TEST_ISOLATE_PROJECT=true" in wrapper


def test_modal_workflows_use_ci_modal_environment() -> None:
    """Keeps CI-created Modal apps and sandboxes in the CI environment."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)

        assert "MODAL_ENVIRONMENT: ci" in workflow


def test_modal_server_teardown_stops_created_app() -> None:
    """Avoids leaving live Modal apps after the server sandbox is torn down."""
    workflow = _read_repo_file(
        ".github/workflows/linux-modal-server-mysql.yml"
    )
    provision_script = _read_repo_file("scripts/ci/provision_modal_server.py")
    teardown_step = _read_workflow_step(workflow, "Teardown Modal server")

    assert '_write_output("app_name", app_name)' in provision_script
    assert '"app",\n        "stop",' in provision_script
    assert "--app-name" in teardown_step
    assert "steps.provision.outputs.app_name" in teardown_step


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
        restore_step = workflow.split(
            "      - name: Restore offload image cache\n", maxsplit=1
        )[1].split("      - name:", maxsplit=1)[0]

        assert "path: .offload-image-cache" in restore_step
        for cache_key_file in cache_key_files:
            assert cache_key_file in restore_step
        assert "restore-keys: |" in restore_step
        assert fallback_key in restore_step


def test_modal_sandbox_context_includes_ci_harness_config() -> None:
    """Keeps Modal payload tests from missing CI regression-test inputs."""
    dockerignore = _read_repo_file(".dockerignore")

    assert "!.github/workflows/**" in dockerignore
    assert "!offload.toml" in dockerignore
    assert "!offload-modal-server-mysql.toml" in dockerignore


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


def test_modal_run_steps_fail_visibly_for_real_test_failures() -> None:
    """Avoids hiding failed offload runs behind continue-on-error."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)
        run_step = _read_workflow_step(workflow, "Run tests via offload")

        assert "continue-on-error: true" not in run_step
        assert 'echo "exit_code=$exit_code" >> "$GITHUB_OUTPUT"' in run_step
        assert 'exit "$exit_code"' in run_step

    fast_run_step = _read_workflow_step(
        _read_repo_file(".github/workflows/linux-fast-modal.yml"),
        "Run tests via offload",
    )

    assert "modal_infra_failed=true" in fast_run_step
    assert "falling back to standard CI" in fast_run_step
