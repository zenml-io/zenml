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

from zenml.logger import get_logger
from zenml.models.v2.base.base import (
    BaseDatedResponseBody,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponseMetadata,
    BaseResponseResources,
)
from zenml.models.v2.base.filter import AnyQuery, BaseFilter

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.models.v2.core.project import ProjectResponse
    from zenml.models.v2.core.user import UserResponse
    from zenml.zen_stores.schemas import BaseSchema

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

    scope_user: Optional[UUID] = Field(
        default=None,
        description="The user to scope this query to.",
    )
    user: Optional[Union[UUID, str]] = Field(
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
            user_filter = and_(
                getattr(table, "user_id") == UserSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.user,
                    table=UserSchema,
                    additional_columns=["full_name"],
                ),
            )
            custom_filters.append(user_filter)

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

        return Client().get_project(self.project_id)


# ---------------------- Filter Models ----------------------


class ProjectScopedFilter(UserScopedFilter):
    """Model to enable advanced scoping with project."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
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


class TaggableFilter(BaseFilter):
    """Model to enable filtering and sorting by tags."""

    tag: Optional[str] = Field(
        description="Tag to apply to the filter query.", default=None
    )
    tags: Optional[List[str]] = Field(
        description="Tags to apply to the filter query.", default=None
    )

    CLI_EXCLUDE_FIELDS = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
    ]
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "tag",
        "tags",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *BaseFilter.CUSTOM_SORTING_OPTIONS,
        "tags",
    ]
    API_MULTI_INPUT_PARAMS: ClassVar[List[str]] = [
        *BaseFilter.API_MULTI_INPUT_PARAMS,
        "tags",
    ]

    @model_validator(mode="after")
    def add_tag_to_tags(self) -> "TaggableFilter":
        """Deprecated the tag attribute in favor of the tags attribute.

        Returns:
            self
        """
        if self.tag is not None:
            logger.warning(
                "The `tag` attribute is deprecated in favor of the `tags` attribute. "
                "Please update your code to use the `tags` attribute instead."
            )
            if self.tags is not None:
                self.tags.append(self.tag)
            else:
                self.tags = [self.tag]

            self.tag = None

        return self

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
        from zenml.zen_stores.schemas import TagResourceSchema, TagSchema

        query = super().apply_filter(query=query, table=table)

        if self.tags:
            query = query.join(
                TagResourceSchema,
                TagResourceSchema.resource_id == getattr(table, "id"),
            ).join(TagSchema, TagSchema.id == TagResourceSchema.tag_id)

        return query

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

        if self.tags:
            from sqlmodel import exists, select

            from zenml.zen_stores.schemas import TagResourceSchema, TagSchema

            for tag in self.tags:
                condition = self.generate_custom_query_conditions_for_column(
                    value=tag, table=TagSchema, column="name"
                )
                exists_subquery = exists(
                    select(TagResourceSchema)
                    .join(TagSchema, TagSchema.id == TagResourceSchema.tag_id)  # type: ignore[arg-type]
                    .where(
                        TagResourceSchema.resource_id == table.id, condition
                    )
                )
                custom_filters.append(exists_subquery)

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

            from zenml.enums import SorterOps, TaggableResourceTypes
            from zenml.zen_stores.schemas import (
                ArtifactSchema,
                ArtifactVersionSchema,
                ModelSchema,
                ModelVersionSchema,
                PipelineRunSchema,
                PipelineSchema,
                RunTemplateSchema,
                TagResourceSchema,
                TagSchema,
            )

            resource_type_mapping = {
                ArtifactSchema: TaggableResourceTypes.ARTIFACT,
                ArtifactVersionSchema: TaggableResourceTypes.ARTIFACT_VERSION,
                ModelSchema: TaggableResourceTypes.MODEL,
                ModelVersionSchema: TaggableResourceTypes.MODEL_VERSION,
                PipelineSchema: TaggableResourceTypes.PIPELINE,
                PipelineRunSchema: TaggableResourceTypes.PIPELINE_RUN,
                RunTemplateSchema: TaggableResourceTypes.RUN_TEMPLATE,
            }

            sorted_tags = (
                select(TagResourceSchema.resource_id, TagSchema.name)
                .join(TagSchema, TagResourceSchema.tag_id == TagSchema.id)  # type: ignore[arg-type]
                .filter(
                    TagResourceSchema.resource_type  # type: ignore[arg-type]
                    == resource_type_mapping[table]
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

    run_metadata: Optional[List[str]] = Field(
        default=None,
        description="The run_metadata to filter the pipeline runs by.",
    )
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "run_metadata",
    ]
    API_MULTI_INPUT_PARAMS: ClassVar[List[str]] = [
        *BaseFilter.API_MULTI_INPUT_PARAMS,
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
           - startswith: String starts with value
           - endswith: String ends with value
           - oneof: Value is one of the specified options
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
            for entry in self.run_metadata:
                if ":" not in entry:
                    raise ValueError(
                        f"Invalid run_metadata entry format: '{entry}'. "
                        "Entry must be in format 'key:value' for direct "
                        "equality comparison or 'key:filterop:value' where "
                        "filterop is one of: equals, notequals, "
                        f"contains, startswith, endswith, oneof, gte, gt, "
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
            from sqlmodel import exists, select

            from zenml.enums import MetadataResourceTypes
            from zenml.zen_stores.schemas import (
                ArtifactVersionSchema,
                ModelVersionSchema,
                PipelineRunSchema,
                RunMetadataResourceSchema,
                RunMetadataSchema,
                ScheduleSchema,
                StepRunSchema,
            )

            resource_type_mapping = {
                ArtifactVersionSchema: MetadataResourceTypes.ARTIFACT_VERSION,
                ModelVersionSchema: MetadataResourceTypes.MODEL_VERSION,
                PipelineRunSchema: MetadataResourceTypes.PIPELINE_RUN,
                StepRunSchema: MetadataResourceTypes.STEP_RUN,
                ScheduleSchema: MetadataResourceTypes.SCHEDULE,
            }

            # Create an EXISTS subquery for each run_metadata filter
            for entry in self.run_metadata:
                # Split at the first colon to get the key
                key, value = entry.split(":", 1)

                # Create an exists subquery
                exists_subquery = exists(
                    select(RunMetadataResourceSchema.id)
                    .join(
                        RunMetadataSchema,
                        RunMetadataSchema.id  # type: ignore[arg-type]
                        == RunMetadataResourceSchema.run_metadata_id,
                    )
                    .where(
                        RunMetadataResourceSchema.resource_id == table.id,
                        RunMetadataResourceSchema.resource_type
                        == resource_type_mapping[table].value,
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
                custom_filters.append(exists_subquery)

        return custom_filters
