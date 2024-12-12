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

import json
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.models.v2.base.base import BaseZenModel
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)
from zenml.models.v2.misc.build_item import BuildItem

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.pipeline import PipelineResponse
    from zenml.models.v2.core.stack import StackResponse


# ------------------ Request Model ------------------


class PipelineBuildBase(BaseZenModel):
    """Base model for pipeline builds."""

    images: Dict[str, BuildItem] = Field(
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
        title="The version of ZenML used for this build.", default=None
    )
    python_version: Optional[str] = Field(
        title="The Python version used for this build.", default=None
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

    checksum: Optional[str] = Field(title="The build checksum.", default=None)
    stack_checksum: Optional[str] = Field(
        title="The stack checksum.", default=None
    )

    stack: Optional[UUID] = Field(
        title="The stack that was used for this build.", default=None
    )
    pipeline: Optional[UUID] = Field(
        title="The pipeline that was used for this build.", default=None
    )


# ------------------ Update Model ------------------

# There is no update model for pipeline build models.


# ------------------ Response Model ------------------
class PipelineBuildResponseBody(WorkspaceScopedResponseBody):
    """Response body for pipeline builds."""


class PipelineBuildResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipeline builds."""

    pipeline: Optional["PipelineResponse"] = Field(
        default=None, title="The pipeline that was used for this build."
    )
    stack: Optional["StackResponse"] = Field(
        default=None, title="The stack that was used for this build."
    )
    images: Dict[str, "BuildItem"] = Field(
        default={}, title="The images of this build."
    )
    zenml_version: Optional[str] = Field(
        default=None, title="The version of ZenML used for this build."
    )
    python_version: Optional[str] = Field(
        default=None, title="The Python version used for this build."
    )
    checksum: Optional[str] = Field(default=None, title="The build checksum.")
    stack_checksum: Optional[str] = Field(
        default=None, title="The stack checksum."
    )
    is_local: bool = Field(
        title="Whether the build images are stored in a container "
        "registry or locally.",
    )
    contains_code: bool = Field(
        title="Whether any image of the build contains user code.",
    )


class PipelineBuildResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the pipeline build entity."""


class PipelineBuildResponse(
    WorkspaceScopedResponse[
        PipelineBuildResponseBody,
        PipelineBuildResponseMetadata,
        PipelineBuildResponseResources,
    ]
):
    """Response model for pipeline builds."""

    def get_hydrated_version(self) -> "PipelineBuildResponse":
        """Return the hydrated version of this pipeline build.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_build(self.id)

    # Helper methods
    def to_yaml(self) -> Dict[str, Any]:
        """Create a yaml representation of the pipeline build.

        Create a yaml representation of the pipeline build that can be used
        to create a PipelineBuildBase instance.

        Returns:
            The yaml representation of the pipeline build.
        """
        # Get the base attributes
        yaml_dict: Dict[str, Any] = json.loads(
            self.model_dump_json(
                exclude={
                    "body",
                    "metadata",
                }
            )
        )
        images = json.loads(
            self.get_metadata().model_dump_json(
                exclude={
                    "pipeline",
                    "stack",
                    "workspace",
                }
            )
        )
        yaml_dict.update(images)
        return yaml_dict

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
    @property
    def pipeline(self) -> Optional["PipelineResponse"]:
        """The `pipeline` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().pipeline

    @property
    def stack(self) -> Optional["StackResponse"]:
        """The `stack` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().stack

    @property
    def images(self) -> Dict[str, "BuildItem"]:
        """The `images` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().images

    @property
    def zenml_version(self) -> Optional[str]:
        """The `zenml_version` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().zenml_version

    @property
    def python_version(self) -> Optional[str]:
        """The `python_version` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().python_version

    @property
    def checksum(self) -> Optional[str]:
        """The `checksum` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().checksum

    @property
    def stack_checksum(self) -> Optional[str]:
        """The `stack_checksum` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().stack_checksum

    @property
    def is_local(self) -> bool:
        """The `is_local` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().is_local

    @property
    def contains_code(self) -> bool:
        """The `contains_code` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().contains_code


# ------------------ Filter Model ------------------


class PipelineBuildFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all pipeline builds."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "container_registry_id",
    ]

    workspace_id: Optional[Union[UUID, str]] = Field(
        description="Workspace for this pipeline build.",
        default=None,
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        description="User that produced this pipeline build.",
        default=None,
        union_mode="left_to_right",
    )
    pipeline_id: Optional[Union[UUID, str]] = Field(
        description="Pipeline associated with the pipeline build.",
        default=None,
        union_mode="left_to_right",
    )
    stack_id: Optional[Union[UUID, str]] = Field(
        description="Stack associated with the pipeline build.",
        default=None,
        union_mode="left_to_right",
    )
    container_registry_id: Optional[Union[UUID, str]] = Field(
        description="Container registry associated with the pipeline build.",
        default=None,
        union_mode="left_to_right",
    )
    is_local: Optional[bool] = Field(
        description="Whether the build images are stored in a container "
        "registry or locally.",
        default=None,
    )
    contains_code: Optional[bool] = Field(
        description="Whether any image of the build contains user code.",
        default=None,
    )
    zenml_version: Optional[str] = Field(
        description="The version of ZenML used for this build.", default=None
    )
    python_version: Optional[str] = Field(
        description="The Python version used for this build.", default=None
    )
    checksum: Optional[str] = Field(
        description="The build checksum.", default=None
    )
    stack_checksum: Optional[str] = Field(
        description="The stack checksum.", default=None
    )

    def get_custom_filters(
        self,
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_

        from zenml.enums import StackComponentType
        from zenml.zen_stores.schemas import (
            PipelineBuildSchema,
            StackComponentSchema,
            StackCompositionSchema,
            StackSchema,
        )

        if self.container_registry_id:
            container_registry_filter = and_(
                PipelineBuildSchema.stack_id == StackSchema.id,
                StackSchema.id == StackCompositionSchema.stack_id,
                StackCompositionSchema.component_id == StackComponentSchema.id,
                StackComponentSchema.type
                == StackComponentType.CONTAINER_REGISTRY.value,
                StackComponentSchema.id == self.container_registry_id,
            )
            custom_filters.append(container_registry_filter)

        return custom_filters
