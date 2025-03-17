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
"""Models representing projects."""

import re
from typing import Any, Dict, Optional

from pydantic import Field, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH, STR_ID_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseUpdate,
)
from zenml.models.v2.base.filter import BaseFilter
from zenml.utils.pydantic_utils import before_validator_handler

# ------------------ Request Model ------------------


class ProjectRequest(BaseRequest):
    """Request model for projects."""

    name: str = Field(
        title="The unique name of the project. The project name must only "
        "contain only lowercase letters, numbers, underscores, and hyphens and "
        "be at most 50 characters long.",
        min_length=1,
        max_length=STR_ID_FIELD_MAX_LENGTH,
        pattern=r"^[a-z0-9_-]+$",
    )
    display_name: str = Field(
        default="",
        title="The display name of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _validate_project_name(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the project name.

        Args:
            data: The values to validate.

        Returns:
            The validated values.
        """
        name = data.get("name")
        display_name = data.get("display_name")

        if not name and not display_name:
            return data

        if not name:
            assert display_name

            project_name = display_name.lower().replace(" ", "-")
            project_name = re.sub(r"[^a-z0-9_-]", "", project_name)

            data["name"] = project_name

        if not display_name:
            # We just use the name as the display name
            data["display_name"] = name

        return data


# ------------------ Update Model ------------------


class ProjectUpdate(BaseUpdate):
    """Update model for projects."""

    name: Optional[str] = Field(
        title="The unique name of the project. The project name must only "
        "contain only lowercase letters, numbers, underscores, and hyphens and "
        "be at most 50 characters long.",
        min_length=1,
        max_length=STR_ID_FIELD_MAX_LENGTH,
        pattern=r"^[a-z0-9_-]+$",
        default=None,
    )
    display_name: Optional[str] = Field(
        title="The display name of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )


# ------------------ Response Model ------------------


class ProjectResponseBody(BaseDatedResponseBody):
    """Response body for projects."""

    display_name: str = Field(
        title="The display name of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class ProjectResponseMetadata(BaseResponseMetadata):
    """Response metadata for projects."""

    description: str = Field(
        default="",
        title="The description of the project.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class ProjectResponseResources(BaseResponseResources):
    """Class for all resource models associated with the project entity."""


class ProjectResponse(
    BaseIdentifiedResponse[
        ProjectResponseBody,
        ProjectResponseMetadata,
        ProjectResponseResources,
    ]
):
    """Response model for projects."""

    name: str = Field(
        title="The unique name of the project.",
        max_length=STR_ID_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "ProjectResponse":
        """Get the hydrated version of this project.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_project(self.id)

    # Body and metadata properties

    @property
    def display_name(self) -> str:
        """The `display_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().display_name

    @property
    def description(self) -> str:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description


# ------------------ Filter Model ------------------


class ProjectFilter(BaseFilter):
    """Model to enable advanced filtering of all projects."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the project",
    )

    display_name: Optional[str] = Field(
        default=None,
        description="Display name of the project",
    )
