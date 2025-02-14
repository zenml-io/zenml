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
"""Implementation of the Daytona orchestrator."""

import os
import tempfile
from typing import TYPE_CHECKING, Dict, Optional, Type, cast

from daytona_sdk import (  # type: ignore
    CreateWorkspaceParams,
    Daytona,
    DaytonaConfig,
    WorkspaceResources,
)

from zenml.constants import (
    ENV_ZENML_CUSTOM_SOURCE_ROOT,
    ENV_ZENML_WHEEL_PACKAGE_NAME,
)
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.daytona.flavors.daytona_orchestrator_flavor import (
    DaytonaOrchestratorConfig,
    DaytonaOrchestratorSettings,
)
from zenml.integrations.daytona.orchestrators.daytona_orchestrator_entrypoint_configuration import (
    DaytonaOrchestratorEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.orchestrators import WheeledOrchestrator
from zenml.orchestrators.dag_runner import ThreadedDagRunner
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import Stack, StackValidator
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)

ENV_ZENML_DAYTONA_RUN_ID = "ZENML_DAYTONA_RUN_ID"
DAYTONA_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH = "/home/daytona/zenml"


class DaytonaOrchestrator(WheeledOrchestrator):
    """Orchestrator responsible for running pipelines using the Daytona SDK."""

    @property
    def config(self) -> DaytonaOrchestratorConfig:
        """Returns the `DaytonaOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(DaytonaOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Daytona orchestrator.

        Returns:
            The settings class.
        """
        return DaytonaOrchestratorSettings

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A StackValidator instance.
        """
        return StackValidator(
            required_components=set(),
            custom_validation_function=None,
        )

    @property
    def root_directory(self) -> str:
        """Path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "daytona",
            str(self.id),
        )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> None:
        """Prepare and run the pipeline using Daytona SDK.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            ValueError: If the Daytona API key is not set in the settings.
        """
        settings = cast(
            DaytonaOrchestratorSettings, self.get_settings(deployment)
        )
        if not settings.api_key:
            raise ValueError(
                "Daytona orchestrator requires `api_key` to be set in the settings."
            )

        # Initialize Daytona client
        daytona_config = DaytonaConfig(
            api_key=settings.api_key or "",
            server_url=settings.server_url or "https://daytona.work/api",
            target=settings.target or "us",
        )
        daytona = Daytona(daytona_config)

        # Create a workspace for the pipeline
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )

        logger.info("Creating Daytona workspace...")
        workspace_params = CreateWorkspaceParams(
            language="python",
            id=orchestrator_run_name,
            name=orchestrator_run_name,
            image=settings.image,
            os_user=settings.os_user,
            env_vars=settings.env_vars,
            labels=settings.labels,
            public=settings.public,
            target=settings.target or "us",
            timeout=settings.timeout,
            auto_stop_interval=settings.auto_stop_interval,
        )

        # Add resource configuration if any resource settings are specified
        if any(
            x is not None
            for x in [
                settings.cpu,
                settings.memory,
                settings.disk,
                settings.gpu,
            ]
        ):
            workspace_params.resources = WorkspaceResources(
                cpu=settings.cpu,
                memory=settings.memory,
                disk=settings.disk,
                gpu=settings.gpu,
            )

        workspace = daytona.create(workspace_params)

        # Create a wheel for the package in a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            wheel_path = self.create_wheel(temp_dir=temp_dir)

        # Set up environment variables
        env_vars = environment.copy()
        env_vars[ENV_ZENML_DAYTONA_RUN_ID] = orchestrator_run_name
        env_vars[ENV_ZENML_CUSTOM_SOURCE_ROOT] = (
            DAYTONA_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH
        )
        env_vars[ENV_ZENML_WHEEL_PACKAGE_NAME] = self.package_name

        # Set environment variables in the workspace
        for key, value in env_vars.items():
            workspace.process.exec(
                f"export {key}='{value}'", cwd="/home/daytona"
            )

        # Create the repository directory and set up the environment
        self._setup_workspace(workspace, wheel_path)

        if settings.synchronous:
            # In synchronous mode, run steps directly in the main workspace
            logger.info("Running pipeline synchronously...")
            pipeline_dag = {
                step_name: step.spec.upstream_steps
                for step_name, step in deployment.step_configurations.items()
            }

            def run_step(step_name: str) -> None:
                """Run a pipeline step.

                Args:
                    step_name: Name of the step to run.
                """
                logger.info(f"Running step: {step_name}")
                entrypoint_command = " ".join(
                    StepEntrypointConfiguration.get_entrypoint_command()
                )
                entrypoint_args = " ".join(
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name,
                        deployment_id=deployment.id,
                    )
                )
                command = f"{entrypoint_command} {entrypoint_args}"
                response = workspace.process.exec(
                    command,
                    cwd=DAYTONA_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH,
                )
                logger.info(f"Step {step_name} result: {response.result}")

            ThreadedDagRunner(dag=pipeline_dag, run_fn=run_step).run()
            logger.info("Pipeline execution completed.")
        else:
            # In asynchronous mode, use the orchestrator entrypoint
            logger.info("Running pipeline asynchronously...")
            entrypoint_command = " ".join(
                DaytonaOrchestratorEntrypointConfiguration.get_entrypoint_command()
            )
            entrypoint_args = " ".join(
                DaytonaOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                    run_name=orchestrator_run_name,
                    deployment_id=deployment.id,
                )
            )
            command = f"{entrypoint_command} {entrypoint_args}"
            response = workspace.process.exec(
                f"nohup {command} > pipeline.log 2>&1 &",
                cwd=DAYTONA_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH,
            )
            logger.info(
                "Pipeline started asynchronously. You can check the logs at "
                f"{DAYTONA_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH}/pipeline.log"
            )

    def _setup_workspace(self, workspace, wheel_path: str) -> None:
        """Set up the workspace with required dependencies and code.

        Args:
            workspace: The Daytona workspace to set up.
            wheel_path: Path to the wheel package to install.
        """
        # Create the repository directory
        workspace.process.exec(
            f"mkdir -p {DAYTONA_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH}",
            cwd="/home/daytona",
        )

        # Upload and install the wheel package
        workspace.fs.upload_file(
            f"/home/daytona/{os.path.basename(wheel_path)}",
            open(wheel_path, "rb").read(),
        )

        # Install Python dependencies
        workspace.process.exec("pip install uv", cwd="/home/daytona")
        workspace.process.exec(
            f"uv pip install {os.path.basename(wheel_path)}",
            cwd="/home/daytona",
        )

        # Execute custom commands if any
        settings = cast(DaytonaOrchestratorSettings, self.config)
        for command in settings.custom_commands or []:
            logger.info(f"Executing custom command: {command}")
            response = workspace.process.exec(command, cwd="/home/daytona")
            logger.info(f"Custom command result: {response.result}")

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If no run id exists.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_DAYTONA_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_DAYTONA_RUN_ID}."
            )
