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
"""Resolve the active :class:`ContainerEngine` from global settings."""

from typing import Optional, Tuple, Type

from zenml.config.global_config import GlobalConfiguration
from zenml.container_engines.base import ContainerEngine
from zenml.container_engines.docker_engine import DockerContainerEngine
from zenml.container_engines.podman_engine import PodmanContainerEngine
from zenml.enums import ContainerEngineType

CONTAINER_ENGINE_CLASSES: dict[ContainerEngineType, Type[ContainerEngine]] = {
    ContainerEngineType.DOCKER: DockerContainerEngine,
    ContainerEngineType.PODMAN: PodmanContainerEngine,
}


def get_container_engine(
    engine_type: Optional[ContainerEngineType] = None,
) -> ContainerEngine:
    """Return the configured container engine, or auto-detect.

    Args:
        engine_type: When set, use this engine instead of global configuration
            or auto-detection.

    Returns:
        ContainerEngine: Ready-to-use engine instance.

    Raises:
        RuntimeError: If the requested engine is unavailable or neither
            engine works in auto mode.
    """
    requested = engine_type or GlobalConfiguration().container_engine
    if not requested:
        choices = [ContainerEngineType.DOCKER, ContainerEngineType.PODMAN]
    else:
        choices = [requested]

    error_message: str | None = None
    for candidate in choices:
        engine = CONTAINER_ENGINE_CLASSES[candidate]()
        is_available, error_message = engine.check_availability()
        if is_available:
            return engine

    if requested:
        raise RuntimeError(
            f"The requested container engine {requested} is not available. "
            f"Make sure it is installed and accessible on your system: "
            f"{error_message}"
        )

    raise RuntimeError(
        "No container engine is available. Install and start Docker, or "
        "install Podman."
    )


def check_container_engine(
    engine_type: ContainerEngineType,
) -> Tuple[bool, str | None]:
    """Check whether the container engine is available.

    Args:
        engine_type: Docker or Podman engine to probe.

    Returns:
        Availability flag and, when unavailable, an error message from the
        engine implementation (otherwise ``None``).
    """
    engine = CONTAINER_ENGINE_CLASSES[engine_type]()
    return engine.check_availability()
