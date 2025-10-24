#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the ZenML local Docker orchestrator."""

import copy
import os
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast
from uuid import uuid4

from docker.errors import ContainerError

from zenml.config.base_settings import BaseSettings
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_LOCAL_STORES_PATH,
)
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import ExecutionMode, StackComponentType
from zenml.logger import get_logger
from zenml.orchestrators import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
    ContainerizedOrchestrator,
    SubmissionResult,
)
from zenml.stack import Stack, StackValidator
from zenml.utils import docker_utils, string_utils

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse

logger = get_logger(__name__)

ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID = "ZENML_DOCKER_ORCHESTRATOR_RUN_ID"


class LocalDockerOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines locally using Docker.

    This orchestrator does not allow for concurrent execution of steps and also
    does not support running on a schedule.
    """

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Local Docker orchestrator.

        Returns:
            The settings class.
        """
        return LocalDockerOrchestratorSettings

    @property
    def config(self) -> "LocalDockerOrchestratorConfig":
        """Returns the `LocalDockerOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(LocalDockerOrchestratorConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Ensures there is an image builder in the stack.

        Returns:
            A `StackValidator` instance.
        """
        return StackValidator(
            required_components={StackComponentType.IMAGE_BUILDER}
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        try:
            return os.environ[ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID}."
            )

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to the orchestrator.

        This method should only submit the pipeline and not wait for it to
        complete. If the orchestrator is configured to wait for the pipeline run
        to complete, a function that waits for the pipeline run to complete can
        be passed as part of the submission result.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment shared by all steps. This should
                be set if your orchestrator for example runs one container that
                is responsible for starting all the steps.
            step_environments: Environment variables to set when executing
                specific steps.
            placeholder_run: An optional placeholder run for the snapshot.

        Raises:
            ContainerError: If the pipeline run fails.
            RuntimeError: If the pipeline run fails.

        Returns:
            Optional submission result.
        """
        if snapshot.schedule:
            logger.warning(
                "Local Docker Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        docker_client = docker_utils._try_get_docker_client_from_env()

        entrypoint = StepEntrypointConfiguration.get_entrypoint_command()

        # Add the local stores path as a volume mount
        stack.check_local_paths()
        local_stores_path = GlobalConfiguration().local_stores_path
        volumes = {
            local_stores_path: {
                "bind": local_stores_path,
                "mode": "rw",
            }
        }
        orchestrator_run_id = str(uuid4())
        start_time = time.time()

        execution_mode = snapshot.pipeline_configuration.execution_mode

        failed_steps: List[str] = []
        skipped_steps: List[str] = []

        # Run each step
        for step_name, step in snapshot.step_configurations.items():
            if (
                execution_mode == ExecutionMode.STOP_ON_FAILURE
                and failed_steps
            ):
                logger.warning(
                    "Skipping step %s due to the failed step(s): %s (Execution mode %s)",
                    step_name,
                    ", ".join(failed_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if failed_upstream_steps := [
                fs for fs in failed_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to failure in upstream step(s): %s (Execution mode %s)",
                    step_name,
                    ", ".join(failed_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if skipped_upstream_steps := [
                fs for fs in skipped_steps if fs in step.spec.upstream_steps
            ]:
                logger.warning(
                    "Skipping step %s due to the skipped upstream step(s) %s (Execution mode %s)",
                    step_name,
                    ", ".join(skipped_upstream_steps),
                    execution_mode,
                )
                skipped_steps.append(step_name)
                continue

            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "Docker orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step_name,
                )

            step_environment = step_environments[step_name]
            step_environment[ENV_ZENML_DOCKER_ORCHESTRATOR_RUN_ID] = (
                orchestrator_run_id
            )
            step_environment[ENV_ZENML_LOCAL_STORES_PATH] = local_stores_path

            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, snapshot_id=snapshot.id
            )

            settings = cast(
                LocalDockerOrchestratorSettings,
                self.get_settings(step),
            )
            image = self.get_image(snapshot=snapshot, step_name=step_name)
            image = settings.run_args.pop("image", image)

            user = None
            if sys.platform != "win32":
                user = os.getuid()
            user = settings.run_args.pop("user", user)
            logger.info("Running step `%s` in Docker:", step_name)

            run_args = copy.deepcopy(settings.run_args)
            docker_environment = run_args.pop("environment", {})
            docker_environment.update(step_environment)

            docker_volumes = run_args.pop("volumes", {})
            docker_volumes.update(volumes)

            extra_hosts = run_args.pop("extra_hosts", {})
            extra_hosts["host.docker.internal"] = "host-gateway"

            try:
                logs = docker_client.containers.run(
                    image=image,
                    entrypoint=entrypoint,
                    command=arguments,
                    user=user,
                    volumes=docker_volumes,
                    environment=docker_environment,
                    stream=True,
                    extra_hosts=extra_hosts,
                    **run_args,
                )

                for line in logs:
                    logger.info(line.strip().decode())
            except ContainerError as e:
                error_message = e.stderr.decode()
                failed_steps.append(step_name)
                if execution_mode == ExecutionMode.FAIL_FAST:
                    raise
                else:
                    logger.error(error_message)

        if failed_steps:
            raise RuntimeError(
                "Pipeline run has failed due to failure in step(s): "
                f"{', '.join(failed_steps)}"
            )

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
        return None

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Supported execution modes for this orchestrator.

        Returns:
            Supported execution modes for this orchestrator.
        """
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]


class LocalDockerOrchestratorSettings(BaseSettings):
    """Local Docker orchestrator settings.

    Attributes:
        run_args: Arguments to pass to the `docker run` call. (See
            https://docker-py.readthedocs.io/en/stable/containers.html for a list
            of what can be passed.)
    """

    run_args: Dict[str, Any] = {}


class LocalDockerOrchestratorConfig(
    BaseOrchestratorConfig, LocalDockerOrchestratorSettings
):
    """Local Docker orchestrator config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return True


class LocalDockerOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the local Docker orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return "local_docker"

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/docker.png"

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return LocalDockerOrchestratorConfig

    @property
    def implementation_class(self) -> Type["LocalDockerOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        return LocalDockerOrchestrator
