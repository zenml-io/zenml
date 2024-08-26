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
from zenml.models.v2.base.filter import AnyQuery, BaseFilter, StrFilter

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
        "scope_user",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "scope_user",
    ]
    scope_user: Optional[UUID] = Field(
        default=None,
        description="The user to scope this query to.",
    )

    def set_scope_user(self, user_id: UUID) -> None:
        """Set the user that is performing the filtering to scope the response.

        Args:
            user_id: The user ID to scope the response to.
        """
        self.scope_user = user_id

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


class WorkspaceScopedFilter(BaseFilter):
    """Model to enable advanced scoping with workspace."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.FILTER_EXCLUDE_FIELDS,
        "scope_workspace",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilter.CLI_EXCLUDE_FIELDS,
        "scope_workspace",
    ]
    scope_workspace: Optional[UUID] = Field(
        default=None,
        description="The workspace to scope this query to.",
    )

    def set_scope_workspace(self, workspace_id: UUID) -> None:
        """Set the workspace to scope this response.

        Args:
            workspace_id: The workspace to scope this response to.
        """
        self.scope_workspace = workspace_id

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


class WorkspaceScopedTaggableFilter(WorkspaceScopedFilter):
    """Model to enable advanced scoping with workspace and tagging."""

    tag: Optional[str] = Field(
        description="Tag to apply to the filter query.", default=None
    )

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
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

    def get_custom_filters(self) -> List["ColumnElement[bool]"]:
        """Get custom tag filters.

        Returns:
            A list of custom filters.
        """
        from zenml.zen_stores.schemas import TagSchema

        custom_filters = super().get_custom_filters()
        if self.tag:
            value, filter_operator = self._resolve_operator(self.tag)
            filter_ = StrFilter(
                operation=filter_operator,
                column="name",
                value=value,
            )

            custom_filters.append(filter_.generate_query_conditions(TagSchema))

        return custom_filters
