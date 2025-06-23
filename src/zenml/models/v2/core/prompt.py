#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Models representing prompts."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    RunMetadataFilterMixin,
    TaggableFilter,
)
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

AnyQuery = TypeVar("AnyQuery", bound=Any)

# ------------------ Request Model ------------------


class PromptRequest(ProjectScopedRequest):
    """Prompt request model."""

    name: str = Field(
        title="Name of the prompt.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    template: str = Field(
        title="The prompt template.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    task: Optional[str] = Field(
        title="The task this prompt is designed for.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    domain: Optional[str] = Field(
        title="The domain this prompt is designed for.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    prompt_type: Optional[str] = Field(
        title="The type of prompt.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    tags: Optional[List[str]] = Field(
        title="Prompt tags.",
        description="Should be a list of plain strings, e.g., ['tag1', 'tag2']",
        default=None,
    )


# ------------------ Update Model ------------------


class PromptUpdate(BaseUpdate):
    """Prompt update model."""

    name: Optional[str] = None
    template: Optional[str] = None
    task: Optional[str] = None
    domain: Optional[str] = None
    prompt_type: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None


# ------------------ Response Model ------------------


class PromptResponseBody(ProjectScopedResponseBody):
    """Response body for prompts."""

    template: str = Field(
        title="The prompt template.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )


class PromptResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for prompts."""

    task: Optional[str] = Field(
        title="The task this prompt is designed for.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    domain: Optional[str] = Field(
        title="The domain this prompt is designed for.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )
    prompt_type: Optional[str] = Field(
        title="The type of prompt.",
        max_length=STR_FIELD_MAX_LENGTH,
        default=None,
    )


class PromptResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the Prompt Entity."""

    tags: List[TagResponse] = Field(
        title="Tags associated with the prompt.",
    )


class PromptResponse(
    ProjectScopedResponse[
        PromptResponseBody,
        PromptResponseMetadata,
        PromptResponseResources,
    ]
):
    """Prompt response model."""

    def get_hydrated_version(self) -> "PromptResponse":
        """Get the hydrated version of this prompt.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        # Note: This would need to be implemented when prompt endpoints are added
        # For now, return self as prompts work through the artifact system
        return self

    name: str = Field(
        title="Name of the prompt.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata properties
    @property
    def template(self) -> str:
        """The `template` property.

        Returns:
            the value of the property.
        """
        return self.get_body().template

    @property
    def task(self) -> Optional[str]:
        """The `task` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().task

    @property
    def domain(self) -> Optional[str]:
        """The `domain` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().domain

    @property
    def prompt_type(self) -> Optional[str]:
        """The `prompt_type` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().prompt_type

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags


# ------------------ Filter Model ------------------


class PromptFilter(ProjectScopedFilter, TaggableFilter, RunMetadataFilterMixin):
    """Model to enable advanced filtering of prompts."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
        *RunMetadataFilterMixin.FILTER_EXCLUDE_FIELDS,
    ]

    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *TaggableFilter.CLI_EXCLUDE_FIELDS,
    ]

    name: Optional[str] = None
    task: Optional[str] = None
    domain: Optional[str] = None
    prompt_type: Optional[str] = None 