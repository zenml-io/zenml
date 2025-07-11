#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of a Modal orchestrator."""

import asyncio
import os
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterator,
    Optional,
    Type,
    cast,
)
from uuid import uuid4

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalExecutionMode,
)
from zenml.integrations.modal.orchestrators.modal_sandbox_executor import (
    ModalSandboxExecutor,
)
from zenml.integrations.modal.utils import (
    ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID,
    create_modal_stack_validator,
    setup_modal_client,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.stack import Stack, StackValidator

if TYPE_CHECKING:
    from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
        ModalOrchestratorConfig,
        ModalOrchestratorSettings,
    )
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse

logger = get_logger(__name__)


class ModalOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running entire pipelines on Modal.

    This orchestrator runs complete pipelines using Modal sandboxes
    for maximum flexibility and efficiency with persistent app architecture.
    """

    @property
    def config(self) -> "ModalOrchestratorConfig":
        """Returns the Modal orchestrator config.

        Returns:
            The Modal orchestrator config.
        """
        return cast("ModalOrchestratorConfig", self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Modal orchestrator.

        Returns:
            The settings class.
        """
        from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
            ModalOrchestratorSettings,
        )

        return ModalOrchestratorSettings

    def _setup_modal_client(self) -> None:
        """Setup Modal client with authentication."""
        setup_modal_client(
            token_id=self.config.token_id,
            token_secret=self.config.token_secret,
            workspace=self.config.workspace,
            environment=self.config.modal_environment,
        )

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is a container registry and artifact store in the stack.

        Returns:
            A `StackValidator` instance.
        """
        validator: StackValidator = create_modal_stack_validator()
        return validator

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID}."
            )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[Iterator[Dict[str, MetadataType]]]:
        """Runs the complete pipeline using Modal sandboxes.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment.

        Raises:
            Exception: If pipeline execution fails.

        Returns:
            None if the pipeline is executed synchronously, otherwise an iterator of metadata dictionaries.
        """
        if deployment.schedule:
            logger.warning(
                "Modal Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        # Setup Modal authentication
        self._setup_modal_client()

        # Generate orchestrator run ID and include pipeline run ID for isolation
        orchestrator_run_id = str(uuid4())
        environment[ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID] = orchestrator_run_id

        # Pass pipeline run ID for proper isolation
        if placeholder_run:
            environment["ZENML_PIPELINE_RUN_ID"] = str(placeholder_run.id)
            logger.debug(f"Pipeline run ID: {placeholder_run.id}")

        logger.debug(f"Orchestrator run ID: {orchestrator_run_id}")

        # Get settings from pipeline configuration
        settings = cast(
            "ModalOrchestratorSettings", self.get_settings(deployment)
        )

        # Check execution mode
        execution_mode = getattr(
            settings, "execution_mode", ModalExecutionMode.PIPELINE
        )
        logger.info(f"Using execution mode: {execution_mode}")

        # Create sandbox executor
        executor = ModalSandboxExecutor(
            deployment=deployment,
            stack=stack,
            environment=environment,
            settings=settings,
        )

        # Execute pipeline using the executor
        logger.info("Starting pipeline execution with Modal sandboxes")

        try:
            synchronous = (
                settings.synchronous
                if hasattr(settings, "synchronous")
                else self.config.synchronous
            )

            asyncio.run(
                executor.execute_pipeline(
                    orchestrator_run_id=orchestrator_run_id,
                    run_id=str(placeholder_run.id)
                    if placeholder_run
                    else None,
                    synchronous=synchronous,
                )
            )
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise

        logger.info("Pipeline execution completed successfully")
        return None
