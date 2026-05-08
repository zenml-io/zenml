"""Tests for offload cache key computation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from scripts.ci.compute_offload_cache_keys import compute_offload_cache_keys

REQUIRED_FILES = [
    "Dockerfile.ci",
    "Dockerfile.ci.dockerignore",
    "pyproject.toml",
    "scripts/install-zenml-dev.sh",
    "scripts/ci/export_offload_integration_requirements.py",
    "scripts/ci/modal_sandbox_requirements.txt",
    "src/zenml/cli/integration.py",
    "src/zenml/integrations/integration.py",
    "src/zenml/integrations/registry.py",
    "src/zenml/integrations/sklearn/__init__.py",
    "offload.toml",
    "offload-modal-server-mysql.toml",
]


def _copy_key_inputs(tmp_path: Path) -> Path:
    for file_name in REQUIRED_FILES:
        source = Path(file_name)
        destination = tmp_path / file_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path


def _keys(root: Path, lane: str = "default"):
    return compute_offload_cache_keys(
        lane=lane,
        runner_os="Linux",
        python_version="3.13",
        run_id="123",
        run_attempt="1",
        root=root,
    )


def test_image_fingerprint_changes_when_dockerfile_changes(
    tmp_path: Path,
) -> None:
    """Docker image build inputs invalidate the image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    (root / "Dockerfile.ci").write_text("FROM python:3.13\n")

    assert _keys(root).image_key != before


def test_image_fingerprint_changes_when_prepare_command_changes(
    tmp_path: Path,
) -> None:
    """Prepare command changes affect Modal image creation."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    config = root / "offload.toml"
    config.write_text(
        config.read_text().replace("--cached", "--cached --force-build")
    )

    assert _keys(root).image_key != before


def test_image_fingerprint_ignores_create_command_resources(
    tmp_path: Path,
) -> None:
    """Sandbox runtime resources do not invalidate image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    config = root / "offload.toml"
    config.write_text(config.read_text().replace("--cpu 4", "--cpu 8"))

    assert _keys(root).image_key == before


def test_image_fingerprint_ignores_max_parallel(tmp_path: Path) -> None:
    """Scheduling settings do not invalidate image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    config = root / "offload.toml"
    config.write_text(
        config.read_text().replace("max_parallel = 20", "max_parallel = 12")
    )

    assert _keys(root).image_key == before


def test_junit_fingerprint_changes_when_filters_change(
    tmp_path: Path,
) -> None:
    """Duration caches are tied to the selected test set."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).junit_restore_prefix

    config = root / "offload.toml"
    config.write_text(
        config.read_text().replace(
            "tests/integration -m 'not slow'",
            "tests/integration tests/unit -m 'not slow'",
        )
    )

    assert _keys(root).junit_restore_prefix != before


def test_junit_save_key_includes_run_id_and_attempt(tmp_path: Path) -> None:
    """Reruns should not collide with previous duration cache saves."""
    root = _copy_key_inputs(tmp_path)

    first = compute_offload_cache_keys(
        lane="default",
        runner_os="Linux",
        python_version="3.13",
        run_id="123",
        run_attempt="1",
        root=root,
    )
    second = compute_offload_cache_keys(
        lane="default",
        runner_os="Linux",
        python_version="3.13",
        run_id="123",
        run_attempt="2",
        root=root,
    )

    assert first.junit_save_key.endswith("-123-1")
    assert second.junit_save_key.endswith("-123-2")
    assert first.junit_save_key != second.junit_save_key


def test_unsupported_lane_raises_clear_error(tmp_path: Path) -> None:
    """Unknown lanes should fail before producing misleading cache keys."""
    root = _copy_key_inputs(tmp_path)

    with pytest.raises(ValueError, match="Unsupported offload lane"):
        compute_offload_cache_keys(
            lane="postgres",
            runner_os="Linux",
            python_version="3.13",
            run_id="123",
            run_attempt="1",
            root=root,
        )
