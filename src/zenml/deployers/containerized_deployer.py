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
    Set,
    cast,
)

import zenml
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    DEPLOYER_DOCKER_IMAGE_KEY,
)
from zenml.deployers.base_deployer import BaseDeployer
from zenml.deployers.exceptions import DeployerError
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

        The serving image lives on the deployment's snapshot.

        Args:
            deployment: The deployment to get the image for.

        Returns:
            The docker image used to deploy the deployment.

        Raises:
            RuntimeError: if the snapshot has no build or the build has no
                deployer image.
        """
        from zenml.client import Client

        if deployment.snapshot is None:
            raise RuntimeError("Deployment does not have a snapshot.")

        build = (
            Client().get_snapshot(deployment.snapshot.id, hydrate=True).build
        )
        if build is None:
            raise RuntimeError("Deployment snapshot does not have a build.")
        if DEPLOYER_DOCKER_IMAGE_KEY not in build.images:
            raise RuntimeError(
                "Deployment snapshot build does not have a deployer image."
            )
        return build.images[DEPLOYER_DOCKER_IMAGE_KEY].image

    def _validate_snapshot_deployable(
        self,
        snapshot: PipelineSnapshotResponse,
        stack: "Stack",
    ) -> None:
        """Require a serving image in the snapshot built for this deployer.

        The serving image is deployer-specific (it carries the deployer's
        requirements), so a snapshot can only be deployed by the deployer its
        image was built for. The match is checked against the stored image
        settings checksum, which the deployer's requirements feed into.

        Args:
            snapshot: The pipeline snapshot to deploy.
            stack: The stack the snapshot will be deployed on.

        Raises:
            DeployerError: If the snapshot has no serving image, or its image
                was built for a different deployer.
        """
        snapshot_base = cast(PipelineSnapshotBase, snapshot)
        required_builds = self.get_docker_builds(snapshot_base)
        if not required_builds:
            return

        if (
            not snapshot.build
            or DEPLOYER_DOCKER_IMAGE_KEY not in snapshot.build.images
        ):
            raise DeployerError(
                "The snapshot does not contain a serving image. Deploy the "
                "pipeline with `pipeline.deploy(...)` to build one."
            )

        code_repository = None
        if snapshot.code_reference:
            from zenml.code_repositories import BaseCodeRepository

            code_repository = BaseCodeRepository.from_model(
                snapshot.code_reference.code_repository
            )

        expected_checksum = required_builds[0].compute_settings_checksum(
            stack, code_repository=code_repository
        )
        actual_checksum = snapshot.build.get_settings_checksum(
            DEPLOYER_DOCKER_IMAGE_KEY
        )
        if expected_checksum != actual_checksum:
            raise DeployerError(
                "The snapshot's serving image was not built for the deployer "
                f"'{self.name}'. Deploy with the deployer the snapshot was "
                "built for, or build a new snapshot with `pipeline.deploy(...)`."
            )

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
        # are not picked up by `stack.requirements()` when the serving image is
        # built. Inject them here (e.g. the `zenml[local]` extra that provides
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
