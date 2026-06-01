"""Tests for offload CI configuration files."""

from __future__ import annotations

from pathlib import Path

import tomllib
import yaml


def _load_config(path: str) -> dict:
    return tomllib.loads(Path(path).read_text())


def _global_state_test_files() -> set[str]:
    """Return integration test files that contain global-state tests."""
    return {
        path.as_posix()
        for path in Path("tests/integration").rglob("test_*.py")
        if "global_state" in path.read_text()
    }


def test_fast_offload_config_is_valid() -> None:
    """Default fast offload config has the expected shape."""
    config = _load_config("offload.toml")

    assert config["offload"]["max_parallel"] == 20
    assert config["offload"]["max_batch_duration_secs"] == 320
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert "tests/unit" in config["groups"]["unit"]["filters"]
    assert "test_wait_abort_aborts_run" in config["groups"]["unit"]["filters"]
    assert (
        "test_parent_waits_while_child_runs_then_wait_resolves"
        in config["groups"]["unit"]["filters"]
    )
    integration_filters = config["groups"]["integration"]["filters"]
    assert "tests/integration" in integration_filters
    assert "not slow" in integration_filters
    assert "test_xgboost.py::test_example" in integration_filters
    assert "test_lightgbm.py::test_example" in integration_filters
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment default"
    )


def test_split_default_offload_configs_match_original_groups() -> None:
    """Split configs keep the same filters as the combined default config."""
    default_config = _load_config("offload.toml")
    unit_config = _load_config("offload-unit.toml")
    integration_config = _load_config("offload-default-integration.toml")

    for split_config in (unit_config, integration_config):
        assert split_config["offload"] == default_config["offload"]
        assert split_config["provider"] == default_config["provider"]
        assert split_config["framework"] == default_config["framework"]
        assert split_config["report"] == default_config["report"]

    assert set(unit_config["groups"]) == {"unit"}
    assert unit_config["groups"]["unit"] == default_config["groups"]["unit"]
    assert set(integration_config["groups"]) == {"integration"}
    assert (
        integration_config["groups"]["integration"]
        == default_config["groups"]["integration"]
    )


def test_offload_dockerfile_does_not_bake_source_before_dependencies() -> None:
    """Code-only changes should not invalidate the dependency image layer."""
    dockerfile = Path("Dockerfile.ci").read_text()
    dockerignore = Path("Dockerfile.ci.dockerignore").read_text()

    assert "COPY . ." not in dockerfile
    assert "integration-requirements.txt" in dockerfile
    assert "!.ci/offload/integration-requirements.txt" in dockerignore
    assert "!.github/workflows/ci-fast.yml" in dockerignore
    assert "!offload-default-integration.toml" in dockerignore
    assert "!offload-unit.toml" in dockerignore


def test_modal_mysql_offload_config_is_valid() -> None:
    """Modal/MySQL offload config targets the remote server environment."""
    config = _load_config("offload-modal-server-mysql.toml")

    assert config["offload"]["max_parallel"] == 20
    assert config["offload"]["max_batch_duration_secs"] == 320
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"integration"}
    integration_filters = config["groups"]["integration"]["filters"]
    assert "tests/integration" in integration_filters
    assert "--ignore=tests/integration/examples" in integration_filters
    assert "--ignore=tests/integration/functional/cli" in integration_filters
    assert "not slow" in integration_filters
    assert "not global_state" in integration_filters
    assert "test_list_secrets_pagination_and_sorting" in integration_filters
    assert "test_deletion_of_links[True]" in integration_filters
    assert config["framework"]["command"].startswith("python -m pytest")
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment remote-mysql-modal"
    )
    assert "MODAL_CI_SERVER_URL" in config["provider"]["create_command"]
    assert "MODAL_TOKEN_SECRET" not in config["provider"]["create_command"]


def test_fast_ci_serial_modal_mysql_job_restores_excluded_tests() -> None:
    """Serial Modal/MySQL job restores tests excluded from parallel offload."""
    workflow = yaml.safe_load(
        Path(".github/workflows/ci-fast.yml").read_text()
    )
    steps = workflow["jobs"]["modal-mysql-serial-shared-state-tests"]["steps"]
    run_blocks = "\n".join(step.get("run", "") for step in steps)

    assert '-m "global_state and not slow"' in run_blocks
    for path in _global_state_test_files():
        assert path in run_blocks
    assert "test_list_secrets_pagination_and_sorting" in run_blocks
    assert "test_deletion_of_links[True]" in run_blocks
