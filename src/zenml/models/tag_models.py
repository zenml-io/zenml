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
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

from zenml.enums import ColorVariants, TaggableResourceTypes
from zenml.models.base_models import (
    BaseRequestModel,
    BaseResponseModel,
    update_model,
)
from zenml.models.constants import STR_FIELD_MAX_LENGTH
from zenml.models.filter_models import BaseFilterModel
from zenml.utils.uuid_utils import generate_uuid_from_string

# Tags


def _validate_color(color: str) -> str:
    try:
        color = str(getattr(ColorVariants, color.upper()).value)
    except:
        raise ValueError(
            f"Given color value `{color}` does not "
            "match any of defined ColorVariants "
            f"`{list(ColorVariants.__members__.keys())}`."
        )
    return color


class TagBaseModel(BaseModel):
    """Base model for tags."""

    name: str = Field(
        description="The unique title of the tag.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    color: str = Field(
        description="The color variant assigned to the tag.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    @root_validator(pre=True)
    def _set_random_color_if_none(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not values.get("color", None):
            values["color"] = random.choice(list(ColorVariants)).name.lower()
        else:
            _validate_color(values["color"])
        return values


class TagResponseModel(TagBaseModel, BaseResponseModel):
    """Response model for tags."""

    tagged_count: int = Field(
        description="The count of resources tagged with this tag."
    )


class TagFilterModel(BaseFilterModel):
    """Model to enable advanced filtering of all tags."""

    name: Optional[str]
    color: Optional[str]

    @validator("color", pre=True)
    def _translate_color_to_integer(cls, color: str) -> str:
        if not color:
            return None
        else:
            return _validate_color(color)


class TagRequestModel(TagBaseModel, BaseRequestModel):
    """Request model for tags."""


@update_model
class TagUpdateModel(BaseModel):
    """Update model for tags."""

    name: Optional[str]
    color: Optional[str]

    @validator("color", pre=True)
    def _translate_color_to_integer(cls, color: str) -> str:
        if not color:
            return None
        else:
            return _validate_color(color)


# Tags <> Resources


class TagResourceBaseModel(BaseModel):
    """Base model for tag resource relationships."""

    tag_id: UUID
    resource_id: UUID

    @staticmethod
    def _get_tag_resource_id(tag_id: UUID, resource_id: UUID):
        return generate_uuid_from_string(str(tag_id) + str(resource_id))

    @property
    def tag_resource_id(self):
        return self._get_tag_resource_id(self.tag_id, self.resource_id)


class TagResourceResponseModel(TagResourceBaseModel, BaseResponseModel):
    """Response model for tag resource relationships."""


class TagResourceRequestModel(TagResourceBaseModel, BaseRequestModel):
    """Request model for tag resource relationships."""

    resource_type: TaggableResourceTypes
