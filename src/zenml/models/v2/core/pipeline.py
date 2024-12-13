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
"""Models representing pipelines."""

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
    SORT_PIPELINES_BY_LATEST_RUN_KEY,
    STR_FIELD_MAX_LENGTH,
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.enums import ExecutionStatus
from zenml.models.v2.base.base import BaseUpdate
from zenml.models.v2.base.scoped import (
    WorkspaceScopedRequest,
    WorkspaceScopedResponse,
    WorkspaceScopedResponseBody,
    WorkspaceScopedResponseMetadata,
    WorkspaceScopedResponseResources,
    WorkspaceScopedTaggableFilter,
)
from zenml.models.v2.core.tag import TagResponse

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, UserResponse
    from zenml.models.v2.core.pipeline_run import PipelineRunResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

AnyQuery = TypeVar("AnyQuery", bound=Any)

# ------------------ Request Model ------------------


class PipelineRequest(WorkspaceScopedRequest):
    """Request model for pipelines."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        default=None,
        title="The description of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    tags: Optional[List[str]] = Field(
        default=None,
        title="Tags of the pipeline.",
    )


# ------------------ Update Model ------------------


class PipelineUpdate(BaseUpdate):
    """Update model for pipelines."""

    description: Optional[str] = Field(
        default=None,
        title="The description of the pipeline.",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    add_tags: Optional[List[str]] = Field(
        default=None, title="New tags to add to the pipeline."
    )
    remove_tags: Optional[List[str]] = Field(
        default=None, title="Tags to remove from the pipeline."
    )


# ------------------ Response Model ------------------


class PipelineResponseBody(WorkspaceScopedResponseBody):
    """Response body for pipelines."""

    latest_run_id: Optional[UUID] = Field(
        default=None,
        title="The ID of the latest run of the pipeline.",
    )
    latest_run_status: Optional[ExecutionStatus] = Field(
        default=None,
        title="The status of the latest run of the pipeline.",
    )


class PipelineResponseMetadata(WorkspaceScopedResponseMetadata):
    """Response metadata for pipelines."""

    description: Optional[str] = Field(
        default=None,
        title="The description of the pipeline.",
    )


class PipelineResponseResources(WorkspaceScopedResponseResources):
    """Class for all resource models associated with the pipeline entity."""

    latest_run_user: Optional["UserResponse"] = Field(
        default=None,
        title="The user that created the latest run of this pipeline.",
    )
    tags: List[TagResponse] = Field(
        title="Tags associated with the pipeline.",
    )


class PipelineResponse(
    WorkspaceScopedResponse[
        PipelineResponseBody,
        PipelineResponseMetadata,
        PipelineResponseResources,
    ]
):
    """Response model for pipelines."""

    name: str = Field(
        title="The name of the pipeline.",
        max_length=STR_FIELD_MAX_LENGTH,
    )

    def get_hydrated_version(self) -> "PipelineResponse":
        """Get the hydrated version of this pipeline.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_pipeline(self.id)

    # Helper methods
    def get_runs(self, **kwargs: Any) -> List["PipelineRunResponse"]:
        """Get runs of this pipeline.

        Can be used to fetch runs other than `self.runs` and supports
        fine-grained filtering and pagination.

        Args:
            **kwargs: Further arguments for filtering or pagination that are
                passed to `client.list_pipeline_runs()`.

        Returns:
            List of runs of this pipeline.
        """
        from zenml.client import Client

        return Client().list_pipeline_runs(pipeline_id=self.id, **kwargs).items

    @property
    def runs(self) -> List["PipelineRunResponse"]:
        """Returns the 20 most recent runs of this pipeline in descending order.

        Returns:
            The 20 most recent runs of this pipeline in descending order.
        """
        return self.get_runs()

    @property
    def num_runs(self) -> int:
        """Returns the number of runs of this pipeline.

        Returns:
            The number of runs of this pipeline.
        """
        from zenml.client import Client

        return Client().list_pipeline_runs(pipeline_id=self.id, size=1).total

    @property
    def last_run(self) -> "PipelineRunResponse":
        """Returns the last run of this pipeline.

        Returns:
            The last run of this pipeline.

        Raises:
            RuntimeError: If no runs were found for this pipeline.
        """
        runs = self.get_runs(size=1)
        if not runs:
            raise RuntimeError(
                f"No runs found for pipeline '{self.name}' with id {self.id}."
            )
        return runs[0]

    @property
    def last_successful_run(self) -> "PipelineRunResponse":
        """Returns the last successful run of this pipeline.

        Returns:
            The last successful run of this pipeline.

        Raises:
            RuntimeError: If no successful runs were found for this pipeline.
        """
        runs = self.get_runs(status=ExecutionStatus.COMPLETED, size=1)
        if not runs:
            raise RuntimeError(
                f"No successful runs found for pipeline '{self.name}' with id "
                f"{self.id}."
            )
        return runs[0]

    @property
    def latest_run_id(self) -> Optional[UUID]:
        """The `latest_run_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_run_id

    @property
    def latest_run_status(self) -> Optional[ExecutionStatus]:
        """The `latest_run_status` property.

        Returns:
            the value of the property.
        """
        return self.get_body().latest_run_status

    @property
    def tags(self) -> List[TagResponse]:
        """The `tags` property.

        Returns:
            the value of the property.
        """
        return self.get_resources().tags


# ------------------ Filter Model ------------------


class PipelineFilter(WorkspaceScopedTaggableFilter):
    """Pipeline filter model."""

    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.CUSTOM_SORTING_OPTIONS,
        SORT_PIPELINES_BY_LATEST_RUN_KEY,
    ]
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedTaggableFilter.FILTER_EXCLUDE_FIELDS,
        "latest_run_status",
    ]

    name: Optional[str] = Field(
        default=None,
        description="Name of the Pipeline",
    )
    latest_run_status: Optional[str] = Field(
        default=None,
        description="Filter by the status of the latest run of a pipeline. "
        "This will always be applied as an `AND` filter for now.",
    )

    def apply_filter(
        self, query: AnyQuery, table: Type["AnySchema"]
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        query = super().apply_filter(query, table)

        from sqlmodel import and_, col, func, select

        from zenml.zen_stores.schemas import PipelineRunSchema, PipelineSchema

        if self.latest_run_status:
            latest_pipeline_run_subquery = (
                select(
                    PipelineRunSchema.pipeline_id,
                    func.max(PipelineRunSchema.created).label("created"),
                )
                .where(col(PipelineRunSchema.pipeline_id).is_not(None))
                .group_by(col(PipelineRunSchema.pipeline_id))
                .subquery()
            )

            query = (
                query.join(
                    PipelineRunSchema,
                    PipelineSchema.id == PipelineRunSchema.pipeline_id,
                )
                .join(
                    latest_pipeline_run_subquery,
                    and_(
                        PipelineRunSchema.pipeline_id
                        == latest_pipeline_run_subquery.c.pipeline_id,
                        PipelineRunSchema.created
                        == latest_pipeline_run_subquery.c.created,
                    ),
                )
                .where(
                    self.generate_custom_query_conditions_for_column(
                        value=self.latest_run_status,
                        table=PipelineRunSchema,
                        column="status",
                    )
                )
            )

        return query

    def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the query.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        from sqlmodel import asc, case, col, desc, func, select

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import PipelineRunSchema, PipelineSchema

        sort_by, operand = self.sorting_params

        if sort_by == SORT_PIPELINES_BY_LATEST_RUN_KEY:
            # Subquery to find the latest run per pipeline
            latest_run_subquery = (
                select(
                    PipelineRunSchema.pipeline_id,
                    case(
                        (
                            func.max(PipelineRunSchema.created).is_(None),
                            PipelineSchema.created,
                        ),
                        else_=func.max(PipelineRunSchema.created),
                    ).label("latest_run"),
                )
                .group_by(col(PipelineRunSchema.pipeline_id))
                .subquery()
            )

            # Join the subquery with the pipelines
            query = query.outerjoin(
                latest_run_subquery,
                PipelineSchema.id == latest_run_subquery.c.pipeline_id,
            )

            if operand == SorterOps.ASCENDING:
                query = query.order_by(
                    asc(latest_run_subquery.c.latest_run)
                ).order_by(col(PipelineSchema.id))
            else:
                query = query.order_by(
                    desc(latest_run_subquery.c.latest_run)
                ).order_by(col(PipelineSchema.id))

            return query
        else:
            return super().apply_sorting(query=query, table=table)
