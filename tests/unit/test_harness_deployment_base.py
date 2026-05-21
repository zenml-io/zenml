"""Tests for harness deployment helpers."""

from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest
from docker import errors as docker_errors

from tests.harness.deployment.base import BaseTestDeployment
from tests.harness.model import DeploymentStoreConfig


class _Deployment(BaseTestDeployment):
    """Minimal concrete deployment for base helper tests."""

    @property
    def is_running(self) -> bool:
        """Return whether the fake deployment is running."""
        return False

    def up(self) -> None:
        """Start the fake deployment."""

    def down(self) -> None:
        """Stop the fake deployment."""

    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Return no store configuration."""
        return None


class _Containers:
    """Fake Docker container collection."""

    def __init__(self) -> None:
        self.requests: list[str] = []
        self.container = object()

    def get(self, name: str) -> object:
        """Return the container only for the Compose v2 name."""
        self.requests.append(name)
        if name == "project-zenml-1":
            return self.container

        raise docker_errors.NotFound("missing")


def test_get_container_accepts_legacy_and_compose_v2_names() -> None:
    """Compose v1 and v2 container names should both be discoverable."""
    deployment = _Deployment(SimpleNamespace(name="project"))
    containers = _Containers()
    deployment._container_engine = SimpleNamespace(
        client=SimpleNamespace(containers=containers)
    )

    container = deployment.get_container(
        "project_zenml_1",
        "project-zenml-1",
    )

    assert container is containers.container
    assert containers.requests == ["project_zenml_1", "project-zenml-1"]


def test_run_docker_compose_uses_project_and_runtime_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Docker Compose commands should be scoped to the deployment project."""
    deployment = _Deployment(SimpleNamespace(name="project"))
    calls: list[tuple[list[str], Path, bool]] = []

    def fake_run(command: list[str], cwd: Path, check: bool) -> None:
        calls.append((command, cwd, check))

    monkeypatch.setattr(
        "tests.harness.deployment.base.subprocess.run",
        fake_run,
    )
    monkeypatch.setattr(deployment, "get_runtime_path", lambda: tmp_path)

    deployment.run_docker_compose("up", "--wait")

    assert calls == [
        (
            [
                "docker",
                "compose",
                "--project-name",
                "project",
                "up",
                "--wait",
            ],
            tmp_path,
            True,
        )
    ]
