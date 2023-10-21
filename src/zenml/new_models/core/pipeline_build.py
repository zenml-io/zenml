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
"""Models representing pipeline builds."""

from typing import TYPE_CHECKING, Dict, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.new_models.base import (
    BaseZenModel,
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    hydrated_property,
)

if TYPE_CHECKING:
    from zenml.new_models.build_item import BuildItem
    from zenml.new_models.core.pipeline import PipelineResponse
    from zenml.new_models.core.stack import StackResponse


# ------------------ Request Model ------------------


class PipelineBuildBase(BaseZenModel):
    """Base model for pipeline builds."""

    images: Dict[str, "BuildItem"] = Field(
        default={}, title="The images of this build."
    )
    is_local: bool = Field(
        title="Whether the build images are stored in a container registry "
        "or locally.",
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

    # Helper methods
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
                exists for this step, will fall back to the pipeline image for
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
                image exists for this step, will fall back to the pipeline image
                for the same key.

        Returns:
            The settings checksum.
        """
        return self._get_item(
            component_key=component_key, step=step
        ).settings_checksum

    def _get_item(
        self, component_key: str, step: Optional[str] = None
    ) -> "BuildItem":
        """Get the item for a specific key.

        Args:
            component_key: The key for which to get the item.
            step: The pipeline step for which to get the item. If no item
                exists for this step, will fall back to the item for
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


class PipelineBuildRequest(PipelineBuildBase, WorkspaceScopedRequest):
    """Request model for pipelines builds."""

    checksum: Optional[str] = Field(title="The build checksum.")

    stack: Optional[UUID] = Field(
        title="The stack that was used for this build."
    )
    pipeline: Optional[UUID] = Field(
        title="The pipeline that was used for this build."
    )


# ------------------ Update Model ------------------

# There is no update model for pipeline build models.


# ------------------ Response Model ------------------
class PipelineBuildResponseBody(WorkspaceScopedResponseBody):
    """Response body for pipeline builds."""


class PipelineBuildResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipeline builds."""

    pipeline: Optional["PipelineResponse"] = Field(
        title="The pipeline that was used for this build."
    )
    stack: Optional["StackResponse"] = Field(
        title="The stack that was used for this build."
    )
    images: Dict[str, "BuildItem"] = Field(
        default={}, title="The images of this build."
    )
    zenml_version: Optional[str] = Field(
        title="The version of ZenML used for this build."
    )
    python_version: Optional[str] = Field(
        title="The Python version used for this build."
    )
    checksum: Optional[str] = Field(title="The build checksum.")
    is_local: bool = Field(
        title="Whether the build images are stored in a container "
        "registry or locally.",
    )
    contains_code: bool = Field(
        title="Whether any image of the build contains user code.",
    )


class PipelineBuildResponse(WorkspaceScopedResponse):
    """Response model for pipeline builds"""

    # Body and metadata pair
    body: "PipelineBuildResponseBody"
    metadata: Optional["PipelineBuildResponseMetadata"]

    def get_hydrated_version(self) -> "PipelineBuildResponse":
        """Return the hydrated version of this pipeline build."""
        from zenml.client import Client

        return Client().get_build(self.id)

    # Helper methods
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
                exists for this step, will fall back to the pipeline image for
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
                image exists for this step, will fall back to the pipeline image
                for the same key.

        Returns:
            The settings checksum.
        """
        return self._get_item(
            component_key=component_key, step=step
        ).settings_checksum

    def _get_item(
        self, component_key: str, step: Optional[str] = None
    ) -> "BuildItem":
        """Get the item for a specific key.

        Args:
            component_key: The key for which to get the item.
            step: The pipeline step for which to get the item. If no item
                exists for this step, will fall back to the item for
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

    # Body and metadata properties
    @hydrated_property
    def pipeline(self):
        """The `pipeline` property."""
        return self.metadata.pipeline

    @hydrated_property
    def stack(self):
        """The `stack` property."""
        return self.metadata.stack

    @hydrated_property
    def images(self):
        """The `images` property."""
        return self.metadata.images

    @hydrated_property
    def zenml_version(self):
        """The `zenml_version` property."""
        return self.metadata.zenml_version

    @hydrated_property
    def python_version(self):
        """The `python_version` property."""
        return self.metadata.python_version

    @hydrated_property
    def checksum(self):
        """The `checksum` property."""
        return self.metadata.checksum

    @hydrated_property
    def is_local(self):
        """The `is_local` property."""
        return self.metadata.is_local

    @hydrated_property
    def contains_code(self):
        """The `contains_code` property."""
        return self.metadata.contains_code


# ------------------ Filter Model ------------------


class PipelineBuildFilter(WorkspaceScopedFilter):
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
        description="Whether the build images are stored in a container "
        "registry or locally.",
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
