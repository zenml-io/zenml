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
"""Build configuration class."""

import hashlib
from typing import TYPE_CHECKING, Dict, Optional

from pydantic import BaseModel

from zenml.config.docker_settings import DockerSettings, SourceFileMode

if TYPE_CHECKING:
    from zenml.code_repositories import BaseCodeRepository
    from zenml.stack import Stack


class BuildConfiguration(BaseModel):
    """Configuration of Docker builds.

    Attributes:
        key: The key to store the build.
        settings: Settings for the build.
        step_name: Name of the step for which this image will be built.
        entrypoint: Optional entrypoint for the image.
        extra_files: Extra files to include in the Docker image.
    """

    key: str
    settings: DockerSettings
    step_name: Optional[str] = None
    entrypoint: Optional[str] = None
    extra_files: Dict[str, str] = {}

    def compute_settings_checksum(
        self,
        stack: "Stack",
        code_repository: Optional["BaseCodeRepository"] = None,
    ) -> str:
        """Checksum for all build settings.

        Args:
            stack: The stack for which to compute the checksum. This is needed
                to gather the stack integration requirements in case the
                Docker settings specify to install them.
            code_repository: Optional code repository that will be used to
                download files inside the image.

        Returns:
            The checksum.
        """
        hash_ = hashlib.md5()  # nosec
        hash_.update(self.settings.model_dump_json().encode())
        if self.entrypoint:
            hash_.update(self.entrypoint.encode())

        for destination, source in self.extra_files.items():
            hash_.update(destination.encode())
            hash_.update(source.encode())

        from zenml.utils.pipeline_docker_image_builder import (
            PipelineDockerImageBuilder,
        )

        pass_code_repo = self.should_download_files(
            code_repository=code_repository
        )
        requirements_files = (
            PipelineDockerImageBuilder.gather_requirements_files(
                docker_settings=self.settings,
                stack=stack,
                code_repository=code_repository if pass_code_repo else None,
                log=False,
            )
        )
        for _, requirements, _ in requirements_files:
            hash_.update(requirements.encode())

        return hash_.hexdigest()

    def should_include_files(
        self,
        code_repository: Optional["BaseCodeRepository"],
    ) -> bool:
        """Whether files should be included in the image.

        Args:
            code_repository: Code repository that can be used to download files
                inside the image.

        Returns:
            Whether files should be included in the image.
        """
        if self.settings.source_files == SourceFileMode.INCLUDE:
            return True

        if (
            self.settings.source_files == SourceFileMode.DOWNLOAD_OR_INCLUDE
            and not code_repository
        ):
            return True

        return False

    def should_download_files(
        self,
        code_repository: Optional["BaseCodeRepository"],
    ) -> bool:
        """Whether files should be downloaded in the image.

        Args:
            code_repository: Code repository that can be used to download files
                inside the image.

        Returns:
            Whether files should be downloaded in the image.
        """
        if not code_repository:
            return False

        return self.settings.source_files in {
            SourceFileMode.DOWNLOAD,
            SourceFileMode.DOWNLOAD_OR_INCLUDE,
        }
