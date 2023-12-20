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

from typing import Dict, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.enums import MetadataResourceTypes
from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
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

    class Config:
        """Pydantic configuration."""

        smart_union = True


# ------------------ Update Model ------------------

# There is no update model for run metadata.

# ------------------ Response Model ------------------


class RunMetadataResponseBody(WorkspaceScopedResponseBody):
    """Response body for run metadata."""

    key: str = Field(
        title="The key of the metadata.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    value: MetadataType = Field(
        title="The value of the metadata.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    type: MetadataTypeEnum = Field(
        title="The type of the metadata.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    class Config:
        """Pydantic configuration."""

        smart_union = True


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


class RunMetadataResponse(
    WorkspaceScopedResponse[
        RunMetadataResponseBody, RunMetadataResponseMetadata
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

    resource_id: Optional[Union[str, UUID]] = None
    resource_type: Optional[MetadataResourceTypes] = None
    stack_component_id: Optional[Union[str, UUID]] = None
    key: Optional[str] = None
    type: Optional[Union[str, MetadataTypeEnum]] = None
