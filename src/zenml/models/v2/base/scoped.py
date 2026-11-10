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
"""Scoped model definitions."""

from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field, model_validator

from zenml.enums import GenericFilterOps, LogicalOperators
from zenml.logger import get_logger
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.filter import (
    AnyQuery,
    BaseFilter,
    StringFilterOption,
    UUIDFilterOption,
)

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement
    from sqlmodel.sql.expression import SelectOfScalar

    from zenml.models.v2.core.project import ProjectResponse
    from zenml.models.v2.core.user import UserResponse
    from zenml.zen_stores.schemas import (
        BaseSchema,
        RunMetadataResourceSchema,
        RunMetadataSchema,
        TagResourceSchema,
        TagSchema,
    )

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = get_logger(__name__)


# ---------------------- Request Models ----------------------


class UserScopedRequest(BaseRequest):
    """Base user-owned request model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: Optional[UUID] = Field(
        default=None,
        title="The id of the user that created this resource. Set "
        "automatically by the server.",
        # This field is set automatically by the server, so the client doesn't
        # need to set it and it will not be serialized.
        exclude=True,
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for user scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["user_id"] = self.user
        return metadata


class ProjectScopedRequest(UserScopedRequest):
    """Base project-scoped request domain model.

    Used as a base class for all domain models that are project-scoped.
    """

    project: UUID = Field(title="The project to which this resource belongs.")

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for project scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["project_id"] = self.project
        return metadata


# ---------------------- Response Models ----------------------


# User-scoped models
class UserScopedResponseBody(BaseDatedResponseBody):
    """Base user-owned body."""

    user_id: Optional[UUID] = Field(title="The user id.", default=None)


class UserScopedResponseMetadata(BaseResponseMetadata):
    """Base user-owned metadata."""


class UserScopedResponseResources(BaseResponseResources):
    """Base class for all resource models associated with the user."""

    user: Optional["UserResponse"] = Field(
        title="The user who created this resource.", default=None
    )


UserBody = TypeVar("UserBody", bound=UserScopedResponseBody)
UserMetadata = TypeVar("UserMetadata", bound=UserScopedResponseMetadata)
UserResources = TypeVar("UserResources", bound=UserScopedResponseResources)


class UserScopedResponse(
    BaseIdentifiedResponse[UserBody, UserMetadata, UserResources],
    Generic[UserBody, UserMetadata, UserResources],
):
    """Base user-owned model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    # Analytics
    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for user scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        if user_id := self.user_id:
            metadata["user_id"] = user_id
        return metadata

    # Body and metadata properties
    @property
    def user_id(self) -> Optional[UUID]:
        """The user ID property.

        Returns:
            the value of the property.
        """
        return self.get_body().user_id

    @property
    def user(self) -> Optional["UserResponse"]:
        """The user property.

        Returns:
            the value of the property.
        """
        return self.get_resources().user


class UserScopedFilter(BaseFilter):
    """Model to enable advanced user-based scoping."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "user",
        "scope_user",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "scope_user",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *BaseFilter.CUSTOM_SORTING_OPTIONS,
        "user",
    ]
    API_SINGLE_INPUT_PARAMS: ClassVar[List[str]] = [
        *BaseFilter.API_SINGLE_INPUT_PARAMS,
        "scope_user",
    ]

    scope_user: Optional[UUID] = Field(
        default=None,
        description="The user to scope this query to.",
    )
    user: UUIDFilterOption = Field(
        default=None,
        description="Name/ID of the user that created the entity.",
        union_mode="left_to_right",
    )

    def set_scope_user(self, user_id: UUID) -> None:
        """Set the user that is performing the filtering to scope the response.

        Args:
            user_id: The user ID to scope the response to.
        """
        self.scope_user = user_id

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        from sqlmodel import and_

        from zenml.zen_stores.schemas import UserSchema

        if self.user:
            user_values = (
                self.user if isinstance(self.user, list) else [self.user]
            )
            for user_value in user_values:
                custom_filters.append(
                    and_(
                        getattr(table, "user_id") == UserSchema.id,
                        self.generate_name_or_id_query_conditions(
                            value=user_value,
                            table=UserSchema,
                            additional_columns=["full_name"],
                        ),
                    )
                )

        return custom_filters

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
        from sqlmodel import asc, desc

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import UserSchema

        sort_by, operand = self.sorting_params

        if sort_by == "user":
            column = UserSchema.name

            query = query.outerjoin(
                UserSchema,
                getattr(table, "user_id") == UserSchema.id,
            )

            query = query.add_columns(UserSchema.name)

            if operand == SorterOps.ASCENDING:
                query = query.order_by(asc(column))
            else:
                query = query.order_by(desc(column))

            return query

        return super().apply_sorting(query=query, table=table)

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        query = super().apply_filter(query=query, table=table)

        if self.scope_user:
            query = query.where(getattr(table, "user_id") == self.scope_user)

        return query


# Project-scoped models


class ProjectScopedResponseBody(UserScopedResponseBody):
    """Base project-scoped body."""

    project_id: UUID = Field(title="The project id.")


class ProjectScopedResponseMetadata(UserScopedResponseMetadata):
    """Base project-scoped metadata."""


class ProjectScopedResponseResources(UserScopedResponseResources):
    """Base project-scoped resources."""


ProjectBody = TypeVar("ProjectBody", bound=ProjectScopedResponseBody)
ProjectMetadata = TypeVar(
    "ProjectMetadata", bound=ProjectScopedResponseMetadata
)
ProjectResources = TypeVar(
    "ProjectResources", bound=ProjectScopedResponseResources
)


class ProjectScopedResponse(
    UserScopedResponse[ProjectBody, ProjectMetadata, ProjectResources],
    Generic[ProjectBody, ProjectMetadata, ProjectResources],
):
    """Base project-scoped domain model.

    Used as a base class for all domain models that are project-scoped.
    """

    # Analytics
    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for project scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["project_id"] = self.project_id
        return metadata

    @property
    def project_id(self) -> UUID:
        """The project ID property.

        Returns:
            the value of the property.
        """
        return self.get_body().project_id

    # Helper
    @property
    def project(self) -> "ProjectResponse":
        """The project property.

        Returns:
            the value of the property.
        """
        from zenml.client import Client

        client = Client()

        try:
            active_project = client.active_project
        except Exception:
            active_project = None

        if active_project is not None and active_project.id == self.project_id:
            return active_project

        return client.get_project(self.project_id)


# ---------------------- Filter Models ----------------------


class ProjectScopedFilter(UserScopedFilter):
    """Model to enable advanced scoping with project."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
        "project",
    ]
    API_SINGLE_INPUT_PARAMS: ClassVar[List[str]] = [
        *UserScopedFilter.API_SINGLE_INPUT_PARAMS,
        "project",
    ]
    project: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the project which the search is scoped to. "
        "This field must always be set and is always applied in addition to "
        "the other filters, regardless of the value of the "
        "logical_operator field.",
        union_mode="left_to_right",
    )

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.

        Raises:
            ValueError: If the project scope is missing from the filter.
        """
        query = super().apply_filter(query=query, table=table)

        # The project scope must always be set and must be a UUID. If the
        # client sets this to a string, the server will try to resolve it to a
        # project ID.
        #
        # If not set by the client, the server will fall back to using the
        # user's default project or even the server's default project, if
        # they are configured. If this also fails to yield a project, this
        # method will raise a ValueError.
        #
        # See: SqlZenStore._set_filter_project_id

        if not self.project:
            raise ValueError("Project scope missing from the filter.")

        if not isinstance(self.project, UUID):
            raise ValueError(
                f"Project scope must be a UUID, got {type(self.project)}."
            )

        scope_filter = getattr(table, "project_id") == self.project
        query = query.where(scope_filter)

        return query


# MySQL flattens every EXISTS subquery of an AND filter into a semi-join, and
# the time it spends ordering the joined tables grows factorially with their
# number: with around ten tag or run metadata values, planning alone can
# outlast any request timeout. MariaDB plans such queries quickly, but its
# execution plans degrade in a similar way.
#
# Filters with at most this many tag and run metadata values in total keep a
# plain subquery per value: planning them is cheap, and the database can start
# from the most selective one. Larger AND filters keep a separate subquery
# only for exact tag names and tag presence checks, which also match the
# resource type of the links. MySQL resolves an exact tag name through the
# unique tag name index before it plans the join order, and with the resource
# type it looks up the link through its full index, so any number of them
# stays cheap to plan. All other values of such a filter are checked by one
# aggregated subquery per relationship, which is never flattened.
_MAX_VALUES_WITH_PLAIN_SUBQUERIES = 4
_TAG_PRESENCE_OPERATORS = (
    GenericFilterOps.IS_NULL,
    GenericFilterOps.IS_NOT_NULL,
)


def _unique_values(values: StringFilterOption) -> List[str]:
    """Get the distinct values of a filter option, keeping their order.

    Identical values are redundant under both AND and OR.

    Args:
        values: The filter option.

    Returns:
        The distinct values.
    """
    if values is None:
        return []
    return list(dict.fromkeys([values] if isinstance(values, str) else values))


def _aggregates_values(
    tags: StringFilterOption,
    run_metadata: StringFilterOption,
    logical_operator: LogicalOperators,
) -> bool:
    """Check whether a filter aggregates its tag and run metadata values.

    Args:
        tags: The tag values of the filter.
        run_metadata: The run metadata values of the filter.
        logical_operator: The operator combining the filter conditions.

    Returns:
        Whether only exact tag names and tag presence checks get their own
        subquery.
    """
    value_count = len(_unique_values(tags)) + len(_unique_values(run_metadata))
    return (
        logical_operator == LogicalOperators.AND
        and value_count > _MAX_VALUES_WITH_PLAIN_SUBQUERIES
    )


def _get_tag_resource_type(table: Type["AnySchema"]) -> str:
    """Get the resource type that tag links use for rows of a table.

    Args:
        table: The taggable table.

    Returns:
        The tag resource type.
    """
    from zenml.enums import TaggableResourceTypes
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        ArtifactVersionSchema,
        DeploymentSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineRunSchema,
        PipelineSchema,
        PipelineSnapshotSchema,
        RunTemplateSchema,
    )

    resource_type_mapping = {
        ArtifactSchema: TaggableResourceTypes.ARTIFACT,
        ArtifactVersionSchema: TaggableResourceTypes.ARTIFACT_VERSION,
        ModelSchema: TaggableResourceTypes.MODEL,
        ModelVersionSchema: TaggableResourceTypes.MODEL_VERSION,
        PipelineSchema: TaggableResourceTypes.PIPELINE,
        PipelineRunSchema: TaggableResourceTypes.PIPELINE_RUN,
        RunTemplateSchema: TaggableResourceTypes.RUN_TEMPLATE,
        PipelineSnapshotSchema: TaggableResourceTypes.PIPELINE_SNAPSHOT,
        DeploymentSchema: TaggableResourceTypes.DEPLOYMENT,
    }
    return resource_type_mapping[table].value


def _generate_link_conditions(
    table: Type["AnySchema"],
    link_table: Union[
        Type["TagResourceSchema"], Type["RunMetadataResourceSchema"]
    ],
    target_table: Union[Type["TagSchema"], Type["RunMetadataSchema"]],
    on_clause: "ColumnElement[bool]",
    resource_type: str,
    predicates: List["ColumnElement[bool]"],
    logical_operator: LogicalOperators,
    separate_count: int,
    plain_separate_subqueries: bool = False,
) -> List["ColumnElement[bool]"]:
    """Generate conditions on the rows linked to rows of a table.

    A row of the queried table satisfies a predicate if at least one of the
    rows linked to it matches the predicate.

    Args:
        table: The queried table.
        link_table: The table linking rows of the queried table to rows of
            the target table.
        target_table: The table that the predicates apply to.
        on_clause: The join condition of the link and target tables.
        resource_type: The resource type of the queried table in the link
            table.
        predicates: The predicates on rows of the target table.
        logical_operator: The operator combining the conditions.
        separate_count: How many of the leading predicates get their own
            subquery when combined with AND. All others are checked by a
            single subquery, which is only equivalent under AND, so every
            predicate gets its own subquery when combined with OR.
        plain_separate_subqueries: Whether the separate subqueries select
            all columns of the links and leave out their resource type. Both
            change which plan MySQL picks for predicates that it cannot
            resolve before planning: it keeps no statistics on the resource
            type and assumes that it rules out most links, which can make it
            scan all of them, and a narrower select list can make it scan all
            queried rows to sort them. Resource IDs are unique across
            resource types, so leaving it out does not change the result.

    Returns:
        The conditions.
    """
    from sqlalchemy import case, func
    from sqlmodel import col, exists, select

    if logical_operator == LogicalOperators.OR:
        separate_count = len(predicates)

    links_of_row = (
        col(link_table.resource_id) == table.id,
        col(link_table.resource_type) == resource_type,
    )
    separate_query: "SelectOfScalar[Any]"
    if plain_separate_subqueries:
        separate_query = select(link_table).where(links_of_row[0])
    else:
        separate_query = select(col(link_table.id)).where(*links_of_row)
    conditions: List["ColumnElement[bool]"] = [
        exists(separate_query.join(target_table, on_clause).where(predicate))
        for predicate in predicates[:separate_count]
    ]

    if aggregated_predicates := predicates[separate_count:]:
        conditions.append(
            exists(
                select(col(link_table.resource_id))
                .join(target_table, on_clause)
                .where(*links_of_row)
                .group_by(col(link_table.resource_id))
                .having(
                    *(
                        func.max(case((predicate, 1), else_=0)) == 1
                        for predicate in aggregated_predicates
                    )
                )
            )
        )

    return conditions


class TaggableFilter(BaseFilter):
    """Model to enable filtering and sorting by tags."""

    tags: StringFilterOption = Field(
        description="Tags to apply to the filter query.", default=None
    )

    CLI_EXCLUDE_FIELDS = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
    ]
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "tags",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *BaseFilter.CUSTOM_SORTING_OPTIONS,
        "tags",
    ]

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom tag filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        if tag_values := _unique_values(self.tags):
            from sqlmodel import col, exists, select

            from zenml.zen_stores.schemas import TagResourceSchema, TagSchema

            resource_type = _get_tag_resource_type(table)
            aggregate = _aggregates_values(
                tags=self.tags,
                run_metadata=self.run_metadata
                if isinstance(self, RunMetadataFilterMixin)
                else None,
                logical_operator=self.logical_operator,
            )
            generate_tag_conditions = partial(
                _generate_link_conditions,
                table=table,
                link_table=TagResourceSchema,
                target_table=TagSchema,
                on_clause=col(TagSchema.id) == col(TagResourceSchema.tag_id),
                resource_type=resource_type,
                logical_operator=self.logical_operator,
            )
            exact_predicates: List["ColumnElement[bool]"] = []
            other_predicates: List["ColumnElement[bool]"] = []
            for tag in tag_values:
                _, operator = self._resolve_operator(tag)
                if operator in _TAG_PRESENCE_OPERATORS:
                    tag_links: "SelectOfScalar[Any]"
                    if aggregate:
                        tag_links = select(col(TagResourceSchema.id)).where(
                            col(TagResourceSchema.resource_type)
                            == resource_type
                        )
                    else:
                        tag_links = select(TagResourceSchema)
                    is_tagged = exists(
                        tag_links.where(
                            col(TagResourceSchema.resource_id) == table.id
                        )
                    )
                    custom_filters.append(
                        ~is_tagged
                        if operator == GenericFilterOps.IS_NULL
                        else is_tagged
                    )
                    continue

                predicate = self.generate_custom_query_conditions_for_column(
                    value=tag, table=TagSchema, column="name"
                )
                if not aggregate:
                    custom_filters.extend(
                        generate_tag_conditions(
                            predicates=[predicate],
                            separate_count=1,
                            plain_separate_subqueries=True,
                        )
                    )
                elif operator == GenericFilterOps.EQUALS:
                    exact_predicates.append(predicate)
                else:
                    other_predicates.append(predicate)

            custom_filters.extend(
                generate_tag_conditions(
                    predicates=exact_predicates,
                    separate_count=len(exact_predicates),
                )
            )
            custom_filters.extend(
                generate_tag_conditions(
                    predicates=other_predicates, separate_count=0
                )
            )

        return custom_filters

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
        sort_by, operand = self.sorting_params

        if sort_by == "tags":
            from sqlmodel import asc, desc, func, select

            from zenml.enums import SorterOps
            from zenml.zen_stores.schemas import TagResourceSchema, TagSchema

            sorted_tags = (
                select(TagResourceSchema.resource_id, TagSchema.name)
                .join(TagSchema, TagResourceSchema.tag_id == TagSchema.id)  # type: ignore[arg-type]
                .filter(
                    TagResourceSchema.resource_type  # type: ignore[arg-type]
                    == _get_tag_resource_type(table)
                )
                .order_by(
                    asc(TagResourceSchema.resource_id), asc(TagSchema.name)
                )
            ).alias("sorted_tags")

            tags_subquery = (
                select(
                    sorted_tags.c.resource_id,
                    func.group_concat(sorted_tags.c.name, ", ").label(
                        "tags_list"
                    ),
                ).group_by(sorted_tags.c.resource_id)
            ).alias("tags_subquery")

            query = query.add_columns(tags_subquery.c.tags_list).outerjoin(
                tags_subquery, table.id == tags_subquery.c.resource_id
            )

            # Apply ordering based on the tags list
            if operand == SorterOps.ASCENDING:
                query = query.order_by(asc("tags_list"))
            else:
                query = query.order_by(desc("tags_list"))

            return query

        return super().apply_sorting(query=query, table=table)


class RunMetadataFilterMixin(BaseFilter):
    """Model to enable filtering and sorting by run metadata."""

    run_metadata: StringFilterOption = Field(
        default=None,
        description="The run_metadata to filter the pipeline runs by.",
    )
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "run_metadata",
    ]

    @model_validator(mode="after")
    def validate_run_metadata_format(self) -> "RunMetadataFilterMixin":
        """Validates that run_metadata entries are in the correct format.

        Each run_metadata entry must be in one of the following formats:
        1. "key:value" - Direct equality comparison (key equals value)
        2. "key:filterop:value" - Where filterop is one of the GenericFilterOps:
           - equals: Exact match
           - notequals: Not equal to
           - contains: String contains value
           - notcontains: String does not contain value
           - startswith: String starts with value
           - endswith: String ends with value
           - oneof: Value is one of the specified options
           - notoneof: Value is not one of the specified options
           - isnull: Value is null
           - isnotnull: Value is not null
           - gte: Greater than or equal to
           - gt: Greater than
           - lte: Less than or equal to
           - lt: Less than
           - in: Value is in a list

        Examples:
        - "status:completed" - Find entries where status equals "completed"
        - "name:contains:test" - Find entries where name contains "test"
        - "duration:gt:10" - Find entries where duration is greater than 10

        Returns:
            self

        Raises:
            ValueError: If any entry in run_metadata does not contain a colon.
        """
        if self.run_metadata:
            entries = (
                [self.run_metadata]
                if isinstance(self.run_metadata, str)
                else self.run_metadata
            )
            for entry in entries:
                if ":" not in entry:
                    raise ValueError(
                        f"Invalid run_metadata entry format: '{entry}'. "
                        "Entry must be in format 'key:value' for direct "
                        "equality comparison or 'key:filterop:value' where "
                        "filterop is one of: equals, notequals, "
                        f"contains, notcontains, startswith, endswith, "
                        f"oneof, notoneof, isnull, isnotnull, gte, gt, "
                        f"lte, lt, in."
                    )
        return self

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom run metadata filters.

        Args:
            table: The query table.

        Returns:
            A list of custom filters.
        """
        custom_filters = super().get_custom_filters(table)

        if self.run_metadata is not None:
            from sqlmodel import and_, col

            from zenml.enums import MetadataResourceTypes
            from zenml.zen_stores.schemas import (
                ArtifactVersionSchema,
                ModelVersionSchema,
                PipelineRunSchema,
                RunMetadataResourceSchema,
                RunMetadataSchema,
                RunWaitConditionSchema,
                ScheduleSchema,
                StepRunSchema,
            )

            resource_type_mapping = {
                ArtifactVersionSchema: MetadataResourceTypes.ARTIFACT_VERSION,
                ModelVersionSchema: MetadataResourceTypes.MODEL_VERSION,
                PipelineRunSchema: MetadataResourceTypes.PIPELINE_RUN,
                RunWaitConditionSchema: MetadataResourceTypes.WAIT_CONDITION,
                StepRunSchema: MetadataResourceTypes.STEP_RUN,
                ScheduleSchema: MetadataResourceTypes.SCHEDULE,
            }

            predicates = []
            for entry in _unique_values(self.run_metadata):
                # Split at the first colon to get the key
                key, value = entry.split(":", 1)
                predicates.append(
                    and_(
                        self.generate_custom_query_conditions_for_column(
                            value=key,
                            table=RunMetadataSchema,
                            column="key",
                        ),
                        self.generate_custom_query_conditions_for_column(
                            value=value,
                            table=RunMetadataSchema,
                            column="value",
                        ),
                    )
                )

            aggregate = _aggregates_values(
                tags=self.tags if isinstance(self, TaggableFilter) else None,
                run_metadata=self.run_metadata,
                logical_operator=self.logical_operator,
            )
            custom_filters.extend(
                _generate_link_conditions(
                    table=table,
                    link_table=RunMetadataResourceSchema,
                    target_table=RunMetadataSchema,
                    on_clause=col(RunMetadataSchema.id)
                    == col(RunMetadataResourceSchema.run_metadata_id),
                    resource_type=resource_type_mapping[table].value,
                    predicates=predicates,
                    logical_operator=self.logical_operator,
                    separate_count=0 if aggregate else len(predicates),
                )
            )

        return custom_filters
