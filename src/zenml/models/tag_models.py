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
"""Models representing tags."""


import random
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ColorVariants, TaggableResourceTypes
from zenml.models.base_models import BaseRequestModel, BaseResponseModel
from zenml.models.v2.base.filter import BaseFilter

# Tags


class TagBaseModel(BaseModel):
    """Base model for tags."""

    name: str = Field(
        description="The unique title of the tag.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    color: ColorVariants = Field(
        description="The color variant assigned to the tag.",
        default_factory=lambda: random.choice(list(ColorVariants)),
    )


class TagResponseModel(TagBaseModel, BaseResponseModel):
    """Response model for tags."""

    tagged_count: int = Field(
        description="The count of resources tagged with this tag."
    )


class TagFilterModel(BaseFilter):
    """Model to enable advanced filtering of all tags."""

    name: Optional[str]
    color: Optional[ColorVariants]


class TagRequestModel(TagBaseModel, BaseRequestModel):
    """Request model for tags."""


class TagUpdateModel(BaseModel):
    """Update model for tags."""

    name: Optional[str]
    color: Optional[ColorVariants]


# Tags <> Resources


class TagResourceBaseModel(BaseModel):
    """Base model for tag resource relationships."""

    tag_id: UUID
    resource_id: UUID
    resource_type: TaggableResourceTypes


class TagResourceResponseModel(TagResourceBaseModel, BaseResponseModel):
    """Response model for tag resource relationships."""


class TagResourceRequestModel(TagResourceBaseModel, BaseRequestModel):
    """Request model for tag resource relationships."""
