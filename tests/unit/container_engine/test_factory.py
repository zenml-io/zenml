#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for :mod:`zenml.container_engines.factory`."""

from unittest.mock import MagicMock

import pytest

from zenml.container_engines.docker_engine import DockerContainerEngine
from zenml.container_engines.factory import (
    check_container_engine,
    get_container_engine,
)
from zenml.container_engines.podman_engine import PodmanContainerEngine
from zenml.enums import ContainerEngineType


def _mock_global_config(
    mocker,
    container_engines: ContainerEngineType | None,
) -> None:
    mock_gc = MagicMock()
    mock_gc.container_engines = container_engines
    mocker.patch(
        "zenml.container_engines.factory.GlobalConfiguration",
        return_value=mock_gc,
    )


def test_get_container_engine_explicit_docker(mocker) -> None:
    """Respects global choice Docker and only probes that engine."""
    _mock_global_config(mocker, ContainerEngineType.DOCKER)
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(True, None),
    )
    spy = mocker.spy(PodmanContainerEngine, "check_availability")
    engine = get_container_engine()
    assert isinstance(engine, DockerContainerEngine)
    spy.assert_not_called()


def test_get_container_engine_explicit_podman(mocker) -> None:
    """Respects global choice Podman."""
    _mock_global_config(mocker, ContainerEngineType.PODMAN)
    mocker.patch.object(
        PodmanContainerEngine,
        "check_availability",
        return_value=(True, None),
    )
    engine = get_container_engine()
    assert isinstance(engine, PodmanContainerEngine)


def test_get_container_engine_explicit_raises_when_unavailable(mocker) -> None:
    """Explicit engine that fails ``check_availability`` raises a clear error."""
    _mock_global_config(mocker, ContainerEngineType.DOCKER)
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(False, "docker daemon not running"),
    )
    with pytest.raises(RuntimeError, match="requested container engine"):
        get_container_engine()


def test_get_container_engine_auto_prefers_docker(mocker) -> None:
    """When unset, Docker is selected if available."""
    _mock_global_config(mocker, None)
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(True, None),
    )
    engine = get_container_engine()
    assert isinstance(engine, DockerContainerEngine)


def test_get_container_engine_auto_falls_back_to_podman(mocker) -> None:
    """When Docker is unavailable, Podman is used if present."""
    _mock_global_config(mocker, None)
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(False, None),
    )
    mocker.patch.object(
        PodmanContainerEngine,
        "check_availability",
        return_value=(True, None),
    )
    engine = get_container_engine()
    assert isinstance(engine, PodmanContainerEngine)


def test_get_container_engine_raises_when_none_available(mocker) -> None:
    """Clear error when neither engine is usable in auto mode."""
    _mock_global_config(mocker, None)
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(False, None),
    )
    mocker.patch.object(
        PodmanContainerEngine,
        "check_availability",
        return_value=(False, None),
    )
    with pytest.raises(RuntimeError, match="No container engine is available"):
        get_container_engine()


def test_get_container_engine_forced_docker(mocker) -> None:
    """``get_container_engine(DOCKER)`` forces Docker regardless of global."""
    _mock_global_config(mocker, ContainerEngineType.PODMAN)
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(True, None),
    )
    engine = get_container_engine(ContainerEngineType.DOCKER)
    assert isinstance(engine, DockerContainerEngine)


def test_check_container_engine_available(mocker) -> None:
    """``check_container_engine`` mirrors the engine's availability."""
    mocker.patch.object(
        DockerContainerEngine,
        "check_availability",
        return_value=(True, None),
    )
    ok, err = check_container_engine(ContainerEngineType.DOCKER)
    assert ok is True
    assert err is None


def test_check_container_engine_unavailable(mocker) -> None:
    """``check_container_engine`` returns the engine's error message."""
    mocker.patch.object(
        PodmanContainerEngine,
        "check_availability",
        return_value=(False, "podman: not found"),
    )
    ok, err = check_container_engine(ContainerEngineType.PODMAN)
    assert ok is False
    assert err == "podman: not found"
