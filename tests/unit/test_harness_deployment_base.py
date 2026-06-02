"""Tests for harness deployment helpers."""

import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Generator, Optional

import pytest
from docker import errors as docker_errors

from tests.harness.deployment.base import BaseTestDeployment
from tests.harness.deployment.server_docker_mariadb import (
    ServerDockerComposeMariaDBTestDeployment,
)
from tests.harness.deployment.server_docker_mysql import (
    ServerDockerComposeMySQLTestDeployment,
)
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


def test_build_server_image_uses_current_python_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Harness server images should match the active CI Python version."""
    deployment = _Deployment(SimpleNamespace(name="project"))
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        deployment, "build_image", lambda **kwargs: calls.append(kwargs)
    )

    deployment.build_server_image()

    assert calls[0]["buildargs"] == {
        "PYTHON_VERSION": (
            f"{sys.version_info.major}.{sys.version_info.minor}"
        )
    }


def test_store_config_model_dump_resolves_environment_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modal CI store config serialization should keep resolved credentials."""
    monkeypatch.setenv("MODAL_CI_SERVER_URL", "https://sandbox.example.com")
    monkeypatch.setenv("MODAL_CI_SERVER_USERNAME", "default")
    monkeypatch.setenv("MODAL_CI_SERVER_PASSWORD", "password")

    config = DeploymentStoreConfig(
        url="{{MODAL_CI_SERVER_URL}}",
        username="{{MODAL_CI_SERVER_USERNAME}}",
        password="{{MODAL_CI_SERVER_PASSWORD}}",
    )

    assert config.url == "https://sandbox.example.com"
    assert config.model_dump() == {
        "url": "https://sandbox.example.com",
        "username": "default",
        "password": "password",
    }


@pytest.mark.parametrize(
    "deployment_cls",
    [
        ServerDockerComposeMySQLTestDeployment,
        ServerDockerComposeMariaDBTestDeployment,
    ],
)
def test_docker_compose_server_up_pulls_missing_service_images(
    deployment_cls: type[BaseTestDeployment],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Docker Compose should pull DB images after CI prunes the local cache."""
    deployment = deployment_cls(SimpleNamespace(name="project"))
    compose_calls: list[tuple[str, ...]] = []

    @contextmanager
    def fake_connect() -> Generator[SimpleNamespace, None, None]:
        yield SimpleNamespace(zen_store=object())

    monkeypatch.setattr(
        deployment_cls, "is_running", property(lambda _: False)
    )
    monkeypatch.setattr(
        deployment, "_generate_docker_compose_manifest", lambda: "services: {}"
    )
    monkeypatch.setattr(deployment, "get_runtime_path", lambda: tmp_path)
    monkeypatch.setattr(deployment, "build_server_image", lambda: None)
    monkeypatch.setattr(
        deployment,
        "run_docker_compose",
        lambda *args: compose_calls.append(args),
    )
    monkeypatch.setattr(deployment, "connect", fake_connect)

    deployment.up()

    assert compose_calls == [
        ("up", "--wait", "--detach", "--force-recreate", "--pull", "missing")
    ]
