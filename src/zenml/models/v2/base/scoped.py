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

from pydantic import Field

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

    from zenml.models.v2.core.user import UserResponse
    from zenml.models.v2.core.workspace import WorkspaceResponse
    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

# ---------------------- Request Models ----------------------


class UserScopedRequest(BaseRequest):
    """Base user-owned request model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: UUID = Field(title="The id of the user that created this resource.")

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for user scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["user_id"] = self.user
        return metadata


class WorkspaceScopedRequest(UserScopedRequest):
    """Base workspace-scoped request domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    workspace: UUID = Field(
        title="The workspace to which this resource belongs."
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for workspace scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["workspace_id"] = self.workspace
        return metadata


# ---------------------- Response Models ----------------------


# User-scoped models
class UserScopedResponseBody(BaseDatedResponseBody):
    """Base user-owned body."""

    user: Optional["UserResponse"] = Field(
        title="The user who created this resource.", default=None
    )


class UserScopedResponseMetadata(BaseResponseMetadata):
    """Base user-owned metadata."""


class UserScopedResponseResources(BaseResponseResources):
    """Base class for all resource models associated with the user."""


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
        if self.user is not None:
            metadata["user_id"] = self.user.id
        return metadata

    # Body and metadata properties
    @property
    def user(self) -> Optional["UserResponse"]:
        """The `user` property.

        Returns:
            the value of the property.
        """
        return self.get_body().user


class UserScopedFilter(BaseFilter):
    """Model to enable advanced user-based scoping."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "user",
        "scope_user",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "user_id",
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
    user_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="UUID of the user that created the entity.",
        union_mode="left_to_right",
    )
    user: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the user that created the entity.",
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

            query = query.join(
                UserSchema, getattr(table, "user_id") == UserSchema.id
            )

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


# Workspace-scoped models


class WorkspaceScopedResponseBody(UserScopedResponseBody):
    """Base workspace-scoped body."""


class WorkspaceScopedResponseMetadata(UserScopedResponseMetadata):
    """Base workspace-scoped metadata."""

    workspace: "WorkspaceResponse" = Field(
        title="The workspace of this resource."
    )


class WorkspaceScopedResponseResources(UserScopedResponseResources):
    """Base workspace-scoped resources."""


WorkspaceBody = TypeVar("WorkspaceBody", bound=WorkspaceScopedResponseBody)
WorkspaceMetadata = TypeVar(
    "WorkspaceMetadata", bound=WorkspaceScopedResponseMetadata
)
WorkspaceResources = TypeVar(
    "WorkspaceResources", bound=WorkspaceScopedResponseResources
)


class WorkspaceScopedResponse(
    UserScopedResponse[WorkspaceBody, WorkspaceMetadata, WorkspaceResources],
    Generic[WorkspaceBody, WorkspaceMetadata, WorkspaceResources],
):
    """Base workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    # Body and metadata properties
    @property
    def workspace(self) -> "WorkspaceResponse":
        """The workspace property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().workspace


class WorkspaceScopedFilter(UserScopedFilter):
    """Model to enable advanced scoping with workspace."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.FILTER_EXCLUDE_FIELDS,
        "workspace",
        "scope_workspace",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *UserScopedFilter.CLI_EXCLUDE_FIELDS,
        "workspace_id",
        "workspace",
        "scope_workspace",
    ]
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *UserScopedFilter.CUSTOM_SORTING_OPTIONS,
        "workspace",
    ]
    scope_workspace: Optional[UUID] = Field(
        default=None,
        description="The workspace to scope this query to.",
    )
    workspace_id: Optional[Union[UUID, str]] = Field(
        default=None,
        description="UUID of the workspace that this entity belongs to.",
        union_mode="left_to_right",
    )
    workspace: Optional[Union[UUID, str]] = Field(
        default=None,
        description="Name/ID of the workspace that this entity belongs to.",
    )

    def set_scope_workspace(self, workspace_id: UUID) -> None:
        """Set the workspace to scope this response.

        Args:
            workspace_id: The workspace to scope this response to.
        """
        self.scope_workspace = workspace_id

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

        from zenml.zen_stores.schemas import WorkspaceSchema

        if self.workspace:
            workspace_filter = and_(
                getattr(table, "workspace_id") == WorkspaceSchema.id,
                self.generate_name_or_id_query_conditions(
                    value=self.workspace,
                    table=WorkspaceSchema,
                ),
            )
            custom_filters.append(workspace_filter)

        return custom_filters

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
        from sqlmodel import or_

        query = super().apply_filter(query=query, table=table)

        if self.scope_workspace:
            scope_filter = or_(
                getattr(table, "workspace_id") == self.scope_workspace,
                getattr(table, "workspace_id").is_(None),
            )
            query = query.where(scope_filter)

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
        from sqlmodel import asc, desc

        from zenml.enums import SorterOps
        from zenml.zen_stores.schemas import WorkspaceSchema

        sort_by, operand = self.sorting_params

        if sort_by == "workspace":
            column = WorkspaceSchema.name

            query = query.join(
                WorkspaceSchema,
                getattr(table, "workspace_id") == WorkspaceSchema.id,
            )

            if operand == SorterOps.ASCENDING:
                query = query.order_by(asc(column))
            else:
                query = query.order_by(desc(column))

            return query

        return super().apply_sorting(query=query, table=table)


class WorkspaceScopedTaggableFilter(WorkspaceScopedFilter):
    """Model to enable advanced scoping with workspace and tagging."""

    tag: Optional[str] = Field(
        description="Tag to apply to the filter query.", default=None
    )

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "tag",
    ]

    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.CUSTOM_SORTING_OPTIONS,
        "tag",
    ]

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
        from zenml.zen_stores.schemas import TagResourceSchema

        query = super().apply_filter(query=query, table=table)
        if self.tag:
            query = (
                query.join(getattr(table, "tags"))
                .join(TagResourceSchema.tag)
                .distinct()
            )

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
        from zenml.zen_stores.schemas import TagSchema

        custom_filters = super().get_custom_filters(table)
        if self.tag:
            custom_filters.append(
                self.generate_custom_query_conditions_for_column(
                    value=self.tag, table=TagSchema, column="name"
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

        if sort_by == "tag":
            from sqlmodel import and_, asc, desc, func

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

            query = (
                query.outerjoin(
                    TagResourceSchema,
                    and_(
                        table.id == TagResourceSchema.resource_id,
                        TagResourceSchema.resource_type
                        == resource_type_mapping[table],
                    ),
                )
                .outerjoin(TagSchema, TagResourceSchema.tag_id == TagSchema.id)
                .group_by(table.id)
            )

            if operand == SorterOps.ASCENDING:
                query = query.order_by(
                    asc(
                        func.group_concat(TagSchema.name, ",").label(
                            "tags_list"
                        )
                    )
                )
            else:
                query = query.order_by(
                    desc(
                        func.group_concat(TagSchema.name, ",").label(
                            "tags_list"
                        )
                    )
                )

            return query

        return super().apply_sorting(query=query, table=table)
