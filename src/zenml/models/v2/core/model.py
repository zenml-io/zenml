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

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    List,
    Optional,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import Field

from zenml.constants import (
    SORT_BY_LATEST_VERSION_KEY,
    STR_FIELD_MAX_LENGTH,
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    TaggableFilter,
)
from zenml.utils.pagination_utils import depaginate

if TYPE_CHECKING:
    from zenml.model.model import Model
    from zenml.models.v2.core.curated_visualization import (
        CuratedVisualizationResponse,
    )
    from zenml.models.v2.core.tag import TagResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

AnyQuery = TypeVar("AnyQuery", bound=Any)

# ------------------ Request Model ------------------


class ModelRequest(ProjectScopedRequest):
    """Request model for models."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    license: str | None = Field(
        title="The license model created under",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    description: str | None = Field(
        title="The description of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    audience: str | None = Field(
        title="The target audience of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    use_cases: str | None = Field(
        title="The use cases of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    limitations: str | None = Field(
        title="The know limitations of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    trade_offs: str | None = Field(
        title="The trade offs of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    ethics: str | None = Field(
        title="The ethical implications of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    tags: list[str] | None = Field(
        title="Tags associated with the model",
        default=None,
    )
    save_models_to_registry: bool = Field(
        title="Whether to save all ModelArtifacts to Model Registry",
        default=True,
    )


# ------------------ Update Model ------------------


class ModelUpdate(BaseUpdate):
    """Update model for models."""

    name: str | None = None
    license: str | None = None
    description: str | None = None
    audience: str | None = None
    use_cases: str | None = None
    limitations: str | None = None
    trade_offs: str | None = None
    ethics: str | None = None
    add_tags: list[str] | None = None
    remove_tags: list[str] | None = None
    save_models_to_registry: bool | None = None


# ------------------ Response Model ------------------


class ModelResponseBody(ProjectScopedResponseBody):
    """Response body for models."""


class ModelResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for models."""

    license: str | None = Field(
        title="The license model created under",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    description: str | None = Field(
        title="The description of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    audience: str | None = Field(
        title="The target audience of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    use_cases: str | None = Field(
        title="The use cases of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    limitations: str | None = Field(
        title="The know limitations of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    trade_offs: str | None = Field(
        title="The trade offs of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    ethics: str | None = Field(
        title="The ethical implications of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
        default=None,
    )
    save_models_to_registry: bool = Field(
        title="Whether to save all ModelArtifacts to Model Registry",
        default=True,
    )


class ModelResponseResources(ProjectScopedResponseResources):
    """Class for all resource models associated with the model entity."""

    tags: list["TagResponse"] = Field(
        title="Tags associated with the model",
    )
    latest_version_name: str | None = None
    latest_version_id: UUID | None = None
    visualizations: list["CuratedVisualizationResponse"] = Field(
        default_factory=list,
        title="Curated visualizations associated with the model.",
    )


class ModelResponse(
    ProjectScopedResponse[
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
    def tags(self) -> list["TagResponse"]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags

    @property
    def latest_version_name(self) -> str | None:
        """The `latest_version_name` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().latest_version_name

    @property
    def latest_version_id(self) -> UUID | None:
        """The `latest_version_id` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().latest_version_id

    @property
    def license(self) -> str | None:
        """The `license` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().license

    @property
    def description(self) -> str | None:
        """The `description` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().description

    @property
    def audience(self) -> str | None:
        """The `audience` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().audience

    @property
    def use_cases(self) -> str | None:
        """The `use_cases` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().use_cases

    @property
    def limitations(self) -> str | None:
        """The `limitations` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().limitations

    @property
    def trade_offs(self) -> str | None:
        """The `trade_offs` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().trade_offs

    @property
    def ethics(self) -> str | None:
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

    @property
    def visualizations(self) -> list["CuratedVisualizationResponse"]:
        """The `visualizations` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().visualizations

    # Helper functions
    @property
    def versions(self) -> list["Model"]:
        """List all versions of the model.

        Returns:
            The list of all model version.
        """
        from zenml.client import Client

        client = Client()
        model_versions = depaginate(
            client.list_model_versions,
            model_name_or_id=self.id,
            project=self.project_id,
        )
        return [
            mv.to_model_class(suppress_class_validation_warnings=True)
            for mv in model_versions
        ]


# ------------------ Filter Model ------------------


class ModelFilter(ProjectScopedFilter, TaggableFilter):
    """Model to enable advanced filtering of all models."""

    name: str | None = Field(
        default=None,
        description="Name of the Model",
    )

    FILTER_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *ProjectScopedFilter.FILTER_EXCLUDE_FIELDS,
        *TaggableFilter.FILTER_EXCLUDE_FIELDS,
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[list[str]] = [
        *ProjectScopedFilter.CUSTOM_SORTING_OPTIONS,
        *TaggableFilter.CUSTOM_SORTING_OPTIONS,
        SORT_BY_LATEST_VERSION_KEY,
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[list[str]] = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        *TaggableFilter.CLI_EXCLUDE_FIELDS,
    ]

    def apply_sorting(
        self,
        query: AnyQuery,
        table: type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the query for Models.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        from sqlmodel import asc, case, col, desc, func, select

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import (
            ModelSchema,
            ModelVersionSchema,
        )

        sort_by, operand = self.sorting_params

        if sort_by == SORT_BY_LATEST_VERSION_KEY:
            # Subquery to find the latest version per model
            latest_version_subquery = (
                select(
                    ModelSchema.id,
                    case(
                        (
                            func.max(ModelVersionSchema.created).is_(None),
                            ModelSchema.created,
                        ),
                        else_=func.max(ModelVersionSchema.created),
                    ).label("latest_version_created"),
                )
                .outerjoin(
                    ModelVersionSchema,
                    ModelSchema.id == ModelVersionSchema.model_id,  # type: ignore[arg-type]
                )
                .group_by(col(ModelSchema.id))
                .subquery()
            )

            query = query.add_columns(
                latest_version_subquery.c.latest_version_created,
            ).where(ModelSchema.id == latest_version_subquery.c.id)

            # Apply sorting based on the operand
            if operand == SorterOps.ASCENDING:
                query = query.order_by(
                    asc(latest_version_subquery.c.latest_version_created),
                    asc(ModelSchema.id),
                )
            else:
                query = query.order_by(
                    desc(latest_version_subquery.c.latest_version_created),
                    desc(ModelSchema.id),
                )
            return query

        # For other sorting cases, delegate to the parent class
        return super().apply_sorting(query=query, table=table)
