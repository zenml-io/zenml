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
"""Shared utilities for the Modal integration."""

from typing import Dict, Optional, cast

import modal
from modal_proto import api_pb2

from zenml.config.resource_settings import ResourceSettings


def get_gpu_values(
    gpu: Optional[str], resource_settings: ResourceSettings
) -> Optional[str]:
    """Build the Modal ``gpu=`` argument from a GPU type and resource settings.

    Args:
        gpu: The GPU type (for example ``"A100"``), or ``None`` for CPU-only.
        resource_settings: The resource settings for the step.

    Returns:
        The GPU string if a count is specified, otherwise the GPU type.
    """
    if not gpu:
        return None
    gpu_count = resource_settings.gpu_count
    return f"{gpu}:{gpu_count}" if gpu_count else gpu


def build_registry_secret(
    docker_username: str, docker_password: str
) -> "modal.secret._Secret":
    """Build a Modal secret carrying container-registry credentials.

    Args:
        docker_username: Username for the upstream container registry.
        docker_password: Password/token for the upstream container registry.

    Returns:
        A Modal secret exposing ``REGISTRY_USERNAME`` and
        ``REGISTRY_PASSWORD`` environment variables to the sandbox.
    """
    return modal.secret._Secret.from_dict(
        {
            "REGISTRY_USERNAME": docker_username,
            "REGISTRY_PASSWORD": docker_password,
        }
    )


def build_registry_image(
    image_name: str,
    registry_secret: "modal.secret._Secret",
    environment: Dict[str, str],
) -> "modal.Image":
    """Wrap a pre-built container image as a Modal image with static auth.

    Args:
        image_name: Fully-qualified image reference (``repo/name:tag``).
        registry_secret: Modal secret carrying registry credentials.
        environment: Environment variables baked into the sandbox.

    Returns:
        A ``modal.Image`` ready to be passed to ``modal.Sandbox.create``.
    """
    spec = modal.image.DockerfileSpec(
        commands=[f"FROM {image_name}"], context_files={}
    )
    image = modal.Image._from_args(
        dockerfile_function=lambda *_, **__: spec,
        force_build=False,
        image_registry_config=modal.image._ImageRegistryConfig(
            api_pb2.REGISTRY_AUTH_TYPE_STATIC_CREDS, registry_secret
        ),
    ).env(environment)
    return cast(modal.Image, image)
