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

from typing import Optional

from pydantic import BaseModel, Field


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
        title="The dockerfile used to build the image."
    )
    requirements: Optional[str] = Field(
        title="The pip requirements installed in the image."
    )
    settings_checksum: Optional[str] = Field(
        title="The checksum of the build settings."
    )
    contains_code: bool = Field(
        default=True, title="Whether the image contains user files."
    )
    requires_code_download: bool = Field(
        default=False, title="Whether the image needs to download files."
    )
