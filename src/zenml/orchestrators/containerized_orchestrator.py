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
from typing import List, Optional, Set

import zenml
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.models import PipelineSnapshotBase, PipelineSnapshotResponse
from zenml.orchestrators import BaseOrchestrator


class ContainerizedOrchestrator(BaseOrchestrator, ABC):
    """Base class for containerized orchestrators."""

    @property
    def requirements(self) -> Set[str]:
        """Set of PyPI requirements for the component.

        Returns:
            A set of PyPI requirements for the component.
        """
        requirements = super().requirements

        if self.config.is_local and GlobalConfiguration().uses_sql_store:
            # If we're directly connected to a DB, we need to install the
            # `local` extra in the Docker image to include the DB dependencies.
            requirements.add(f"zenml[local]=={zenml.__version__}")

        return requirements

    @staticmethod
    def get_image(
        snapshot: "PipelineSnapshotResponse",
        step_name: Optional[str] = None,
    ) -> str:
        """Gets the Docker image for the pipeline/a step.

        Args:
            snapshot: The snapshot from which to get the image.
            step_name: Pipeline step name for which to get the image. If not
                given the generic pipeline image will be returned.

        Raises:
            RuntimeError: If the snapshot does not have an associated build.

        Returns:
            The image name or digest.
        """
        if not snapshot.build:
            raise RuntimeError(
                f"Missing build for snapshot {snapshot.id}. This is "
                "probably because the build was manually deleted."
            )

        return snapshot.build.get_image(
            component_key=ORCHESTRATOR_DOCKER_IMAGE_KEY, step=step_name
        )

    def should_build_pipeline_image(
        self, snapshot: "PipelineSnapshotBase"
    ) -> bool:
        """Whether to build the pipeline image.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            Whether to build the pipeline image.
        """
        # When running a dynamic pipeline, we need an image for the
        # orchestration container.
        return snapshot.is_dynamic

    def get_docker_builds(
        self, snapshot: "PipelineSnapshotBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            snapshot: The pipeline snapshot for which to get the builds.

        Returns:
            The required Docker builds.
        """
        pipeline_settings = snapshot.pipeline_configuration.docker_settings

        included_pipeline_build = False
        builds = []

        for name, step in snapshot.step_configurations.items():
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

        if not included_pipeline_build and self.should_build_pipeline_image(
            snapshot
        ):
            pipeline_build = BuildConfiguration(
                key=ORCHESTRATOR_DOCKER_IMAGE_KEY,
                settings=pipeline_settings,
            )
            builds.append(pipeline_build)

        return builds
