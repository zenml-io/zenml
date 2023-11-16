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

from typing import Optional

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.filter import BaseFilter
from zenml.models.v2.base.update import update_model

# ------------------ Request Model ------------------


class WorkspaceRequest(BaseRequest):
    """Request model for workspaces."""

    name: str = Field(
        title="The unique name of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: str = Field(
        default="",
        title="The description of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


# ------------------ Update Model ------------------


@update_model
class WorkspaceUpdate(WorkspaceRequest):
    """Update model for workspaces."""


# ------------------ Response Model ------------------


class WorkspaceResponseBody(BaseResponseBody):
    """Response body for workspaces."""


class WorkspaceResponseMetadata(BaseResponseMetadata):
    """Response metadata for workspaces."""

    description: str = Field(
        default="",
        title="The description of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class WorkspaceResponse(
    BaseResponse[WorkspaceResponseBody, WorkspaceResponseMetadata]
):
    """Response model for workspaces."""

    name: str = Field(
        title="The unique name of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
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
