#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Containerized orchestrator class."""

from abc import ABC
from typing import List, Optional

from zenml.config.build_configuration import BuildConfiguration
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.models import PipelineDeploymentBase, PipelineDeploymentResponse
from zenml.orchestrators import BaseOrchestrator


class ContainerizedOrchestrator(BaseOrchestrator, ABC):
    """Base class for containerized orchestrators."""

    @staticmethod
    def get_image(
        deployment: "PipelineDeploymentResponse",
        step_name: Optional[str] = None,
    ) -> str:
        """Gets the Docker image for the pipeline/a step.

        Args:
            deployment: The deployment from which to get the image.
            step_name: Pipeline step name for which to get the image. If not
                given the generic pipeline image will be returned.

        Raises:
            RuntimeError: If the deployment does not have an associated build.

        Returns:
            The image name or digest.
        """
        if not deployment.build:
            raise RuntimeError(
                f"Missing build for deployment {deployment.id}. This is "
                "probably because the build was manually deleted."
            )

        return deployment.build.get_image(
            component_key=ORCHESTRATOR_DOCKER_IMAGE_KEY, step=step_name
        )

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        pipeline_settings = deployment.pipeline_configuration.docker_settings

        included_pipeline_build = False
        builds = []

        for name, step in deployment.step_configurations.items():
            step_settings = step.config.docker_settings

            if step_settings != pipeline_settings:
                build = BuildConfiguration(
                    key=ORCHESTRATOR_DOCKER_IMAGE_KEY,
                    settings=step_settings,
                    step_name=name,
                )
                builds.append(build)
            elif not included_pipeline_build:
                pipeline_build = BuildConfiguration(
                    key=ORCHESTRATOR_DOCKER_IMAGE_KEY,
                    settings=pipeline_settings,
                )
                builds.append(pipeline_build)
                included_pipeline_build = True

        return builds
