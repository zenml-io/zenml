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
"""Modal step operator implementation."""

import math
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

import modal

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.resource_settings import ByteUnit, ResourceSettings
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.exceptions import StackComponentInterfaceError
from zenml.integrations.modal.flavors import (
    ModalStepOperatorConfig,
    ModalStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators.publish_utils import publish_step_run_metadata
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineSnapshotBase, StepRunResponse

logger = get_logger(__name__)

MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY = "modal_step_operator"
STEP_SANDBOX_ID_METADATA_KEY = "sandbox_id"
STEP_MODAL_ENVIRONMENT_METADATA_KEY = "modal_environment"


def _normalize_optional_config_value(value: Optional[str]) -> Optional[str]:
    """Normalize optional string config values."""
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def get_gpu_values(
    settings: ModalStepOperatorSettings, resource_settings: ResourceSettings
) -> Optional[str]:
    """Compute and validate the Modal ``gpu`` argument string.

    Modal expects GPU resources as either ``None`` (CPU only), a GPU type string
    like ``"A100"`` (implicitly a single GPU), or ``"A100:2"`` when multiple
    GPUs of the same type are requested. Within ZenML, the GPU type is captured
    in :class:`ModalStepOperatorSettings` while the count lives in
    :class:`~zenml.config.resource_settings.ResourceSettings`. This helper
    reconciles both sources.

    Args:
        settings: The Modal step operator settings describing the GPU type.
        resource_settings: Resource constraints for the step, providing the GPU count.

    Returns:
        A Modal-compatible GPU specification string or ``None`` when running on CPU.

    Raises:
        StackComponentInterfaceError: If the configuration is inconsistent or invalid.
    """
    gpu_type_raw = settings.gpu
    gpu_type = gpu_type_raw.strip() if gpu_type_raw is not None else None
    if gpu_type == "":
        gpu_type = None

    gpu_count = resource_settings.gpu_count
    if gpu_count is not None:
        try:
            gpu_count = int(gpu_count)
        except (TypeError, ValueError):
            raise StackComponentInterfaceError(
                f"Invalid GPU count '{gpu_count}'. Must be a non-negative integer."
            )
        if gpu_count < 0:
            raise StackComponentInterfaceError(
                f"Invalid GPU count '{gpu_count}'. Must be >= 0."
            )

    if gpu_type is None:
        if gpu_count is not None and gpu_count > 0:
            raise StackComponentInterfaceError(
                "GPU resources requested (gpu_count > 0) but no GPU type was specified "
                "in Modal settings. Please set a GPU type (e.g., 'T4', 'A100') via "
                "ModalStepOperatorSettings.gpu or @step(settings={'modal': {'gpu': '<TYPE>'}}), "
                "or set gpu_count=0 to run on CPU."
            )
        return None

    if gpu_count == 0:
        logger.warning(
            "Modal GPU type '%s' is configured but ResourceSettings.gpu_count is 0. "
            "Ignoring the GPU type and running on CPU only.",
            gpu_type,
        )
        return None

    if gpu_count is None:
        return gpu_type

    if gpu_count > 0:
        return f"{gpu_type}:{gpu_count}"

    return None


class ModalStepOperator(BaseStepOperator):
    """Step operator to run a step on Modal.

    This class defines code that can set up a Modal environment and run
    functions in it.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Modal step operator."""
        super().__init__(*args, **kwargs)
        self._modal_client: Optional["modal.Client"] = None
        self._modal_client_lock = threading.Lock()

    def _get_modal_client(self) -> Optional["modal.Client"]:
        """Get an explicit Modal client when credentials are configured."""
        token_id = _normalize_optional_config_value(self.config.token_id)
        token_secret = _normalize_optional_config_value(
            self.config.token_secret
        )

        if bool(token_id) != bool(token_secret):
            raise StackComponentInterfaceError(
                "Modal token_id and token_secret must be configured together."
            )

        if not token_id or not token_secret:
            return None

        with self._modal_client_lock:
            modal_client = self._modal_client
            if modal_client is None or modal_client.is_closed():
                modal_client = modal.Client.from_credentials(
                    token_id, token_secret
                )
                self._modal_client = modal_client

        return modal_client

    @property
    def config(self) -> ModalStepOperatorConfig:
        """Get the Modal step operator configuration.

        Returns:
            The Modal step operator configuration.
        """
        return cast(ModalStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Get the settings class for the Modal step operator.

        Returns:
            The Modal step operator settings class.
        """
        return ModalStepOperatorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Get the stack validator for the Modal step operator.

        Returns:
            The stack validator.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Modal step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Modal "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Modal step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Modal step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Get the Docker build configurations for the Modal step operator.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A list of Docker build configurations.
        """
        builds = []
        for step_name, step in snapshot.step_configurations.items():
            if step.config.uses_step_operator(self.name):
                build = BuildConfiguration(
                    key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                )
                builds.append(build)

        return builds

    def submit(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Submits a step run to Modal.

        Args:
            info: The step run information.
            entrypoint_command: The entrypoint command for the step.
            environment: The environment variables for the step.

        Raises:
            ValueError: If no container registry is found in the stack or the
                entrypoint command is empty.
        """
        settings = cast(ModalStepOperatorSettings, self.get_settings(info))
        image_name = info.get_image(key=MODAL_STEP_OPERATOR_DOCKER_IMAGE_KEY)
        zc = Client()
        stack = zc.active_stack

        if not stack.container_registry:
            raise ValueError(
                "No Container registry found in the stack. "
                "Please add a container registry and ensure "
                "it is correctly configured."
            )

        if docker_creds := stack.container_registry.credentials:
            docker_username, docker_password = docker_creds
            registry_secret = modal.Secret.from_dict(
                {
                    "REGISTRY_USERNAME": docker_username,
                    "REGISTRY_PASSWORD": docker_password,
                }
            )
            zenml_image = modal.Image.from_registry(
                image_name, secret=registry_secret
            )
        else:
            zenml_image = modal.Image.from_registry(image_name)

        resource_settings = info.config.resource_settings
        gpu_values = get_gpu_values(settings, resource_settings)
        memory_mb = resource_settings.get_memory(ByteUnit.MB)
        memory_int = math.ceil(memory_mb) if memory_mb is not None else None

        if not entrypoint_command:
            raise ValueError(
                "Modal step operator received an empty entrypoint command."
            )

        modal_environment = _normalize_optional_config_value(
            settings.modal_environment
        )
        modal_client = self._get_modal_client()

        app = modal.App.lookup(
            f"zenml-{info.step_run_id}-{info.pipeline_step_name}"[:64],
            create_if_missing=True,
            environment_name=modal_environment,
            client=modal_client,
        )
        sandbox_environment: Dict[str, Optional[str]] = dict(environment)
        sandbox = modal.Sandbox.create(
            *entrypoint_command,
            app=app,
            image=zenml_image,
            gpu=gpu_values,
            cpu=resource_settings.cpu_count,
            memory=memory_int,
            cloud=settings.cloud,
            region=settings.region,
            timeout=settings.timeout,
            env=sandbox_environment,
            client=modal_client,
        )
        metadata: Dict[str, Any] = {
            STEP_SANDBOX_ID_METADATA_KEY: sandbox.object_id
        }
        if modal_environment:
            metadata[STEP_MODAL_ENVIRONMENT_METADATA_KEY] = modal_environment

        publish_step_run_metadata(info.step_run_id, {self.id: metadata})
        info.step_run.run_metadata.update(metadata)

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Gets the status of a submitted Modal sandbox.

        Args:
            step_run: The step run.

        Returns:
            The step status.
        """
        sandbox_id = str(step_run.run_metadata[STEP_SANDBOX_ID_METADATA_KEY])
        modal_client = self._get_modal_client()
        sandbox = modal.Sandbox.from_id(sandbox_id, client=modal_client)
        return_code = sandbox.poll()
        if return_code is None:
            return ExecutionStatus.RUNNING
        if return_code == 0:
            return ExecutionStatus.COMPLETED
        return ExecutionStatus.FAILED

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancels a submitted Modal sandbox.

        Args:
            step_run: The step run.
        """
        sandbox_id = str(step_run.run_metadata[STEP_SANDBOX_ID_METADATA_KEY])
        modal_client = self._get_modal_client()
        sandbox = modal.Sandbox.from_id(sandbox_id, client=modal_client)
        sandbox.terminate()
