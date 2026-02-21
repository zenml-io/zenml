#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utility helpers shared by Modal integration components."""

import inspect
from typing import TYPE_CHECKING, Any, Dict, Optional

from zenml.logger import get_logger

if TYPE_CHECKING:
    import modal

logger = get_logger(__name__)


def get_modal_app(
    app_name: str, create_if_missing: bool = True
) -> "modal.App":
    """Looks up or creates a Modal app.

    Args:
        app_name: Name of the Modal app.
        create_if_missing: Whether to create the app if it is not found.

    Returns:
        A Modal app handle.
    """
    import modal

    lookup = getattr(modal.App, "lookup", None)
    if callable(lookup):
        try:
            lookup_signature = inspect.signature(lookup)
            if "create_if_missing" in lookup_signature.parameters:
                return lookup(app_name, create_if_missing=create_if_missing)
            return lookup(app_name)
        except Exception:
            if not create_if_missing:
                raise
            logger.debug(
                "Falling back to direct Modal app creation for app `%s`.",
                app_name,
                exc_info=True,
            )

    return modal.App(app_name)


def build_modal_image(
    base_image: str,
    env: Optional[Dict[str, str]] = None,
    registry_username: Optional[str] = None,
    registry_password: Optional[str] = None,
) -> "modal.Image":
    """Builds a Modal image from a base image name.

    Args:
        base_image: Base image URI.
        env: Optional environment variables to set in the image.
        registry_username: Optional private registry username.
        registry_password: Optional private registry password.

    Returns:
        A Modal image.
    """
    import modal

    image = None

    if registry_username and registry_password:
        try:
            from modal_proto import api_pb2

            my_secret = modal.secret._Secret.from_dict(
                {
                    "REGISTRY_USERNAME": registry_username,
                    "REGISTRY_PASSWORD": registry_password,
                }
            )
            spec = modal.image.DockerfileSpec(
                commands=[f"FROM {base_image}"], context_files={}
            )
            image = modal.Image._from_args(
                dockerfile_function=lambda *_, **__: spec,
                force_build=False,
                image_registry_config=modal.image._ImageRegistryConfig(
                    api_pb2.REGISTRY_AUTH_TYPE_STATIC_CREDS, my_secret
                ),
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to build Modal image with registry credentials. "
                "Please verify the image registry access configuration."
            ) from e

    if image is None:
        from_registry = getattr(modal.Image, "from_registry", None)
        if callable(from_registry):
            image = from_registry(base_image)
        else:
            spec = modal.image.DockerfileSpec(
                commands=[f"FROM {base_image}"], context_files={}
            )
            image = modal.Image._from_args(
                dockerfile_function=lambda *_, **__: spec,
                force_build=False,
            )

    if env:
        return image.env(env)
    return image


def map_resource_settings(
    cpu: Optional[float],
    memory_mb: Optional[int],
    gpu: Optional[str],
    include_none: bool = False,
) -> Dict[str, Any]:
    """Maps ZenML resources to Modal sandbox resource kwargs.

    Args:
        cpu: Number of CPUs.
        memory_mb: Memory in MB.
        gpu: GPU request.
        include_none: Whether to include keys with `None` values.

    Returns:
        Modal keyword arguments for resource settings.
    """
    kwargs: Dict[str, Any] = {}
    if cpu is not None or include_none:
        kwargs["cpu"] = cpu
    if memory_mb is not None or include_none:
        kwargs["memory"] = memory_mb
    if gpu is not None or include_none:
        kwargs["gpu"] = gpu
    return kwargs
