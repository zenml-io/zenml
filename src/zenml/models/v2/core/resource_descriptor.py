#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Models representing resource descriptors."""

from typing import Any, ClassVar, List, Optional, Union
from uuid import UUID

from pydantic import Field, PositiveInt

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)


class ResourceDescriptorUnit(BaseZenModel):
    """Unit entry for a resource descriptor."""

    name: str = Field(
        title="The resource unit name.",
        min_length=1,
        max_length=64,
    )
    multiplier: PositiveInt = Field(
        title="The positive multiplier over the descriptor base unit.",
    )


class ResourceDescriptorRequest(UserScopedRequest):
    """Request model for resource descriptor creation."""

    name: str = Field(
        title="The resource descriptor name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    kind: str = Field(
        title="The resource descriptor kind.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        title="The resource descriptor attributes.",
    )
    units: list[ResourceDescriptorUnit] = Field(
        default_factory=list,
        title="The resource descriptor unit catalog.",
    )


class ResourceDescriptorUpdate(BaseUpdate):
    """Update model for resource descriptors."""

    name: Optional[str] = Field(
        default=None,
        title="The new resource descriptor name.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    kind: Optional[str] = Field(
        default=None,
        title="The new resource descriptor kind.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    attributes: Optional[dict[str, Any]] = Field(
        default=None,
        title="The replacement resource descriptor attributes.",
    )
    units: Optional[list[ResourceDescriptorUnit]] = Field(
        default=None,
        title="The replacement resource descriptor unit catalog.",
    )


class ResourceDescriptorResponseBody(UserScopedResponseBody):
    """Response body for resource descriptors."""

    name: str = Field(title="The resource descriptor name.")
    kind: str = Field(title="The resource descriptor kind.")


class ResourceDescriptorResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for resource descriptors."""

    attributes: dict[str, Any] = Field(
        default_factory=dict,
        title="The resource descriptor attributes.",
    )
    units: list[ResourceDescriptorUnit] = Field(
        default_factory=list,
        title="The resource descriptor unit catalog.",
    )


class ResourceDescriptorResponseResources(UserScopedResponseResources):
    """Response resources for resource descriptors."""


class ResourceDescriptorResponse(
    UserScopedResponse[
        ResourceDescriptorResponseBody,
        ResourceDescriptorResponseMetadata,
        ResourceDescriptorResponseResources,
    ]
):
    """Response model for resource descriptors."""

    @property
    def name(self) -> str:
        """Resource descriptor name.

        Returns:
            The resource descriptor name.
        """
        return self.get_body().name

    @property
    def kind(self) -> str:
        """Resource descriptor kind.

        Returns:
            The resource descriptor kind.
        """
        return self.get_body().kind

    @property
    def attributes(self) -> dict[str, Any]:
        """Resource descriptor attributes.

        Returns:
            The descriptor attributes.
        """
        return self.get_metadata().attributes

    @property
    def units(self) -> list[ResourceDescriptorUnit]:
        """Resource descriptor unit catalog.

        Returns:
            The resource descriptor units.
        """
        return self.get_metadata().units


class ResourceDescriptorFilter(UserScopedFilter):
    """Resource descriptor filter model."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
    ]

    id: Union[UUID, str, None] = Field(
        default=None,
        description="ID of the resource descriptor.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the resource descriptor.",
    )
    kind: Optional[str] = Field(
        default=None,
        description="Kind of the resource descriptor.",
    )
