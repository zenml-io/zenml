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
"""Models representing artifacts."""

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
)
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.constants import SORT_BY_LATEST_VERSION_KEY, STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.scoped import WorkspaceScopedTaggableFilter
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

AnyQuery = TypeVar("AnyQuery", bound=Any)

# ------------------ Request Model ------------------


class ArtifactRequest(BaseRequest):
    """Artifact request model."""

    name: str = Field(
        title="Name of the artifact.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    has_custom_name: bool = Field(
        title="Whether the name is custom (True) or auto-generated (False).",
        default=False,
    )
    tags: Optional[List[str]] = Field(
        title="Artifact tags.",
        description="Should be a list of plain strings, e.g., ['tag1', 'tag2']",
        default=None,
    )


# ------------------ Update Model ------------------


class ArtifactUpdate(BaseModel):
    """Artifact update model."""

    name: Optional[str] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None
    has_custom_name: Optional[bool] = None


# ------------------ Response Model ------------------


class ArtifactResponseBody(BaseDatedResponseBody):
    """Response body for artifacts."""

    tags: List[TagResponse] = Field(
        title="Tags associated with the model",
    )
    latest_version_name: Optional[str] = None
    latest_version_id: Optional[UUID] = None


class ArtifactResponseMetadata(BaseResponseMetadata):
    """Response metadata for artifacts."""

    has_custom_name: bool = Field(
        title="Whether the name is custom (True) or auto-generated (False).",
        default=False,
    )


class ArtifactResponseResources(BaseResponseResources):
    """Class for all resource models associated with the Artifact Entity."""


class ArtifactResponse(
    BaseIdentifiedResponse[
        ArtifactResponseBody,
        ArtifactResponseMetadata,
        ArtifactResponseResources,
    ]
):
    """Artifact response model."""

    def get_hydrated_version(self) -> "ArtifactResponse":
        """Get the hydrated version of this artifact.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_artifact(self.id)

    name: str = Field(
        title="Name of the output in the parent step.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    # Body and metadata properties
    @property
    def tags(self) -> List[TagResponse]:
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
    def has_custom_name(self) -> bool:
        """The `has_custom_name` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().has_custom_name

    # Helper methods
    @property
    def versions(self) -> Dict[str, "ArtifactVersionResponse"]:
        """Get a list of all versions of this artifact.

        Returns:
            A list of all versions of this artifact.
        """
        from zenml.client import Client

        responses = Client().list_artifact_versions(name=self.name)
        return {str(response.version): response for response in responses}


# ------------------ Filter Model ------------------


class ArtifactFilter(WorkspaceScopedTaggableFilter):
    """Model to enable advanced filtering of artifacts."""

    name: Optional[str] = None
    has_custom_name: Optional[bool] = None

    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.CUSTOM_SORTING_OPTIONS,
        SORT_BY_LATEST_VERSION_KEY,
    ]

    def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the query for Artifacts.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        from sqlmodel import asc, case, col, desc, func, select

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import (
            ArtifactSchema,
            ArtifactVersionSchema,
        )

        sort_by, operand = self.sorting_params

        if sort_by == SORT_BY_LATEST_VERSION_KEY:
            # Subquery to find the latest version per artifact
            latest_version_subquery = (
                select(
                    ArtifactSchema.id,
                    case(
                        (
                            func.max(ArtifactVersionSchema.created).is_(None),
                            ArtifactSchema.created,
                        ),
                        else_=func.max(ArtifactVersionSchema.created),
                    ).label("latest_version_created"),
                )
                .outerjoin(
                    ArtifactVersionSchema,
                    ArtifactSchema.id == ArtifactVersionSchema.artifact_id,  # type: ignore[arg-type]
                )
                .group_by(col(ArtifactSchema.id))
                .subquery()
            )

            query = query.add_columns(
                latest_version_subquery.c.latest_version_created,
            ).where(ArtifactSchema.id == latest_version_subquery.c.id)

            # Apply sorting based on the operand
            if operand == SorterOps.ASCENDING:
                query = query.order_by(
                    asc(latest_version_subquery.c.latest_version_created),
                    asc(ArtifactSchema.id),
                )
            else:
                query = query.order_by(
                    desc(latest_version_subquery.c.latest_version_created),
                    desc(ArtifactSchema.id),
                )
            return query

        # For other sorting cases, delegate to the parent class
        return super().apply_sorting(query=query, table=table)
