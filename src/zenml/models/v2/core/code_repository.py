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

from typing import Any

from pydantic import Field

from zenml.config.source import Source, SourceWithValidator
from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)

# ------------------ Request Model ------------------


class CodeRepositoryRequest(ProjectScopedRequest):
    """Request model for code repositories."""

    name: str = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    config: dict[str, Any] = Field(
        description="Configuration for the code repository."
    )
    source: Source = Field(description="The code repository source.")
    logo_url: str | None = Field(
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository.",
        default=None,
    )
    description: str | None = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )


# ------------------ Update Model ------------------


class CodeRepositoryUpdate(BaseUpdate):
    """Update model for code repositories."""

    name: str | None = Field(
        title="The name of the code repository.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    config: dict[str, Any] | None = Field(
        description="Configuration for the code repository.",
        default=None,
    )
    source: SourceWithValidator | None = Field(
        description="The code repository source.", default=None
    )
    logo_url: str | None = Field(
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository.",
        default=None,
    )
    description: str | None = Field(
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )


# ------------------ Response Model ------------------


class CodeRepositoryResponseBody(ProjectScopedResponseBody):
    """Response body for code repositories."""

    source: Source = Field(description="The code repository source.")
    logo_url: str | None = Field(
        default=None,
        description="Optional URL of a logo (png, jpg or svg) for the "
        "code repository.",
    )


class CodeRepositoryResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for code repositories."""

    config: dict[str, Any] = Field(
        description="Configuration for the code repository."
    )
    description: str | None = Field(
        default=None,
        description="Code repository description.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class CodeRepositoryResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the code repository entity."""


class CodeRepositoryResponse(
    ProjectScopedResponse[
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
    def logo_url(self) -> str | None:
        """The `logo_url` property.

        Returns:
            the value of the property.
        """
        return self.get_body().logo_url

    @property
    def config(self) -> dict[str, Any]:
        """The `config` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().config

    @property
    def description(self) -> str | None:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description


# ------------------ Filter Model ------------------


class CodeRepositoryFilter(ProjectScopedFilter):
    """Model to enable advanced filtering of all code repositories."""

    name: str | None = Field(
        description="Name of the code repository.",
        default=None,
    )
