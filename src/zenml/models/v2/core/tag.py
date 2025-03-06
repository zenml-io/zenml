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
"""Models representing tags."""

import random
from typing import Optional

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ColorVariants
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    UserScopedFilter,
    UserScopedRequest,
    UserScopedResponse,
    UserScopedResponseBody,
    UserScopedResponseMetadata,
    UserScopedResponseResources,
)

# ------------------ Request Model ------------------


class TagRequest(UserScopedRequest):
    """Request model for tags."""

    name: str = Field(
        description="The unique title of the tag.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    exclusive: bool = Field(
        description="The flag signifying whether the tag is an exclusive tag.",
        default=False,
    )
    color: ColorVariants = Field(
        description="The color variant assigned to the tag.",
        default_factory=lambda: random.choice(list(ColorVariants)),
    )


# ------------------ Update Model ------------------


class TagUpdate(BaseUpdate):
    """Update model for tags."""

    name: Optional[str] = None
    exclusive: Optional[bool] = None
    color: Optional[ColorVariants] = None


# ------------------ Response Model ------------------


class TagResponseBody(UserScopedResponseBody):
    """Response body for tags."""

    color: ColorVariants = Field(
        description="The color variant assigned to the tag.",
        default_factory=lambda: random.choice(list(ColorVariants)),
    )
    exclusive: bool = Field(
        description="The flag signifying whether the tag is an exclusive tag."
    )
    tagged_count: int = Field(
        description="The count of resources tagged with this tag."
    )


class TagResponseMetadata(UserScopedResponseMetadata):
    """Response metadata for tags."""


class TagResponseResources(UserScopedResponseResources):
    """Class for all resource models associated with the tag entity."""


class TagResponse(
    UserScopedResponse[
        TagResponseBody, TagResponseMetadata, TagResponseResources
    ]
):
    """Response model for tags."""

    name: str = Field(
        description="The unique title of the tag.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "TagResponse":
        """Get the hydrated version of this tag.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_tag(self.id)

    @property
    def color(self) -> ColorVariants:
        """The `color` property.

        Returns:
            the value of the property.
        """
        return self.get_body().color

    @property
    def exclusive(self) -> bool:
        """The `exclusive` property.

        Returns:
            the value of the property.
        """
        return self.get_body().exclusive

    @property
    def tagged_count(self) -> int:
        """The `tagged_count` property.

        Returns:
            the value of the property.
        """
        return self.get_body().tagged_count


# ------------------ Filter Model ------------------


class TagFilter(UserScopedFilter):
    """Model to enable advanced filtering of all tags."""

    name: Optional[str] = Field(
        description="The unique title of the tag.", default=None
    )
    color: Optional[ColorVariants] = Field(
        description="The color variant assigned to the tag.", default=None
    )
    exclusive: Optional[bool] = Field(
        description="The flag signifying whether the tag is an exclusive tag.",
        default=None,
    )
