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
"""Model definition for pipeline build item."""

import hashlib
from typing import List, Optional

from pydantic import BaseModel, Field

from zenml.config.build_configuration import BuildConfiguration


class BuildItem(BaseModel):
    """Pipeline build item.

    Attributes:
        image: The image name or digest.
        dockerfile: The contents of the Dockerfile used to build the image.
        requirements: The pip requirements installed in the image. This is a
            string consisting of multiple concatenated requirements.txt files.
        settings_checksum: Checksum of the settings used for the build.
        contains_code: Whether the image contains user files.
        requires_code_download: Whether the image needs to download files.
    """

    image: str = Field(title="The image name or digest.")
    dockerfile: Optional[str] = Field(
        default=None, title="The dockerfile used to build the image."
    )
    requirements: Optional[str] = Field(
        default=None, title="The pip requirements installed in the image."
    )
    settings_checksum: Optional[str] = Field(
        default=None, title="The checksum of the build settings."
    )
    contains_code: bool = Field(
        default=True, title="Whether the image contains user files."
    )
    requires_code_download: bool = Field(
        default=False, title="Whether the image needs to download files."
    )


class PreparedBuildItem(BaseModel):
    """A build configuration with its precomputed identifiers.

    Attributes:
        configuration: The Docker build configuration.
        key: The key used to identify the image in a pipeline build.
        settings_checksum: Checksum of the build configuration settings.
    """

    configuration: BuildConfiguration = Field(
        title="The Docker build configuration."
    )
    key: str = Field(title="The pipeline build image key.")
    settings_checksum: str = Field(
        title="The checksum of the build configuration settings."
    )


class PreparedPipelineBuild(BaseModel):
    """Precomputed data needed to find or create a pipeline build.

    Attributes:
        items: Build configurations with their precomputed identifiers.
    """

    items: List[PreparedBuildItem] = Field(
        title="The prepared Docker build configurations."
    )

    @property
    def checksum(self) -> str:
        """Compute the aggregate checksum of all prepared build items.

        Returns:
            The aggregate pipeline build checksum.
        """
        hash_ = hashlib.md5()  # nosec
        for item in self.items:
            hash_.update(item.key.encode())
            hash_.update(item.settings_checksum.encode())

        return hash_.hexdigest()

    def get_matching_item(
        self,
        key: str,
        configuration: BuildConfiguration,
    ) -> Optional[PreparedBuildItem]:
        """Get an item with the same key and build configuration.

        Args:
            key: The pipeline build image key.
            configuration: The required build configuration.

        Returns:
            A matching prepared build item, if one exists.
        """
        return next(
            (
                item
                for item in self.items
                if item.key == key and item.configuration == configuration
            ),
            None,
        )
