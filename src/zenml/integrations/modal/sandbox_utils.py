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
"""Shared Modal Sandbox helpers."""

import math
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

import modal

from zenml.config.resource_settings import ByteUnit, ResourceSettings
from zenml.constants import ENV_ZENML_STORE_PREFIX
from zenml.enums import ExecutionStatus
from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger

logger = get_logger(__name__)

SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY = f"{ENV_ZENML_STORE_PREFIX}API_TOKEN"
SENSITIVE_ZENML_RUNTIME_ENV_KEYS = {SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY}

DEFAULT_GPU_SETTINGS_FIELD = "ModalStepOperatorSettings.gpu"
DEFAULT_GPU_SETTINGS_EXAMPLE = (
    "For example with @step(settings={'step_operator': "
    "ModalStepOperatorSettings(gpu='<TYPE>'), 'resources': "
    "ResourceSettings(gpu_count=1)}), or set gpu_count=0 to run on CPU."
)


def normalize_optional_config_value(value: Optional[str]) -> Optional[str]:
    """Normalize optional string config values."""
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def split_modal_runtime_environment(
    environment: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, Optional[str]]]:
    """Split runtime environment variables into plain and secret values."""
    sandbox_environment: Dict[str, str] = {}
    sensitive_environment: Dict[str, Optional[str]] = {}

    for key, value in environment.items():
        if key in SENSITIVE_ZENML_RUNTIME_ENV_KEYS:
            sensitive_environment[key] = value
        else:
            sandbox_environment[key] = value

    return sandbox_environment, sensitive_environment


def get_modal_client(
    *,
    get_token_id: Callable[[], Optional[str]],
    get_token_secret: Callable[[], Optional[str]],
    get_cached_client: Callable[[], Optional["modal.Client"]],
    set_cached_client: Callable[["modal.Client"], None],
    lock: Lock,
) -> Optional["modal.Client"]:
    """Get an explicit Modal client when credentials are configured.

    If no credentials are configured, this returns ``None`` so the Modal SDK can
    use its ambient authentication configuration. If credentials are configured,
    the created SDK client is cached until it is closed.
    """
    modal_client = get_cached_client()
    if modal_client is not None and not modal_client.is_closed():
        return modal_client

    with lock:
        modal_client = get_cached_client()
        if modal_client is not None and not modal_client.is_closed():
            return modal_client

        normalized_token_id = normalize_optional_config_value(get_token_id())
        normalized_token_secret = normalize_optional_config_value(
            get_token_secret()
        )

        if bool(normalized_token_id) != bool(normalized_token_secret):
            raise StackComponentInterfaceError(
                "Modal token_id and token_secret must be configured together."
            )

        if not normalized_token_id or not normalized_token_secret:
            return None

        modal_client = modal.Client.from_credentials(
            normalized_token_id, normalized_token_secret
        )
        set_cached_client(modal_client)

    return modal_client


def get_modal_image_from_registry(
    image_name: str,
    registry_credentials: Optional[Tuple[str, str]] = None,
) -> Any:
    """Create a Modal image from a registry image name."""
    if registry_credentials:
        docker_username, docker_password = registry_credentials
        registry_secret = modal.Secret.from_dict(
            {
                "REGISTRY_USERNAME": docker_username,
                "REGISTRY_PASSWORD": docker_password,
            }
        )
        return modal.Image.from_registry(image_name, secret=registry_secret)

    return modal.Image.from_registry(image_name)


def lookup_modal_app(
    app_name: str,
    *,
    modal_environment: Optional[str],
    modal_client: Optional["modal.Client"],
) -> Any:
    """Look up or create a Modal app for Sandbox execution."""
    return modal.App.lookup(
        app_name,
        create_if_missing=True,
        environment_name=modal_environment,
        client=modal_client,
    )


def get_gpu_values(
    settings: Any,
    resource_settings: ResourceSettings,
    *,
    settings_gpu_field: str = DEFAULT_GPU_SETTINGS_FIELD,
    settings_example: str = DEFAULT_GPU_SETTINGS_EXAMPLE,
) -> Optional[str]:
    """Compute and validate the Modal ``gpu`` argument string.

    Modal expects GPU resources as either ``None`` (CPU only), a GPU type string
    like ``"A100"`` (implicitly a single GPU), or ``"A100:2"`` when multiple
    GPUs of the same type are requested. Within ZenML, the GPU type is captured
    in Modal component settings while the count lives in
    :class:`~zenml.config.resource_settings.ResourceSettings`. This helper
    reconciles both sources.

    Args:
        settings: Modal component settings describing the GPU type.
        resource_settings: Resource constraints providing the GPU count.
        settings_gpu_field: Human-readable settings field for error messages.
        settings_example: Human-readable settings example for error messages.

    Returns:
        A Modal-compatible GPU specification string or ``None`` when running on
        CPU.

    Raises:
        StackComponentInterfaceError: If the configuration is inconsistent or
            invalid.
    """
    gpu_type = normalize_optional_config_value(settings.gpu)
    gpu_count = resource_settings.gpu_count

    if gpu_type is None:
        if gpu_count is not None and gpu_count > 0:
            raise StackComponentInterfaceError(
                "GPU resources requested (gpu_count > 0) but no GPU type was "
                "specified in Modal settings. Please set a GPU type (e.g., "
                f"'T4', 'A100') via {settings_gpu_field}. "
                f"{settings_example}"
            )
        return None

    if gpu_count == 0:
        logger.warning(
            "Modal GPU type '%s' is configured but ResourceSettings.gpu_count "
            "is 0. Ignoring the GPU type and running on CPU only.",
            gpu_type,
        )
        return None

    if gpu_count is None:
        return gpu_type

    if gpu_count > 0:
        return f"{gpu_type}:{gpu_count}"

    return None


def get_memory_mb(resource_settings: ResourceSettings) -> Optional[int]:
    """Convert ZenML memory resource settings to Modal MiB."""
    memory_mb = resource_settings.get_memory(ByteUnit.MB)
    return math.ceil(memory_mb) if memory_mb is not None else None


def create_runtime_secrets(
    sensitive_environment: Dict[str, Optional[str]],
) -> List[Any]:
    """Create Modal secrets for sensitive runtime environment values."""
    if not sensitive_environment:
        return []

    return [modal.Secret.from_dict(sensitive_environment)]


def build_sandbox_create_kwargs(
    *,
    app: Any,
    image: Any,
    settings: Any,
    resource_settings: ResourceSettings,
    environment: Dict[str, str],
    modal_client: Optional["modal.Client"],
    settings_gpu_field: str = DEFAULT_GPU_SETTINGS_FIELD,
    settings_example: str = DEFAULT_GPU_SETTINGS_EXAMPLE,
) -> Dict[str, Any]:
    """Build keyword arguments for ``modal.Sandbox.create``."""
    sandbox_environment, sensitive_environment = (
        split_modal_runtime_environment(environment)
    )
    runtime_secrets = create_runtime_secrets(sensitive_environment)

    sandbox_create_kwargs: Dict[str, Any] = {
        "app": app,
        "image": image,
        "gpu": get_gpu_values(
            settings,
            resource_settings,
            settings_gpu_field=settings_gpu_field,
            settings_example=settings_example,
        ),
        "cpu": resource_settings.cpu_count,
        "memory": get_memory_mb(resource_settings),
        "cloud": settings.cloud,
        "region": settings.region,
        "timeout": settings.timeout,
        "env": sandbox_environment,
        "client": modal_client,
    }
    if runtime_secrets:
        sandbox_create_kwargs["secrets"] = runtime_secrets

    return sandbox_create_kwargs


def create_modal_sandbox(
    entrypoint_command: List[str],
    *,
    app: Any,
    image: Any,
    settings: Any,
    resource_settings: ResourceSettings,
    environment: Dict[str, str],
    modal_client: Optional["modal.Client"],
    settings_gpu_field: str = DEFAULT_GPU_SETTINGS_FIELD,
    settings_example: str = DEFAULT_GPU_SETTINGS_EXAMPLE,
) -> Any:
    """Create a Modal sandbox for a ZenML entrypoint command."""
    sandbox_create_kwargs = build_sandbox_create_kwargs(
        app=app,
        image=image,
        settings=settings,
        resource_settings=resource_settings,
        environment=environment,
        modal_client=modal_client,
        settings_gpu_field=settings_gpu_field,
        settings_example=settings_example,
    )
    return modal.Sandbox.create(*entrypoint_command, **sandbox_create_kwargs)


def sandbox_status_from_return_code(
    return_code: Optional[int],
) -> ExecutionStatus:
    """Map a Modal sandbox return code to a ZenML execution status."""
    if return_code is None:
        return ExecutionStatus.RUNNING
    if return_code == 0:
        return ExecutionStatus.COMPLETED
    return ExecutionStatus.FAILED


def get_sandbox_by_id(
    sandbox_id: str,
    *,
    modal_client: Optional["modal.Client"],
) -> Any:
    """Reconstruct a Modal sandbox handle by ID."""
    return modal.Sandbox.from_id(sandbox_id, client=modal_client)


def get_sandbox_status(
    sandbox_id: str,
    *,
    modal_client: Optional["modal.Client"],
) -> ExecutionStatus:
    """Get the ZenML execution status for a Modal sandbox."""
    sandbox = get_sandbox_by_id(sandbox_id, modal_client=modal_client)
    return sandbox_status_from_return_code(sandbox.poll())


def terminate_sandbox(
    sandbox_id: str,
    *,
    modal_client: Optional["modal.Client"],
) -> None:
    """Terminate a Modal sandbox by ID."""
    sandbox = get_sandbox_by_id(sandbox_id, modal_client=modal_client)
    sandbox.terminate()
