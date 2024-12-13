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

from zenml.config.source import Source, SourceWithValidator
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedFilter,
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
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
        "code repository.",
        default=None,
    )
    description: Optional[str] = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )


# ------------------ Update Model ------------------


class CodeRepositoryUpdate(BaseUpdate):
    """Update model for code repositories."""

    name: Optional[str] = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    config: Optional[Dict[str, Any]] = Field(
        description="Configuration for the code repository.",
        default=None,
    )
    source: Optional[SourceWithValidator] = Field(
        description="The code repository source.", default=None
    )
    logo_url: Optional[str] = Field(
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository.",
        default=None,
    )
    description: Optional[str] = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )


# ------------------ Response Model ------------------


class CodeRepositoryResponseBody(WorkspaceScopedResponseBody):
    """Response body for code repositories."""

    source: Source = Field(description="The code repository source.")
    logo_url: Optional[str] = Field(
        default=None,
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository.",
    )


class CodeRepositoryResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for code repositories."""

    config: Dict[str, Any] = Field(
        description="Configuration for the code repository."
    )
    description: Optional[str] = Field(
        default=None,
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class CodeRepositoryResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the code repository entity."""


class CodeRepositoryResponse(
    WorkspaceScopedResponse[
        CodeRepositoryResponseBody,
        CodeRepositoryResponseMetadata,
        CodeRepositoryResponseResources,
    ]
):
    """Response model for code repositories."""

    name: str = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "CodeRepositoryResponse":
        """Get the hydrated version of this code repository.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_code_repository(self.id)

    # Body and metadata properties
    @property
    def source(self) -> Source:
        """The `source` property.

        Returns:
            the value of the property.
        """
        return self.get_body().source

    @property
    def logo_url(self) -> Optional[str]:
        """The `logo_url` property.

        Returns:
            the value of the property.
        """
        return self.get_body().logo_url

    @property
    def config(self) -> Dict[str, Any]:
        """The `config` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description


# ------------------ Filter Model ------------------


class CodeRepositoryFilter(WorkspaceScopedFilter):
    """Model to enable advanced filtering of all code repositories."""

    name: Optional[str] = Field(
        description="Name of the code repository.",
        default=None,
    )
