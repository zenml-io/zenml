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

from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

import modal

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.modal import sandbox_utils
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


class ModalStepOperator(BaseStepOperator):
    """Step operator to run a step on Modal.

    This class defines code that can set up a Modal environment and run
    functions in it.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Modal step operator."""
        super().__init__(*args, **kwargs)
        self._modal_client: Optional["modal.Client"] = None
        self._modal_client_lock = Lock()

    def _get_modal_client(self) -> Optional["modal.Client"]:
        """Get an explicit Modal client when credentials are configured."""
        if (
            self._modal_client is not None
            and not self._modal_client.is_closed()
        ):
            return self._modal_client

        with self._modal_client_lock:
            if (
                self._modal_client is not None
                and not self._modal_client.is_closed()
            ):
                return self._modal_client

            self._modal_client = (
                sandbox_utils.create_modal_client_from_credentials(
                    token_id=self.config.token_id,
                    token_secret=self.config.token_secret,
                )
            )
            return self._modal_client

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
            Exception: If sandbox metadata publication or local metadata update
                fails after sandbox creation. In this case, the sandbox is
                terminated before re-raising the original exception.
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

        if not entrypoint_command:
            raise ValueError(
                "Modal step operator received an empty entrypoint command."
            )

        zenml_image = sandbox_utils.get_modal_image_from_registry(
            image_name,
            stack.container_registry.credentials,
        )
        resource_settings = info.config.resource_settings
        modal_environment = sandbox_utils.normalize_optional_config_value(
            settings.modal_environment
        )
        modal_client = self._get_modal_client()

        app = sandbox_utils.lookup_modal_app(
            f"zenml-{info.step_run_id}-{info.pipeline_step_name}"[:64],
            modal_environment=modal_environment,
            modal_client=modal_client,
        )
        sandbox = sandbox_utils.create_modal_sandbox(
            entrypoint_command,
            app=app,
            image=zenml_image,
            settings=settings,
            resource_settings=resource_settings,
            environment=environment,
            modal_client=modal_client,
        )
        metadata: Dict[str, Any] = {
            STEP_SANDBOX_ID_METADATA_KEY: sandbox.object_id
        }
        if modal_environment:
            metadata[STEP_MODAL_ENVIRONMENT_METADATA_KEY] = modal_environment

        try:
            publish_step_run_metadata(info.step_run_id, {self.id: metadata})
            info.step_run.run_metadata.update(metadata)
        except Exception:
            try:
                sandbox.terminate()
            except Exception:
                logger.exception(
                    "Failed to terminate Modal sandbox '%s' after metadata "
                    "publication failed.",
                    sandbox.object_id,
                )
            raise

    def get_status(self, step_run: "StepRunResponse") -> ExecutionStatus:
        """Gets the status of a submitted Modal sandbox.

        Args:
            step_run: The step run.

        Returns:
            The step status.
        """
        sandbox_id = str(step_run.run_metadata[STEP_SANDBOX_ID_METADATA_KEY])
        modal_client = self._get_modal_client()
        return sandbox_utils.get_sandbox_status(
            sandbox_id, modal_client=modal_client
        )

    def cancel(self, step_run: "StepRunResponse") -> None:
        """Cancels a submitted Modal sandbox.

        Args:
            step_run: The step run.
        """
        sandbox_id = str(step_run.run_metadata[STEP_SANDBOX_ID_METADATA_KEY])
        modal_client = self._get_modal_client()
        sandbox_utils.terminate_sandbox(sandbox_id, modal_client=modal_client)
