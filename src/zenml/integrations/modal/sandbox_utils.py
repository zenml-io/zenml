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
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple

import modal

from zenml.config.resource_settings import ByteUnit, ResourceSettings
from zenml.constants import ENV_ZENML_STORE_PREFIX
from zenml.enums import ExecutionStatus
from zenml.exceptions import StackComponentInterfaceError
from zenml.logger import get_logger

logger = get_logger(__name__)

SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY = f"{ENV_ZENML_STORE_PREFIX}API_TOKEN"

# Environment variable names that Modal's SDK reads as ambient authentication.
# Injecting these into a sandbox lets code running inside it call the Modal API
# without a stored ZenML component token or a `~/.modal.toml` config file.
MODAL_TOKEN_ID_ENV_KEY = "MODAL_TOKEN_ID"
MODAL_TOKEN_SECRET_ENV_KEY = "MODAL_TOKEN_SECRET"

SENSITIVE_ZENML_RUNTIME_ENV_KEYS = {
    SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY,
    MODAL_TOKEN_ID_ENV_KEY,
    MODAL_TOKEN_SECRET_ENV_KEY,
}


DEFAULT_GPU_SETTINGS_FIELD = "ModalStepOperatorSettings.gpu"
DEFAULT_GPU_SETTINGS_EXAMPLE = (
    "For example with @step(settings={'step_operator': "
    "ModalStepOperatorSettings(gpu='<TYPE>'), 'resources': "
    "ResourceSettings(gpu_count=1)}), or set gpu_count=0 to run on CPU."
)


class ModalSandboxSettings(Protocol):
    """Fields shared by Modal component settings that describe a sandbox."""

    @property
    def gpu(self) -> Optional[str]:
        """GPU type requested for the sandbox, if any."""
        ...

    @property
    def cloud(self) -> Optional[str]:
        """Cloud provider for the sandbox, if any."""
        ...

    @property
    def region(self) -> Optional[str]:
        """Cloud region for the sandbox, if any."""
        ...

    @property
    def timeout(self) -> int:
        """Maximum sandbox lifetime in seconds."""
        ...


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


def create_modal_client_from_credentials(
    *,
    token_id: Optional[str],
    token_secret: Optional[str],
) -> Optional["modal.Client"]:
    """Create an explicit Modal client from component credentials.

    If no component credentials are configured, this returns ``None`` so the
    Modal SDK can use its ambient authentication configuration. If only one
    credential value is configured, the component configuration is invalid.
    """
    normalized_token_id = normalize_optional_config_value(token_id)
    normalized_token_secret = normalize_optional_config_value(token_secret)

    if bool(normalized_token_id) != bool(normalized_token_secret):
        raise StackComponentInterfaceError(
            "Modal token_id and token_secret must be configured together."
        )

    if not normalized_token_id or not normalized_token_secret:
        return None

    return modal.Client.from_credentials(
        normalized_token_id,
        normalized_token_secret,
    )


def resolve_modal_token_pair(
    *,
    token_id: Optional[str],
    token_secret: Optional[str],
) -> Optional[Tuple[str, str]]:
    """Resolve the Modal token pair to forward into a sandbox.

    The explicitly configured component token is preferred. When it is absent,
    this falls back to Modal's ambient authentication config (``~/.modal.toml``
    or the ``MODAL_TOKEN_ID`` / ``MODAL_TOKEN_SECRET`` environment variables),
    the same source Modal's SDK uses when no explicit client is created.

    Args:
        token_id: Explicitly configured Modal token ID, if any.
        token_secret: Explicitly configured Modal token secret, if any.

    Returns:
        The resolved ``(token_id, token_secret)`` pair, or ``None`` when no
        credentials can be resolved from either source.
    """
    resolved_id = normalize_optional_config_value(token_id)
    resolved_secret = normalize_optional_config_value(token_secret)

    if not resolved_id or not resolved_secret:
        from modal.config import config as modal_config

        ambient_id: Optional[str] = None
        ambient_secret: Optional[str] = None
        try:
            ambient_id = modal_config.get("token_id")  # type: ignore[no-untyped-call, unused-ignore]
            ambient_secret = modal_config.get("token_secret")  # type: ignore[no-untyped-call, unused-ignore]
        except Exception:
            logger.debug(
                "Failed to read ambient Modal token configuration.",
                exc_info=True,
            )

        resolved_id = resolved_id or normalize_optional_config_value(
            ambient_id
        )
        resolved_secret = resolved_secret or normalize_optional_config_value(
            ambient_secret
        )

    if not resolved_id or not resolved_secret:
        return None

    return resolved_id, resolved_secret


def get_modal_image_from_registry(
    image_name: str,
    registry_credentials: Optional[Tuple[str, str]] = None,
) -> "modal.Image":
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
) -> "modal.App":
    """Look up or create a Modal app for Sandbox execution."""
    return modal.App.lookup(
        app_name,
        create_if_missing=True,
        environment_name=modal_environment,
        client=modal_client,
    )


def get_gpu_values(
    settings: ModalSandboxSettings,
    resource_settings: ResourceSettings,
    *,
    gpu_settings_field: str = DEFAULT_GPU_SETTINGS_FIELD,
    gpu_settings_example: str = DEFAULT_GPU_SETTINGS_EXAMPLE,
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
        gpu_settings_field: Settings field name to mention in GPU errors.
        gpu_settings_example: Example configuration to mention in GPU errors.

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
                f"'T4', 'A100') via "
                f"{gpu_settings_field}. "
                f"{gpu_settings_example}"
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

    return f"{gpu_type}:{gpu_count}"


def get_memory_mb(resource_settings: ResourceSettings) -> Optional[int]:
    """Convert ZenML memory resource settings to Modal MiB."""
    memory_mb = resource_settings.get_memory(ByteUnit.MB)
    return math.ceil(memory_mb) if memory_mb is not None else None


def create_runtime_secrets(
    sensitive_environment: Dict[str, Optional[str]],
) -> List["modal.Secret"]:
    """Create Modal secrets for sensitive runtime environment values."""
    if not sensitive_environment:
        return []

    return [modal.Secret.from_dict(sensitive_environment)]


def build_sandbox_create_kwargs(
    *,
    app: "modal.App",
    image: "modal.Image",
    settings: ModalSandboxSettings,
    resource_settings: ResourceSettings,
    environment: Dict[str, str],
    modal_client: Optional["modal.Client"],
    gpu_settings_field: str = DEFAULT_GPU_SETTINGS_FIELD,
    gpu_settings_example: str = DEFAULT_GPU_SETTINGS_EXAMPLE,
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
            gpu_settings_field=gpu_settings_field,
            gpu_settings_example=gpu_settings_example,
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
    app: "modal.App",
    image: "modal.Image",
    settings: ModalSandboxSettings,
    resource_settings: ResourceSettings,
    environment: Dict[str, str],
    modal_client: Optional["modal.Client"],
    gpu_settings_field: str = DEFAULT_GPU_SETTINGS_FIELD,
    gpu_settings_example: str = DEFAULT_GPU_SETTINGS_EXAMPLE,
) -> "modal.Sandbox":
    """Create a Modal sandbox for a ZenML entrypoint command."""
    sandbox_create_kwargs = build_sandbox_create_kwargs(
        app=app,
        image=image,
        settings=settings,
        resource_settings=resource_settings,
        environment=environment,
        modal_client=modal_client,
        gpu_settings_field=gpu_settings_field,
        gpu_settings_example=gpu_settings_example,
    )
    return modal.Sandbox.create(*entrypoint_command, **sandbox_create_kwargs)


def wait_for_sandbox(
    sandbox: "modal.Sandbox", poll_interval: float = 1.0
) -> int:
    """Wait for a Modal sandbox by polling its return code."""
    while True:
        return_code = sandbox.poll()
        if return_code is not None:
            return return_code
        time.sleep(poll_interval)


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
) -> "modal.Sandbox":
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
