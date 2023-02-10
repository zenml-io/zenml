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
from typing import List

from zenml.config.build_configuration import BuildConfiguration
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel
from zenml.orchestrators import BaseOrchestrator


class ContainerizedOrchestrator(BaseOrchestrator, ABC):
    """Base class for containerized orchestrators."""

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBaseModel"
    ) -> List["BuildConfiguration"]:
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
