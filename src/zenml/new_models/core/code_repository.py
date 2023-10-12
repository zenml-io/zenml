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


from typing import Any, Dict, Optional

from pydantic import Field

from zenml.config.source import Source
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.new_models.base import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseMetadata,
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


class CodeRepositoryResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata model for code repositories."""

    config: Dict[str, Any] = Field(
        description="Configuration for the code repository."
    )
    description: Optional[str] = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class CodeRepositoryResponse(WorkspaceScopedResponse):
    """Response model for code repositories."""

    # Entity fields
    name: str = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    source: Source = Field(description="The code repository source.")
    logo_url: Optional[str] = Field(
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository."
    )

    # Metadata related field, method and properties
    metadata: Optional["CodeRepositoryResponseMetadata"]

    def get_hydrated_version(self) -> "CodeRepositoryResponse":
        # TODO: Implement it with the parameterized calls
        from zenml.client import Client

        return Client().get_code_repository(self.id)

    @hydrated_property
    def config(self):
        """The config property."""
        return self.metadata.config

    @hydrated_property
    def description(self):
        """The description property."""
        return self.metadata.description
