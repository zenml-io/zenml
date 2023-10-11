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
from zenml.new_models.base import (
    BaseRequestModel,
    BaseResponseModel,
    BaseResponseModelMetadata,
    hydrated_property,
    update_model,
)

# ------------------ Request Model ------------------


class WorkspaceRequest(BaseRequestModel):
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


class WorkspaceResponseMetadata(BaseResponseModelMetadata):
    """Response metadata model for workspaces."""

    description: str = Field(
        default="",
        title="The description of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )


class WorkspaceResponse(BaseResponseModel):
    """Response model for workspaces."""

    # Entity fields
    name: str = Field(
        title="The unique name of the workspace.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Metadata related field, method and properties
    metadata: Optional["WorkspaceResponseMetadata"]

    def get_hydrated_version(self) -> "WorkspaceResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_workspace(self.id, hydrate=True)

    @hydrated_property
    def description(self):
        """The description property."""
        return self.metadata.description
