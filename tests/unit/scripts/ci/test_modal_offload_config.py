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


def test_modal_workflows_use_ci_modal_environment_and_pinned_uv() -> None:
    """Keeps Modal apps in CI and runner uv installs reproducible."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)

        assert "MODAL_ENVIRONMENT: ci" in workflow
        assert "UV_VERSION: 0.8.22" in workflow
        assert (
            'python -m pip install --upgrade "uv==${UV_VERSION}"' in workflow
        )
        assert "pip install --upgrade uv" not in workflow

    integration_workflow = _read_repo_file(
        ".github/workflows/integration-test-fast.yml"
    )
    dockerfile = _read_repo_file("Dockerfile.ci")
    assert "UV_VERSION: 0.8.22" in integration_workflow
    assert 'pip install "uv==${UV_VERSION}"' in integration_workflow
    assert "ARG UV_VERSION=0.8.22" in dockerfile
    assert '"uv==${UV_VERSION}"' in dockerfile


def test_modal_server_teardown_stops_created_app() -> None:
    """Avoids leaving live Modal apps after the server sandbox is torn down."""
    workflow = _read_repo_file(
        ".github/workflows/linux-modal-server-mysql.yml"
    )
    provision_script = _read_repo_file("scripts/ci/provision_modal_server.py")
    teardown_step = _read_workflow_step(workflow, "Teardown Modal server")

    assert '_write_output("app_name", app_name)' in provision_script
    assert "stop_modal_app" in provision_script
    assert "def _stop_modal_app" not in provision_script
    assert '"app",\n            "stop",' in _read_repo_file(
        "tests/harness/deployment/_modal_runtime.py"
    )
    assert "--app-name" in teardown_step
    assert "steps.provision.outputs.app_name" in teardown_step


def test_modal_sqlite_ci_wall_clock_exceeds_offload_timeout() -> None:
    """Keeps GitHub from killing offload before it can report an exit code."""
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


def test_modal_junit_cache_keys_use_canonical_lane_names() -> None:
    """Keeps duration caches isolated by the renamed Modal lanes."""
    sqlite_workflow = _read_repo_file(".github/workflows/linux-fast-modal.yml")
    server_workflow = _read_repo_file(
        ".github/workflows/linux-modal-server-mysql.yml"
    )

    assert "offload-modal-sqlite-fast-ci-junit" in sqlite_workflow
    assert "offload-modal-server-rest-mysql-ci-junit" in server_workflow
    assert "offload-junit-${{ runner.os }}" not in sqlite_workflow
    assert "offload-modal-server-mysql-junit" not in server_workflow


def test_modal_sandbox_context_includes_examples_and_ci_harness_config() -> (
    None
):
    """Keeps Modal payload tests from missing regression-test inputs."""
    dockerignore = _read_repo_file(".dockerignore")

    assert "!examples" in dockerignore
    assert "!examples/**" in dockerignore
    assert "!.github/workflows/**" in dockerignore
    assert "!offload.toml" in dockerignore
    assert "!offload-modal-server-mysql.toml" in dockerignore


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
        classify_step = _read_workflow_step(
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


def test_modal_run_steps_defer_status_to_classifier() -> None:
    """Allows SQLite infra fallback while still failing classified test errors."""
    workflow_paths = (
        ".github/workflows/linux-fast-modal.yml",
        ".github/workflows/linux-modal-server-mysql.yml",
    )

    for workflow_path in workflow_paths:
        workflow = _read_repo_file(workflow_path)
        run_step = _read_workflow_step(workflow, "Run tests via offload")

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
    run_step = _read_workflow_step(workflow, "Run tests via offload")

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
    assert "trap restore_offload_config EXIT" in run_step
    assert "cp offload-modal-server-mysql.toml offload.toml" in run_step
    assert 'cp "$original_offload" offload.toml' in run_step


def test_top_level_fast_ci_uses_valid_paths_and_canonical_jobs() -> None:
    """Replaces the invalid paths-ignore allowlist with valid paths."""
    workflow = _read_repo_file(".github/workflows/ci-fast.yml")

    assert "paths-ignore:" not in workflow
    assert "paths:" in workflow
    assert "examples/**" in workflow
    assert "tests/**" in workflow
    assert "      - zen-dev\n" in workflow
    assert "      - zen-dev/**\n" in workflow
    assert "      - zen-test\n" in workflow
    assert "      - zen-test/**\n" in workflow
    assert "!tests/integration/examples" not in workflow
    assert "  modal-sqlite-fast-ci:" in workflow
    assert "  modal-server-rest-mysql-ci:" in workflow
    assert "  linux-fast-modal:" not in workflow
    assert "ubuntu-latest-modal-server-mysql-integration-test" not in workflow


def test_coverage_xml_script_rejects_stale_reports() -> None:
    """Ensures coverage.xml validation rejects stale artifacts."""
    script = _read_repo_file("scripts/test-coverage-xml.sh")

    assert 'coverage_started_at="$(date +%s)"' in script
    assert '--mtime-after "$coverage_started_at"' in script


def test_offload_report_dirs_and_example_coverage_policy() -> None:
    """Keeps lane report paths canonical and example coverage explicit."""
    sqlite_config = _read_repo_file("offload.toml")
    server_config = _read_repo_file("offload-modal-server-mysql.toml")

    assert 'output_dir = "test-results/modal-sqlite-fast-ci"' in sqlite_config
    assert (
        'output_dir = "test-results/modal-server-rest-mysql-ci"'
        in server_config
    )
    assert "--ignore=tests/integration/examples" not in sqlite_config
    assert "filters = \"tests/integration -m 'not slow'\"" in sqlite_config


def test_generic_integration_dispatch_hides_modal_server_lane() -> None:
    """Keeps the dedicated Modal REST lane out of generic manual choices."""
    workflow = _read_repo_file(".github/workflows/integration-test-fast.yml")
    dispatch_block = workflow.split("  workflow_dispatch:", maxsplit=1)[
        1
    ].split("jobs:", maxsplit=1)[0]

    assert "modal-server-mysql" not in dispatch_block
    assert "test_environment:" in dispatch_block


def test_modal_server_image_context_allowlist_excludes_repo_noise() -> None:
    """Keeps the Modal server image context separate from test payloads."""
    runtime = _read_repo_file("tests/harness/deployment/_modal_runtime.py")

    assert "ALLOWLISTED_SERVER_IMAGE_CONTEXT_FILES" in runtime
    assert "ALLOWLISTED_SERVER_IMAGE_CONTEXT_DIRS" in runtime
    assert "add_local_file" in runtime
    assert "add_local_dir" in runtime
    assert "ignore=list" not in runtime
    assert "uv.lock" not in runtime
    assert "prompt-exports" not in runtime
