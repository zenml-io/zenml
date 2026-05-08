"""Tests for offload CI configuration files."""

from __future__ import annotations

from pathlib import Path

import tomllib


def test_fast_offload_config_is_valid() -> None:
    """Default fast offload config has the expected shape."""
    config = tomllib.loads(Path("offload.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["offload"]["max_batch_duration_secs"] == 320
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert config["groups"]["unit"]["filters"] == "tests/unit"
    assert "tests/integration" in config["groups"]["integration"]["filters"]
    assert "not slow" in config["groups"]["integration"]["filters"]
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment default"
    )


def test_offload_dockerfile_does_not_bake_source_before_dependencies() -> None:
    """Code-only changes should not invalidate the dependency image layer."""
    dockerfile = Path("Dockerfile.ci").read_text()
    dockerignore = Path("Dockerfile.ci.dockerignore").read_text()

    assert "COPY . ." not in dockerfile
    assert "integration-requirements.txt" in dockerfile
    assert "!.ci/offload/integration-requirements.txt" in dockerignore


def test_modal_mysql_offload_config_is_valid() -> None:
    """Modal/MySQL offload config targets the remote server environment."""
    config = tomllib.loads(Path("offload-modal-server-mysql.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["offload"]["max_batch_duration_secs"] == 320
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"integration"}
    assert "tests/integration" in config["groups"]["integration"]["filters"]
    assert "not slow" in config["groups"]["integration"]["filters"]
    assert "not global_state" in config["groups"]["integration"]["filters"]
    assert config["framework"]["command"].startswith("python -m pytest")
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment remote-mysql-modal"
    )
    assert "MODAL_CI_SERVER_URL" in config["provider"]["create_command"]
