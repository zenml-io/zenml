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
"""Models representing workspaces."""

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


class WorkspaceRequest(BaseRequest):
    """Request model for workspaces."""

    name: str = Field(
        title="The unique name of the workspace. The workspace name must only "
        "contain only lowercase letters, numbers, underscores, and hyphens and "
        "be at most 50 characters long.",
        min_length=1,
        max_length=STR_ID_FIELD_MAX_LENGTH,
        pattern=r"^[a-z0-9_-]+$",
    )
    display_name: str = Field(
        default="",
        title="The display name of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _validate_workspace_name(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the workspace name.

        Args:
            data: The values to validate.

        Raises:
            ValueError: If the workspace name is invalid.

        Returns:
            The validated values.
        """
        name = data.get("name")
        display_name = data.get("display_name")

        if not name and not display_name:
            return data

        if not name:
            assert display_name

            tenant_name = display_name.lower().replace(" ", "-")
            tenant_name = re.sub(r"[^a-z0-9_-]", "", tenant_name)

            data["name"] = tenant_name

        if not display_name:
            # We just use the name as the display name
            data["display_name"] = name

        return data


# ------------------ Update Model ------------------


class WorkspaceUpdate(BaseUpdate):
    """Update model for workspaces."""

    name: Optional[str] = Field(
        title="The unique name of the workspace. The workspace name must only "
        "contain only lowercase letters, numbers, underscores, and hyphens and "
        "be at most 50 characters long.",
        min_length=1,
        max_length=STR_ID_FIELD_MAX_LENGTH,
        pattern=r"^[a-z0-9_-]+$",
        default=None,
    )
    display_name: Optional[str] = Field(
        title="The display name of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )


# ------------------ Response Model ------------------


class WorkspaceResponseBody(BaseDatedResponseBody):
    """Response body for workspaces."""

    display_name: str = Field(
        title="The display name of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class WorkspaceResponseMetadata(BaseResponseMetadata):
    """Response metadata for workspaces."""

    description: str = Field(
        default="",
        title="The description of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class WorkspaceResponseResources(BaseResponseResources):
    """Class for all resource models associated with the workspace entity."""


class WorkspaceResponse(
    BaseIdentifiedResponse[
        WorkspaceResponseBody,
        WorkspaceResponseMetadata,
        WorkspaceResponseResources,
    ]
):
    """Response model for workspaces."""

    name: str = Field(
        title="The unique name of the workspace.",
        max_length=STR_ID_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "WorkspaceResponse":
        """Get the hydrated version of this workspace.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_workspace(self.id)

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


class WorkspaceFilter(BaseFilter):
    """Model to enable advanced filtering of all Workspaces."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the workspace",
    )

    display_name: Optional[str] = Field(
        default=None,
        description="Display name of the workspace",
    )
