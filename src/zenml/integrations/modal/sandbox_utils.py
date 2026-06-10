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
import os
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

import modal

from zenml.config.resource_settings import ByteUnit, ResourceSettings
from zenml.constants import ENV_ZENML_STORE_PREFIX
from zenml.enums import ExecutionStatus
from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.modal import MODAL_VOLUME_ARTIFACT_STORE_FLAVOR
from zenml.integrations.modal.flavors.modal_volume_artifact_store_flavor import (
    ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME,
    ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX,
    ModalVolumeArtifactStoreConfig,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY = f"{ENV_ZENML_STORE_PREFIX}API_TOKEN"
SENSITIVE_ZENML_RUNTIME_ENV_KEYS = {SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY}
ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME = "ZENML_MODAL_VOLUME_ENVIRONMENT_NAME"


@dataclass(frozen=True)
class ModalVolumeSandboxMount:
    """Modal Volume mount data for a sandbox."""

    mount_path: str
    volume: "modal.Volume"
    environment: Dict[str, str]

    @property
    def volumes(self) -> Dict[str, "modal.Volume"]:
        """Return the Modal SDK ``volumes`` mapping."""
        return {self.mount_path: self.volume}


@dataclass(frozen=True)
class ModalVolumeMountCacheKey:
    """Cache key for resolved Modal Volume sandbox mounts."""

    volume_name: str
    volume_prefix: str
    mount_path: str
    modal_environment: Optional[str]
    create_if_missing: bool
    modal_client_identity: Optional[int]


@dataclass(frozen=True)
class GpuValidationMessage:
    """Human-readable context for Modal GPU validation errors."""

    settings_field: str
    settings_example: str


DEFAULT_GPU_VALIDATION_MESSAGE = GpuValidationMessage(
    settings_field="ModalStepOperatorSettings.gpu",
    settings_example=(
        "For example with @step(settings={'step_operator': "
        "ModalStepOperatorSettings(gpu='<TYPE>'), 'resources': "
        "ResourceSettings(gpu_count=1)}), or set gpu_count=0 to run on CPU."
    ),
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


class ModalClientFactory:
    """Create and cache explicit Modal clients from lazy token providers."""

    def __init__(
        self,
        *,
        get_token_id: Callable[[], Optional[str]],
        get_token_secret: Callable[[], Optional[str]],
    ) -> None:
        """Initialize the factory without reading token values."""
        self._get_token_id = get_token_id
        self._get_token_secret = get_token_secret
        self._cached_client: Optional["modal.Client"] = None
        self._lock = Lock()

    def get_client(self) -> Optional["modal.Client"]:
        """Get an explicit Modal client when credentials are configured.

        If no credentials are configured, this returns ``None`` so the Modal SDK
        can use its ambient authentication configuration. If credentials are
        configured, the created SDK client is cached until it is closed.
        """
        if (
            self._cached_client is not None
            and not self._cached_client.is_closed()
        ):
            return self._cached_client

        with self._lock:
            if (
                self._cached_client is not None
                and not self._cached_client.is_closed()
            ):
                return self._cached_client

            normalized_token_id = normalize_optional_config_value(
                self._get_token_id()
            )
            normalized_token_secret = normalize_optional_config_value(
                self._get_token_secret()
            )

            if bool(normalized_token_id) != bool(normalized_token_secret):
                raise StackComponentInterfaceError(
                    "Modal token_id and token_secret must be configured "
                    "together."
                )

            if not normalized_token_id or not normalized_token_secret:
                return None

            self._cached_client = modal.Client.from_credentials(
                normalized_token_id, normalized_token_secret
            )
            return self._cached_client


class ModalVolumeMountFactory:
    """Resolve and cache Modal Volume mounts for sandbox creation."""

    def __init__(self) -> None:
        """Initialize the empty mount cache."""
        self._cache: Dict[
            ModalVolumeMountCacheKey, ModalVolumeSandboxMount
        ] = {}
        self._lock = Lock()

    def get_mount(
        self,
        stack: Any,
        *,
        modal_environment: Optional[str],
        modal_client: Optional["modal.Client"],
    ) -> Optional[ModalVolumeSandboxMount]:
        """Get a cached Modal Volume sandbox mount, if configured."""
        config = get_modal_volume_artifact_store_config(stack)
        if config is None:
            return None

        cache_key = ModalVolumeMountCacheKey(
            volume_name=config.volume_name,
            volume_prefix=config.volume_prefix,
            mount_path=config.mount_path,
            modal_environment=modal_environment,
            create_if_missing=config.create_if_missing,
            modal_client_identity=(id(modal_client) if modal_client else None),
        )
        with self._lock:
            if cache_key not in self._cache:
                self._cache[cache_key] = resolve_modal_volume_sandbox_mount(
                    config,
                    modal_environment=modal_environment,
                    modal_client=modal_client,
                )
            return self._cache[cache_key]


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


def stack_uses_modal_volume_artifact_store(stack: Any) -> bool:
    """Check whether a stack uses the Modal Volume artifact-store flavor."""
    artifact_store = getattr(stack, "artifact_store", None)
    if artifact_store is None:
        return False
    return (
        getattr(artifact_store, "flavor", None)
        == MODAL_VOLUME_ARTIFACT_STORE_FLAVOR
    )


def validate_modal_volume_environment_consistency(
    stack: Any,
    *,
    modal_environment: Optional[str],
) -> None:
    """Reject child sandboxes that would mount a different Modal environment."""
    if not stack_uses_modal_volume_artifact_store(stack):
        return

    expected_environment = os.environ.get(
        ENV_ZENML_MODAL_VOLUME_ENVIRONMENT_NAME
    )
    if expected_environment is None:
        return

    current_environment = modal_environment or ""
    if current_environment != expected_environment:
        expected_text = expected_environment or "the default Modal environment"
        current_text = current_environment or "the default Modal environment"
        raise StackComponentInterfaceError(
            "The active stack uses a modal_volume artifact store, so every "
            "sandbox in one run must mount the Volume from the same Modal "
            "environment. The orchestration sandbox uses "
            f"{expected_text}, but this sandbox is configured for "
            f"{current_text}. Remove the step-level Modal environment "
            "override or run with a separate stack."
        )


def get_modal_volume_artifact_store_config(
    stack: Any,
) -> Optional[ModalVolumeArtifactStoreConfig]:
    """Return the active Modal Volume artifact-store config, if any."""
    artifact_store = getattr(stack, "artifact_store", None)
    if artifact_store is None:
        return None
    if not stack_uses_modal_volume_artifact_store(stack):
        return None

    config = artifact_store.config
    if isinstance(config, ModalVolumeArtifactStoreConfig):
        return config
    return ModalVolumeArtifactStoreConfig.model_validate(config)


def resolve_modal_volume_sandbox_mount(
    config: ModalVolumeArtifactStoreConfig,
    *,
    modal_environment: Optional[str],
    modal_client: Optional["modal.Client"],
) -> ModalVolumeSandboxMount:
    """Resolve Modal Volume mount data for an artifact-store config.

    Args:
        config: The Modal Volume artifact-store config.
        modal_environment: Modal environment used by the sandbox.
        modal_client: Explicit Modal client, if one is configured.

    Returns:
        Modal Volume mount data.

    Raises:
        StackComponentInterfaceError: If the Modal Volume cannot be resolved.
    """
    try:
        volume = modal.Volume.from_name(
            config.volume_name,
            environment_name=modal_environment,
            create_if_missing=config.create_if_missing,
            client=modal_client,
        )
    except Exception as e:
        environment_text = modal_environment or "the default Modal environment"
        raise StackComponentInterfaceError(
            "Failed to resolve Modal Volume "
            f"'{config.volume_name}' in {environment_text} for the "
            "modal_volume artifact store. The configured create_if_missing "
            f"value is {config.create_if_missing}. Please create the Volume "
            "in Modal or set create_if_missing=True if ZenML should create it "
            "during Modal sandbox setup. Original Modal SDK error "
            f"({type(e).__name__}): {e}"
        ) from e

    return ModalVolumeSandboxMount(
        mount_path=config.mount_path,
        volume=volume,
        environment={
            ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH: "1",
            ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH: config.mount_path,
            ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME: config.volume_name,
            ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX: config.volume_prefix,
        },
    )


def get_modal_volume_sandbox_mount(
    stack: Any,
    *,
    modal_environment: Optional[str],
    modal_client: Optional["modal.Client"],
) -> Optional[ModalVolumeSandboxMount]:
    """Resolve the active Modal Volume artifact-store mount, if configured."""
    config = get_modal_volume_artifact_store_config(stack)
    if config is None:
        return None
    return resolve_modal_volume_sandbox_mount(
        config,
        modal_environment=modal_environment,
        modal_client=modal_client,
    )


def get_gpu_values(
    settings: ModalSandboxSettings,
    resource_settings: ResourceSettings,
    *,
    gpu_validation_message: GpuValidationMessage = DEFAULT_GPU_VALIDATION_MESSAGE,
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
        gpu_validation_message: Human-readable context for error messages.

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
                f"{gpu_validation_message.settings_field}. "
                f"{gpu_validation_message.settings_example}"
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
    gpu_validation_message: GpuValidationMessage = DEFAULT_GPU_VALIDATION_MESSAGE,
    volumes: Optional[Dict[str, "modal.Volume"]] = None,
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
            gpu_validation_message=gpu_validation_message,
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
    if volumes:
        sandbox_create_kwargs["volumes"] = volumes

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
    gpu_validation_message: GpuValidationMessage = DEFAULT_GPU_VALIDATION_MESSAGE,
    volumes: Optional[Dict[str, "modal.Volume"]] = None,
) -> "modal.Sandbox":
    """Create a Modal sandbox for a ZenML entrypoint command."""
    sandbox_create_kwargs = build_sandbox_create_kwargs(
        app=app,
        image=image,
        settings=settings,
        resource_settings=resource_settings,
        environment=environment,
        modal_client=modal_client,
        gpu_validation_message=gpu_validation_message,
        volumes=volumes,
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
