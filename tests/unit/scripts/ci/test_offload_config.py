"""Tests for offload CI configuration files."""

from __future__ import annotations

from pathlib import Path

import tomllib


def test_fast_offload_config_is_valid() -> None:
    """Default fast offload config has the expected shape."""
    config = tomllib.loads(Path("offload.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert config["groups"]["unit"]["filters"] == "tests/unit"
    assert "tests/integration" in config["groups"]["integration"]["filters"]
    assert "not slow" in config["groups"]["integration"]["filters"]
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment default"
    )


def test_modal_mysql_offload_config_is_valid() -> None:
    """Modal/MySQL offload config targets the remote server environment."""
    config = tomllib.loads(Path("offload-modal-server-mysql.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert config["groups"]["unit"]["filters"] == "tests/unit"
    assert "tests/integration" in config["groups"]["integration"]["filters"]
    assert "not slow" in config["groups"]["integration"]["filters"]
    assert "remote-mysql-modal" in config["framework"]["run_args"]
    assert "MODAL_CI_SERVER_URL" in config["provider"]["create_command"]
