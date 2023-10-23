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
"""Models representing code repositories."""

from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import Field

from zenml.config.source import Source
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
)
from zenml.models.v2.base.utils import (
    hydrated_property,
    update_model,
)

# ------------------ Request Model ------------------


class CodeRepositoryRequest(WorkspaceScopedRequest):
    """Request model for code repositories."""

    name: str = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    config: Dict[str, Any] = Field(
        description="Configuration for the code repository."
    )
    source: Source = Field(description="The code repository source.")
    logo_url: Optional[str] = Field(
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository."
    )
    description: Optional[str] = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


# ------------------ Update Model ------------------


@update_model
class CodeRepositoryUpdate(CodeRepositoryRequest):
    """Update model for code repositories."""


# ------------------ Response Model ------------------


class CodeRepositoryResponseBody(WorkspaceScopedResponseBody):
    """Response body for code repositories."""

    source: Source = Field(description="The code repository source.")
    logo_url: Optional[str] = Field(
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository."
    )


class CodeRepositoryResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for code repositories."""

    config: Dict[str, Any] = Field(
        description="Configuration for the code repository."
    )
    description: Optional[str] = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class CodeRepositoryResponse(WorkspaceScopedResponse):
    """Response model for code repositories."""

    name: str = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata pair
    body: "CodeRepositoryResponseBody"
    metadata: Optional["CodeRepositoryResponseMetadata"]

    def get_hydrated_version(self) -> "CodeRepositoryResponse":
        """Get the hydrated version of this code repository."""
        from zenml.client import Client

        return Client().zen_store.get_code_repository(self.id)

    # Body and metadata properties
    @property
    def source(self):
        """The `source` property."""
        return self.body.source

    @property
    def logo_url(self):
        """The `logo_url` property."""
        return self.body.logo_url

    @hydrated_property
    def config(self):
        """The `config` property."""
        return self.metadata.config

    @hydrated_property
    def description(self):
        """The `description` property."""
        return self.metadata.description


# ------------------ Filter Model ------------------


class CodeRepositoryFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all code repositories."""

    name: Optional[str] = Field(
        description="Name of the code repository.",
    )
    workspace_id: Union[UUID, str, None] = Field(
        description="Workspace of the code repository."
    )
    user_id: Union[UUID, str, None] = Field(
        description="User that created the code repository."
    )
