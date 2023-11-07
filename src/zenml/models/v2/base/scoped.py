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

from abc import abstractmethod
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
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.models.v2.base.base import (
    BaseRequest,
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
)
from zenml.models.v2.base.filter import BaseFilter

if TYPE_CHECKING:
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


class ShareableRequest(WorkspaceScopedRequest):
    """Base shareable workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped and are
    shareable.
    """

    is_shared: bool = Field(
        default=False,
        title=(
            "Flag describing if this resource is shared with other users in "
            "the same workspace."
        ),
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for workspace scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["is_shared"] = self.is_shared
        return metadata


# ---------------------- Response Models ----------------------


# User-scoped models
class UserScopedResponseBody(BaseResponseBody):
    """Base user-owned body."""

    user: Optional["UserResponse"] = Field(
        title="The user who created this resource."
    )


class UserScopedResponseMetadata(BaseResponseMetadata):
    """Base user-owned metadata."""


class UserScopedResponse(BaseResponse):
    """Base user-owned model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    # Body and metadata pair
    body: UserScopedResponseBody = Field("The body of this resource.")
    metadata: Optional["UserScopedResponseMetadata"] = Field(
        title="The metadata related to this resource."
    )

    @abstractmethod
    def get_hydrated_version(self) -> "UserScopedResponse":
        """Abstract method that needs to be implemented to hydrate the instance.

        Each response model has a metadata field. The purpose of this
        is to populate this field by making an additional call to the API.
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
    def user(self) -> "UserResponse":
        """The `user` property."""
        return self.body.user


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
        query: Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"],
        table: Type["AnySchema"],
    ) -> Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"]:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        from sqlmodel import or_

        query = super().apply_filter(query=query, table=table)

        if self.scope_user:
            scope_filter = or_(
                getattr(table, "user_id") == self.scope_user,
            )
            query = query.where(scope_filter)

        return query


# Workspace-scoped models


class WorkspaceScopedResponseBody(UserScopedResponseBody):
    """Base workspace-scoped body."""


class WorkspaceScopedResponseMetadata(UserScopedResponseMetadata):
    """Base workspace-scoped metadata."""

    workspace: "WorkspaceResponse" = Field(
        title="The workspace of this resource."
    )


class WorkspaceScopedResponse(UserScopedResponse):
    """Base workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    # Body and metadata definition
    body: "WorkspaceScopedResponseBody"
    metadata: Optional["WorkspaceScopedResponseMetadata"]

    @abstractmethod
    def get_hydrated_version(self) -> "WorkspaceScopedResponse":
        """Abstract method that needs to be implemented to hydrate the instance.

        Each response model has a metadata field. The purpose of this
        is to populate this field by making an additional call to the API.
        """

    # Body and metadata properties
    @property
    def workspace(self) -> "WorkspaceResponse":
        """The workspace property."""
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
        query: Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"],
        table: Type["AnySchema"],
    ) -> Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"]:
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


# Shareable models
class SharableResponseBody(WorkspaceScopedResponseBody):
    """Base shareable workspace-scoped body."""

    is_shared: bool = Field(
        title=(
            "Flag describing if this resource is shared with other users in "
            "the same workspace."
        ),
    )


class SharableResponseMetadata(WorkspaceScopedResponseMetadata):
    """Base shareable workspace-scoped metadata."""


class ShareableResponse(WorkspaceScopedResponse):
    """Base shareable workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped and are
    shareable.
    """

    # Body and metadata definition
    body: "SharableResponseBody"
    metadata: Optional["SharableResponseMetadata"]

    @abstractmethod
    def get_hydrated_version(self) -> "ShareableResponse":
        """Abstract method that needs to be implemented to hydrate the instance.

        Each response model has a metadata field. The purpose of this
        is to populate this field by making an additional call to the API.
        """

    # Analytics
    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for workspace scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["is_shared"] = self.is_shared
        return metadata

    # Body and metadata properties
    @property
    def is_shared(self) -> bool:
        """The is_shared property."""
        return self.body.is_shared


class ShareableFilter(WorkspaceScopedFilter):
    """Model for workspace and user scoped shareable entities."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.FILTER_EXCLUDE_FIELDS,
        "scope_user",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *WorkspaceScopedFilter.CLI_EXCLUDE_FIELDS,
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
        query: Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"],
        table: Type["AnySchema"],
    ) -> Union["Select[AnySchema]", "SelectOfScalar[AnySchema]"]:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        from sqlmodel import or_

        query = super().apply_filter(query=query, table=table)

        if self.scope_user:
            scope_filter = or_(
                getattr(table, "user_id") == self.scope_user,
                getattr(table, "is_shared").is_(True),
            )
            query = query.where(scope_filter)

        return query
