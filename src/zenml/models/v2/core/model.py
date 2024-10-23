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
"""Models representing models."""

from typing import TYPE_CHECKING, ClassVar, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
from zenml.models.v2.base.scoped import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
    WorkspaceScopedTaggableFilter,
)
from zenml.utils.pagination_utils import depaginate

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.model.model import Model
    from zenml.models.v2.core.tag import TagResponse

# ------------------ Request Model ------------------


class ModelRequest(WorkspaceScopedRequest):
    """Request model for models."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    license: Optional[str] = Field(
        title="The license model created under",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    audience: Optional[str] = Field(
        title="The target audience of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    use_cases: Optional[str] = Field(
        title="The use cases of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    limitations: Optional[str] = Field(
        title="The know limitations of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    trade_offs: Optional[str] = Field(
        title="The trade offs of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    ethics: Optional[str] = Field(
        title="The ethical implications of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    tags: Optional[List[str]] = Field(
        title="Tags associated with the model",
        default=None,
    )
    save_models_to_registry: bool = Field(
        title="Whether to save all ModelArtifacts to Model Registry",
        default=True,
    )


# ------------------ Update Model ------------------


class ModelUpdate(BaseModel):
    """Update model for models."""

    name: Optional[str] = None
    license: Optional[str] = None
    description: Optional[str] = None
    audience: Optional[str] = None
    use_cases: Optional[str] = None
    limitations: Optional[str] = None
    trade_offs: Optional[str] = None
    ethics: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None
    save_models_to_registry: Optional[bool] = None


# ------------------ Response Model ------------------


class ModelResponseBody(WorkspaceScopedResponseBody):
    """Response body for models."""

    tags: List["TagResponse"] = Field(
        title="Tags associated with the model",
    )
    latest_version_name: Optional[str] = None
    latest_version_id: Optional[UUID] = None


class ModelResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for models."""

    license: Optional[str] = Field(
        title="The license model created under",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    description: Optional[str] = Field(
        title="The description of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    audience: Optional[str] = Field(
        title="The target audience of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    use_cases: Optional[str] = Field(
        title="The use cases of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    limitations: Optional[str] = Field(
        title="The know limitations of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    trade_offs: Optional[str] = Field(
        title="The trade offs of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    ethics: Optional[str] = Field(
        title="The ethical implications of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    save_models_to_registry: bool = Field(
        title="Whether to save all ModelArtifacts to Model Registry",
        default=True,
    )


class ModelResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the model entity."""


class ModelResponse(
    WorkspaceScopedResponse[
        ModelResponseBody, ModelResponseMetadata, ModelResponseResources
    ]
):
    """Response model for models."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "ModelResponse":
        """Get the hydrated version of this model.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_model(self.id)

    # Body and metadata properties
    @property
    def tags(self) -> List["TagResponse"]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_body().tags

    @property
    def latest_version_name(self) -> Optional[str]:
        """The `latest_version_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_version_name

    @property
    def latest_version_id(self) -> Optional[UUID]:
        """The `latest_version_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_version_id

    @property
    def license(self) -> Optional[str]:
        """The `license` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().license

    @property
    def description(self) -> Optional[str]:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def audience(self) -> Optional[str]:
        """The `audience` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().audience

    @property
    def use_cases(self) -> Optional[str]:
        """The `use_cases` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().use_cases

    @property
    def limitations(self) -> Optional[str]:
        """The `limitations` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().limitations

    @property
    def trade_offs(self) -> Optional[str]:
        """The `trade_offs` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().trade_offs

    @property
    def ethics(self) -> Optional[str]:
        """The `ethics` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().ethics

    @property
    def save_models_to_registry(self) -> bool:
        """The `save_models_to_registry` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().save_models_to_registry

    # Helper functions
    @property
    def versions(self) -> List["Model"]:
        """List all versions of the model.

        Returns:
            The list of all model version.
        """
        from zenml.client import Client

        client = Client()
        model_versions = depaginate(
            client.list_model_versions, model_name_or_id=self.id
        )
        return [
            mv.to_model_class(suppress_class_validation_warnings=True)
            for mv in model_versions
        ]


# ------------------ Filter Model ------------------


class ModelFilter(WorkspaceScopedTaggableFilter):
    """Model to enable advanced filtering of all Workspaces."""

    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.CLI_EXCLUDE_FIELDS,
        "workspace_id",
        "user_id",
    ]
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.FILTER_EXCLUDE_FIELDS,
        "user",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the Model",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Workspace of the Model",
        union_mode="left_to_right",
    )
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="User of the Model",
        union_mode="left_to_right",
    )
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the model.",
    )

    def get_custom_filters(
        self,
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters()

        from sqlmodel import and_

        from zenml.zen_stores.schemas import (
            ModelSchema,
            UserSchema,
        )

        if self.user:
            user_filter = and_(
                ModelSchema.user_id == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user, table=UserSchema, additional_columns=["full_name"],
                ),
            )
            custom_filters.append(user_filter)

        return custom_filters
