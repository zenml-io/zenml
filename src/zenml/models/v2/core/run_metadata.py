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
"""Models representing run metadata."""

from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import Field, field_validator

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
)

# ------------------ Request Model ------------------


class RunMetadataRequest(WorkspaceScopedRequest):
    """Request model for run metadata."""

    resource_id: UUID = Field(
        title="The ID of the resource that this metadata belongs to.",
    )
    resource_type: MetadataResourceTypes = Field(
        title="The type of the resource that this metadata belongs to.",
    )
    stack_component_id: Optional[UUID] = Field(
        title="The ID of the stack component that this metadata belongs to."
    )
    values: Dict[str, "MetadataType"] = Field(
        title="The metadata to be created.",
    )
    types: Dict[str, "MetadataTypeEnum"] = Field(
        title="The types of the metadata to be created.",
    )


# ------------------ Update Model ------------------

# There is no update model for run metadata.

# ------------------ Response Model ------------------


class RunMetadataResponseBody(WorkspaceScopedResponseBody):
    """Response body for run metadata."""

    key: str = Field(title="The key of the metadata.")
    value: MetadataType = Field(
        title="The value of the metadata.", union_mode="smart"
    )
    type: MetadataTypeEnum = Field(title="The type of the metadata.")

    @field_validator("key", "type")
    @classmethod
    def str_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum str length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        assert len(str(value)) < STR_FIELD_MAX_LENGTH, (
            "The length of the value for this field can not "
            f"exceed {STR_FIELD_MAX_LENGTH}"
        )
        return value

    @field_validator("value")
    @classmethod
    def text_field_max_length_check(cls, value: Any) -> Any:
        """Checks if the length of the value exceeds the maximum text length.

        Args:
            value: the value set in the field

        Returns:
            the value itself.

        Raises:
            AssertionError: if the length of the field is longer than the
                maximum threshold.
        """
        assert len(str(value)) < TEXT_FIELD_MAX_LENGTH, (
            "The length of the value for this field can not "
            f"exceed {TEXT_FIELD_MAX_LENGTH}"
        )
        return value


class RunMetadataResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for run metadata."""

    resource_id: UUID = Field(
        title="The ID of the resource that this metadata belongs to.",
    )
    resource_type: MetadataResourceTypes = Field(
        title="The type of the resource that this metadata belongs to.",
    )
    stack_component_id: Optional[UUID] = Field(
        title="The ID of the stack component that this metadata belongs to."
    )


class RunMetadataResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the run metadata entity."""


class RunMetadataResponse(
    WorkspaceScopedResponse[
        RunMetadataResponseBody,
        RunMetadataResponseMetadata,
        RunMetadataResponseResources,
    ]
):
    """Response model for run metadata."""

    def get_hydrated_version(self) -> "RunMetadataResponse":
        """Get the hydrated version of this run metadata.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_run_metadata(self.id)

    # Body and metadata properties
    @property
    def key(self) -> str:
        """The `key` property.

        Returns:
            the value of the property.
        """
        return self.get_body().key

    @property
    def value(self) -> MetadataType:
        """The `value` property.

        Returns:
            the value of the property.
        """
        return self.get_body().value

    @property
    def type(self) -> MetadataTypeEnum:
        """The `type` property.

        Returns:
            the value of the property.
        """
        return self.get_body().type

    @property
    def resource_id(self) -> UUID:
        """The `resource_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().resource_id

    @property
    def resource_type(self) -> MetadataResourceTypes:
        """The `resource_type` property.

        Returns:
            the value of the property.
        """
        return MetadataResourceTypes(self.get_metadata().resource_type)

    @property
    def stack_component_id(self) -> Optional[UUID]:
        """The `stack_component_id` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().stack_component_id


# ------------------ Filter Model ------------------


class RunMetadataFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of run metadata."""

    resource_id: Optional[Union[str, UUID]] = Field(
        default=None, union_mode="left_to_right"
    )
    resource_type: Optional[MetadataResourceTypes] = None
    stack_component_id: Optional[Union[str, UUID]] = Field(
        default=None, union_mode="left_to_right"
    )
    key: Optional[str] = None
    type: Optional[Union[str, MetadataTypeEnum]] = Field(
        default=None, union_mode="left_to_right"
    )


# -------------------- Lazy Loader --------------------


class LazyRunMetadataResponse(RunMetadataResponse):
    """Lazy run metadata response.

    Used if the run metadata is accessed from the model in
    a pipeline context available only during pipeline compilation.
    """

    id: Optional[UUID] = None  # type: ignore[assignment]
    lazy_load_artifact_name: Optional[str] = None
    lazy_load_artifact_version: Optional[str] = None
    lazy_load_metadata_name: Optional[str] = None
    lazy_load_model_name: str
    lazy_load_model_version: Optional[str] = None

    def get_body(self) -> None:  # type: ignore[override]
        """Protects from misuse of the lazy loader.

        Raises:
            RuntimeError: always
        """
        raise RuntimeError(
            "Cannot access run metadata body before pipeline runs."
        )

    def get_metadata(self) -> None:  # type: ignore[override]
        """Protects from misuse of the lazy loader.

        Raises:
            RuntimeError: always
        """
        raise RuntimeError(
            "Cannot access run metadata metadata before pipeline runs."
        )
