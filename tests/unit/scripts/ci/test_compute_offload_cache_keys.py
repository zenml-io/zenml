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
    "offload-default-integration.toml",
    "offload-modal-server-mysql.toml",
    "offload-unit.toml",
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


def test_image_fingerprint_changes_when_exporter_changes(
    tmp_path: Path,
) -> None:
    """Generated integration requirement logic invalidates the image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    exporter = root / "scripts/ci/export_offload_integration_requirements.py"
    exporter.write_text(exporter.read_text() + "\nSUPPLEMENTAL = 'changed'\n")

    assert _keys(root).image_key != before


def test_image_fingerprint_changes_when_generated_requirements_change(
    tmp_path: Path,
) -> None:
    """Generated integration requirements invalidate restored images."""
    root = _copy_key_inputs(tmp_path)
    requirements = root / ".ci/offload/integration-requirements.txt"
    requirements.parent.mkdir(parents=True, exist_ok=True)
    requirements.write_text("pyyaml\n")
    before = _keys(root).image_key

    requirements.write_text("pyyaml\nmaison<2\n")

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
        config.read_text().replace("tests/unit", "tests/unit tests/core")
    )

    assert _keys(root).junit_restore_prefix != before


def test_split_default_lanes_have_separate_duration_caches(
    tmp_path: Path,
) -> None:
    """Unit and integration lanes should not share timing history."""
    root = _copy_key_inputs(tmp_path)

    unit = _keys(root, lane="default-unit")
    integration = _keys(root, lane="default-integration")

    assert unit.junit_restore_prefix.startswith(
        "offload-junit-v2-default-unit-"
    )
    assert integration.junit_restore_prefix.startswith(
        "offload-junit-v2-default-integration-"
    )
    assert unit.junit_restore_prefix != integration.junit_restore_prefix


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
