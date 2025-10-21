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
"""Base class for all containerized deployers."""

from abc import ABC
from typing import (
    List,
    Set,
)

import zenml
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    DEPLOYER_DOCKER_IMAGE_KEY,
)
from zenml.deployers.base_deployer import BaseDeployer
from zenml.deployers.utils import load_deployment_requirements
from zenml.logger import get_logger
from zenml.models import (
    PipelineSnapshotBase,
    PipelineSnapshotResponse,
)

logger = get_logger(__name__)


class ContainerizedDeployer(BaseDeployer, ABC):
    """Base class for all containerized deployers."""

    @staticmethod
    def get_image(snapshot: PipelineSnapshotResponse) -> str:
        """Get the docker image used to deploy a pipeline snapshot.

        Args:
            snapshot: The pipeline snapshot to get the image for.

        Returns:
            The docker image used to deploy the pipeline snapshot.

        Raises:
            RuntimeError: if the pipeline snapshot does not have a build or
                if the deployer image is not in the build.
        """
        if snapshot.build is None:
            raise RuntimeError("Pipeline snapshot does not have a build. ")
        if DEPLOYER_DOCKER_IMAGE_KEY not in snapshot.build.images:
            raise RuntimeError(
                "Pipeline snapshot build does not have a deployer image. "
            )
        return snapshot.build.images[DEPLOYER_DOCKER_IMAGE_KEY].image

    @property
    def requirements(self) -> Set[str]:
        """Set of PyPI requirements for the deployer.

        Returns:
            A set of PyPI requirements for the deployer.
        """
        requirements = super().requirements

        if self.config.is_local and GlobalConfiguration().uses_sql_store:
            # If we're directly connected to a DB, we need to install the
            # `local` extra in the Docker image to include the DB dependencies.
            requirements.add(f"zenml[local]=={zenml.__version__}")

        return requirements

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            snapshot: The pipeline snapshot for which to get the builds.

        Returns:
            The required Docker builds.
        """
        deployment_settings = (
            snapshot.pipeline_configuration.deployment_settings
        )
        docker_settings = snapshot.pipeline_configuration.docker_settings
        if not docker_settings.install_deployment_requirements:
            return []

        deployment_requirements = load_deployment_requirements(
            deployment_settings
        )
        return [
            BuildConfiguration(
                key=DEPLOYER_DOCKER_IMAGE_KEY,
                settings=snapshot.pipeline_configuration.docker_settings,
                extra_requirements_files={
                    ".zenml_deployment_requirements": deployment_requirements,
                },
            )
        ]
