#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Models representing pipeline builds."""

from typing import TYPE_CHECKING, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.utils import pydantic_utils

if TYPE_CHECKING:
    from zenml.models.pipeline_models import PipelineResponseModel
    from zenml.models.stack_models import StackResponseModel


# ---- #
# BASE #
# ---- #


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


class PipelineBuildBaseModel(pydantic_utils.YAMLSerializationMixin):
    """Base model for pipeline builds.

    Attributes:
        images: Docker images of this build.
        is_local: Whether the images are stored locally or in a container
            registry.
    """

    images: Dict[str, BuildItem] = Field(
        default={}, title="The images of this build."
    )
    is_local: bool = Field(
        title="Whether the build images are stored in a container registry or locally.",
    )
    contains_code: bool = Field(
        title="Whether any image of the build contains user code.",
    )
    zenml_version: Optional[str] = Field(
        title="The version of ZenML used for this build."
    )
    python_version: Optional[str] = Field(
        title="The Python version used for this build."
    )
    checksum: Optional[str] = Field(title="The build checksum.")

    @property
    def requires_code_download(self) -> bool:
        """Whether the build requires code download.

        Returns:
            Whether the build requires code download.
        """
        return any(
            item.requires_code_download for item in self.images.values()
        )

    @staticmethod
    def get_image_key(component_key: str, step: Optional[str] = None) -> str:
        """Get the image key.

        Args:
            component_key: The component key.
            step: The pipeline step for which the image was built.

        Returns:
            The image key.
        """
        if step:
            return f"{step}.{component_key}"
        else:
            return component_key

    def get_image(self, component_key: str, step: Optional[str] = None) -> str:
        """Get the image built for a specific key.

        Args:
            component_key: The key for which to get the image.
            step: The pipeline step for which to get the image. If no image
                exists for this step, will fallback to the pipeline image for
                the same key.

        Returns:
            The image name or digest.
        """
        return self._get_item(component_key=component_key, step=step).image

    def get_settings_checksum(
        self, component_key: str, step: Optional[str] = None
    ) -> Optional[str]:
        """Get the settings checksum for a specific key.

        Args:
            component_key: The key for which to get the checksum.
            step: The pipeline step for which to get the checksum. If no
                image exists for this step, will fallback to the pipeline image
                for the same key.

        Returns:
            The settings checksum.
        """
        return self._get_item(
            component_key=component_key, step=step
        ).settings_checksum

    def _get_item(
        self, component_key: str, step: Optional[str] = None
    ) -> BuildItem:
        """Get the item for a specific key.

        Args:
            component_key: The key for which to get the item.
            step: The pipeline step for which to get the item. If no item
                exists for this step, will fallback to the item for
                the same key.

        Raises:
            KeyError: If no item exists for the given key.

        Returns:
            The build item.
        """
        if step:
            try:
                combined_key = self.get_image_key(
                    component_key=component_key, step=step
                )
                return self.images[combined_key]
            except KeyError:
                pass

        try:
            return self.images[component_key]
        except KeyError:
            raise KeyError(
                f"Unable to find image for key {component_key}. Available keys: "
                f"{set(self.images)}."
            )


# -------- #
# RESPONSE #
# -------- #


class PipelineBuildResponseModel(
    PipelineBuildBaseModel, WorkspaceScopedResponseModel
):
    """Response model for pipeline builds."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        title="The pipeline that was used for this build."
    )
    stack: Optional["StackResponseModel"] = Field(
        title="The stack that was used for this build."
    )


# ------ #
# FILTER #
# ------ #


class PipelineBuildFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all pipeline builds."""

    workspace_id: Union[UUID, str, None] = Field(
        description="Workspace for this pipeline build."
    )
    user_id: Union[UUID, str, None] = Field(
        description="User that produced this pipeline build."
    )
    pipeline_id: Union[UUID, str, None] = Field(
        description="Pipeline associated with the pipeline build.",
    )
    stack_id: Union[UUID, str, None] = Field(
        description="Stack used for the Pipeline Run"
    )
    is_local: Optional[bool] = Field(
        description="Whether the build images are stored in a container registry or locally.",
    )
    contains_code: Optional[bool] = Field(
        description="Whether any image of the build contains user code.",
    )
    zenml_version: Optional[str] = Field(
        description="The version of ZenML used for this build."
    )
    python_version: Optional[str] = Field(
        description="The Python version used for this build."
    )
    checksum: Optional[str] = Field(description="The build checksum.")


# ------- #
# REQUEST #
# ------- #


class PipelineBuildRequestModel(
    PipelineBuildBaseModel, WorkspaceScopedRequestModel
):
    """Request model for pipelines builds."""

    stack: Optional[UUID] = Field(
        title="The stack that was used for this build."
    )
    pipeline: Optional[UUID] = Field(
        title="The pipeline that was used for this build."
    )
