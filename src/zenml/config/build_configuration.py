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
import json
from typing import TYPE_CHECKING, Dict, Optional

from pydantic import BaseModel

from zenml.config.docker_settings import DockerSettings
from zenml.logger import get_logger
from zenml.utils import json_utils

if TYPE_CHECKING:
    from zenml.code_repositories import BaseCodeRepository
    from zenml.stack import Stack

logger = get_logger(__name__)


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
        settings_json = json.dumps(
            self.settings.model_dump(
                mode="json", exclude={"prevent_build_reuse"}
            ),
            sort_keys=True,
            default=json_utils.pydantic_encoder,
        )
        hash_.update(settings_json.encode())
        if self.entrypoint:
            hash_.update(self.entrypoint.encode())

        for destination, source in self.extra_files.items():
            hash_.update(destination.encode())
            hash_.update(source.encode())

        from zenml.utils.pipeline_docker_image_builder import (
            PipelineDockerImageBuilder,
        )

        pass_code_repo = self.should_download_files_from_code_repository(
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

        if self.settings.dockerfile:
            with open(self.settings.dockerfile, "rb") as f:
                hash_.update(f.read())

        if self.settings.parent_image and stack.container_registry:
            digest = stack.container_registry.get_image_repo_digest(
                self.settings.parent_image
            )
            if digest:
                hash_.update(digest.encode())
            elif self.settings.skip_build:
                # If the user has specified to skip the build, the image being
                # used for the run is whatever they set for `parent_image`.
                # In this case, the bevavior depends on the orchestrators image
                # pull policy, and whether there is any caching involved. This
                # is out of our control here, so we don't log any warning.
                pass
            else:
                logger.warning(
                    "Unable to fetch parent image digest for image `%s`. "
                    "This may lead to ZenML reusing existing builds even "
                    "though a new version of the parent image has been "
                    "pushed. Most likely you can fix this error by making sure "
                    "the parent image is pushed to the container registry of "
                    "your active stack `%s`.",
                    self.settings.parent_image,
                    stack.name,
                )

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
        if self.settings.local_project_install_command:
            return True

        if self.should_download_files(code_repository=code_repository):
            return False

        return self.settings.allow_including_files_in_images

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
        if self.settings.local_project_install_command:
            return False

        if self.should_download_files_from_code_repository(
            code_repository=code_repository
        ):
            return True

        if self.settings.allow_download_from_artifact_store:
            return True

        return False

    def should_download_files_from_code_repository(
        self,
        code_repository: Optional["BaseCodeRepository"],
    ) -> bool:
        """Whether files should be downloaded from the code repository.

        Args:
            code_repository: Code repository that can be used to download files
                inside the image.

        Returns:
            Whether files should be downloaded from the code repository.
        """
        if self.settings.local_project_install_command:
            return False

        if (
            code_repository
            and self.settings.allow_download_from_code_repository
        ):
            return True

        return False
