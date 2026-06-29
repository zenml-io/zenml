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
    cast,
)
from uuid import UUID

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
        snapshot: PipelineSnapshotResponse,
        stack: "Stack",
        local_code_available: bool = False,
    ) -> Optional[UUID]:
        """Build the deployer image for the deployment.

        The deployer image is built through the same machinery as any other
        pipeline image. The code is built into the image from the local code
        when deploying directly from local code, otherwise the image is
        code-free and the running container downloads the code from the
        snapshot.

        Args:
            snapshot: The pipeline snapshot to deploy.
            stack: The stack supplying the image builder and container registry.
            local_code_available: Whether the local code can be built into the
                image, set only when deploying directly from local code.

        Raises:
            DeployerError: If the deployment has no code to run.

        Returns:
            The ID of the build containing the deployer image, or None if no
            build is required.
        """
        from zenml.pipelines.build_utils import build_required_images
        from zenml.utils import code_repository_utils

        assert snapshot.stack is not None

        snapshot_base = cast(PipelineSnapshotBase, snapshot)
        required_builds = self.get_docker_builds(snapshot_base)
        if not required_builds:
            return None

        code_repository = None
        if local_code_available:
            local_repo = code_repository_utils.find_active_code_repository()
            if local_repo and not local_repo.has_local_changes:
                code_repository = local_repo.code_repository

        if required_builds[0].should_include_files(
            code_repository=code_repository
        ):
            if not local_code_available:
                raise DeployerError(
                    "The pipeline code must be built into the deployer image, "
                    "but there is no local code to build from. Deploy from "
                    "local code, or use a snapshot whose code is uploaded to "
                    "the artifact store or tracked in a code repository."
                )
        elif not snapshot.code_path and not snapshot.code_reference:
            raise DeployerError(
                "The deployer image does not contain the pipeline code and the "
                "snapshot has no code to download at runtime. Use a snapshot "
                "whose code is uploaded to the artifact store or tracked in a "
                "code repository."
            )

        stack.ensure_image_builder()
        build = build_required_images(
            snapshot=snapshot_base,
            stack=stack,
            stack_model=snapshot.stack,
            required_builds=required_builds,
            project_id=snapshot.project_id,
            pipeline_id=snapshot.pipeline.id,
            code_repository=code_repository,
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
