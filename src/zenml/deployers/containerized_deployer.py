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
    TYPE_CHECKING,
    List,
    Optional,
    Set,
)
from uuid import UUID

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
    DeploymentResponse,
    PipelineSnapshotBase,
    PipelineSnapshotResponse,
)

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)


class ContainerizedDeployer(BaseDeployer, ABC):
    """Base class for all containerized deployers."""

    @staticmethod
    def get_image(deployment: DeploymentResponse) -> str:
        """Get the docker image used to deploy a deployment.

        Args:
            deployment: The deployment to get the image for.

        Returns:
            The docker image used to deploy the deployment.

        Raises:
            RuntimeError: if the deployment does not have a build or if the
                deployer image is not in the build.
        """
        if deployment.build is None:
            raise RuntimeError("Deployment does not have a build.")
        if DEPLOYER_DOCKER_IMAGE_KEY not in deployment.build.images:
            raise RuntimeError(
                "Deployment build does not have a deployer image."
            )
        return deployment.build.images[DEPLOYER_DOCKER_IMAGE_KEY].image

    def _prepare_deployment_build(
        self,
        deployment: DeploymentResponse,
        snapshot: PipelineSnapshotResponse,
        stack: "Stack",
    ) -> Optional[UUID]:
        """Build the deployer image for the deployment.

        Args:
            deployment: The deployment to build the image for.
            snapshot: The pipeline snapshot to deploy.
            stack: The stack supplying the image builder and container registry.

        Returns:
            The ID of the build containing the deployer image, or None if no
            build is required.
        """
        from zenml.pipelines.build_utils import create_deployer_build

        build = create_deployer_build(
            snapshot=snapshot, stack=stack, deployer=self
        )
        return build.id if build else None

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
        extra_requirements_files = {
            ".zenml_deployment_requirements": deployment_requirements,
        }

        # The deployer is no longer part of the stack, so its own requirements
        # are not picked up by `stack.requirements()` during the deploy-time
        # build. Inject them here (e.g. the `zenml[local]` extra that provides
        # the DB drivers needed for a direct database connection).
        if docker_settings.install_stack_requirements:
            deployer_requirements = sorted(self.requirements)
            if deployer_requirements:
                extra_requirements_files[".zenml_deployer_requirements"] = (
                    deployer_requirements
                )

        return [
            BuildConfiguration(
                key=DEPLOYER_DOCKER_IMAGE_KEY,
                settings=docker_settings,
                extra_requirements_files=extra_requirements_files,
            )
        ]
