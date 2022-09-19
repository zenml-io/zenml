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

import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Type

from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.orchestrators.local_docker.local_docker_entrypoint_configuration import (
    RUN_NAME_OPTION,
    LocalDockerEntrypointConfiguration,
)
from zenml.stack import Stack
from zenml.steps import BaseStep
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration

logger = get_logger(__name__)


class LocalDockerOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally using Docker.

    This orchestrator does not allow for concurrent execution of steps and also
    does not support running on a schedule.
    """

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Builds a docker image for the current environment.

        This function also uploads it to a container registry if configured.

        Args:
            pipeline: The pipeline to be deployed.
            stack: The stack to be deployed.
            runtime_configuration: The runtime configuration to be used.
        """
        docker_image_builder = PipelineDockerImageBuilder()
        if stack.container_registry:
            docker_image_builder.build_and_push_docker_image(
                pipeline_name=pipeline.name,
                docker_configuration=pipeline.docker_configuration,
                stack=stack,
                runtime_configuration=runtime_configuration,
            )
        else:
            # If there is no container registry, we only build the image
            target_image_name = (
                f"{pipeline.docker_configuration.target_repository}:"
                f"{pipeline.name}"
            )
            docker_image_builder.build_docker_image(
                target_image_name=target_image_name,
                pipeline_name=pipeline.name,
                docker_configuration=pipeline.docker_configuration,
                stack=stack,
            )
            runtime_configuration["docker_image"] = target_image_name

    @staticmethod
    def _get_volumes(stack: "Stack") -> Dict[str, Dict[str, str]]:
        """Get mount volumes for all necessary local stack components.

        Args:
            stack: The stack on which the pipeline is running.

        Returns:
            List of volumes to mount.
        """
        volumes = {}

        # Add a volume for all local paths of stack components
        for stack_component in stack.components.values():
            local_path = stack_component.local_path
            if not local_path:
                continue

            volumes[local_path] = {"bind": local_path, "mode": "rw"}

        return volumes

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """This method iterates through all steps and executes them in Docker.

        Args:
            sorted_steps: A list of steps in the pipeline.
            pipeline: The pipeline object.
            pb2_pipeline: The pipeline object in protobuf format.
            stack: The stack object.
            runtime_configuration: The runtime configuration object.
        """
        if runtime_configuration.schedule:
            logger.warning(
                "Local Docker Orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )
        assert runtime_configuration.run_name, "Run name must be set"

        from docker.client import DockerClient

        docker_client = DockerClient.from_env()
        image_name = runtime_configuration["docker_image"]
        entrypoint = LocalDockerEntrypointConfiguration.get_entrypoint_command()

        # Run each step
        for step in sorted_steps:
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "Docker orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step.name,
                )

            arguments = (
                LocalDockerEntrypointConfiguration.get_entrypoint_arguments(
                    step=step,
                    pb2_pipeline=pb2_pipeline,
                    **{RUN_NAME_OPTION: runtime_configuration.run_name},
                )
            )
            volumes = self._get_volumes(stack=stack)
            user = None
            if sys.platform != "win32":
                user = os.getuid()
            logger.info("Running step `%s` in Docker:", step.name)
            logs = docker_client.containers.run(
                image=image_name,
                entrypoint=entrypoint,
                command=arguments,
                user=user,
                volumes=volumes,
                stream=True,
            )

            for line in logs:
                logger.info(line.strip().decode())


class LocalDockerOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the local Docker orchestrator."""

    @property
    def name(self) -> str:
        return "local_docker"

    @property
    def implementation_class(self) -> Type["LocalDockerOrchestrator"]:
        return LocalDockerOrchestrator
