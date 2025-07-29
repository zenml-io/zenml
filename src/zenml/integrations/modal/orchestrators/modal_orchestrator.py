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
    List,
    Optional,
    Type,
    cast,
)

from zenml.config.base_settings import BaseSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalExecutionMode,
)
from zenml.integrations.modal.orchestrators.modal_sandbox_executor import (
    ModalSandboxExecutor,
)
from zenml.integrations.modal.utils import (
    ENV_ZENML_MODAL_ORCHESTRATOR_RUN_ID,
    get_modal_stack_validator,
    setup_modal_client,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.stack import Stack, StackValidator

if TYPE_CHECKING:
    from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
        ModalOrchestratorConfig,
        ModalOrchestratorSettings,
    )
    from zenml.models import (
        PipelineDeploymentBase,
        PipelineDeploymentResponse,
        PipelineRunResponse,
    )

logger = get_logger(__name__)


class ModalOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running entire pipelines on Modal."""

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

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        For Modal orchestrator in PIPELINE mode, per-step images are not allowed
        since the entire pipeline runs in a single sandbox.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.

        Raises:
            ValueError: If PIPELINE mode is used with per-step Docker settings.
        """
        builds = super().get_docker_builds(deployment)

        # Get the execution mode from settings
        settings = cast(
            "ModalOrchestratorSettings", self.get_settings(deployment)
        )
        mode = settings.mode

        # In PIPELINE mode, check if any builds have step-specific configurations
        if mode == ModalExecutionMode.PIPELINE:
            for build in builds:
                if (
                    build.key == ORCHESTRATOR_DOCKER_IMAGE_KEY
                    and build.step_name is not None
                ):
                    raise ValueError(
                        f"Per-step Docker settings are not supported in PIPELINE "
                        f"execution mode. Step '{build.step_name}' has custom Docker "
                        f"settings but will be ignored since the entire pipeline runs "
                        f"in a single sandbox. Either use PER_STEP execution mode or "
                        f"remove step-specific Docker settings."
                    )

        return builds

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
        return get_modal_stack_validator()

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

    def submit_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to Modal for execution.

        This method submits the pipeline to Modal and returns immediately unless
        synchronous execution is configured, in which case it provides a wait
        function in the submission result.

        Args:
            deployment: The pipeline deployment to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment.

        Returns:
            Optional submission result with wait function if synchronous.
        """
        self._setup_modal_client()

        if placeholder_run:
            environment["ZENML_PIPELINE_RUN_ID"] = str(placeholder_run.id)

        # Get settings from pipeline configuration
        settings = cast(
            "ModalOrchestratorSettings", self.get_settings(deployment)
        )

        # Check execution mode
        mode = settings.mode
        logger.info(f"🚀 Executing pipeline with Modal ({mode.lower()} mode)")

        # Create sandbox executor
        executor = ModalSandboxExecutor(
            deployment=deployment,
            stack=stack,
            environment=environment,
            settings=settings,
        )

        run_id = placeholder_run.id if placeholder_run else None

        if settings.synchronous:

            def _wait_for_completion() -> None:
                # TODO: separate this into creating the sandbox, and
                # monitoring/log streaming.
                async def _execute_pipeline() -> None:
                    try:
                        await executor.execute_pipeline(
                            run_id=run_id,
                            synchronous=True,
                        )
                        logger.info(
                            "✅ Pipeline execution completed successfully"
                        )
                    except Exception as e:
                        logger.error(f"Pipeline execution failed: {e}")
                        raise

                asyncio.run(_execute_pipeline())

            return SubmissionResult(wait_for_completion=_wait_for_completion)
        else:

            async def _execute_pipeline() -> None:
                try:
                    await executor.execute_pipeline(
                        run_id=run_id,
                        synchronous=False,
                    )
                    logger.info("✅ Pipeline submitted successfully")
                except Exception as e:
                    logger.error(f"Pipeline submission failed: {e}")
                    raise

            asyncio.run(_execute_pipeline())
            return None
