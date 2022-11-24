#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Base domain model definitions."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar
from uuid import UUID

from pydantic import Field

from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

if TYPE_CHECKING:
    from zenml.models.workspace_models import WorkspaceResponseModel
    from zenml.models.user_models import UserResponseModel


# --------------- #
# RESPONSE MODELS #
# --------------- #


class BaseResponseModel(AnalyticsTrackedModelMixin):
    """Base domain model.

    Used as a base class for all domain models that have the following common
    characteristics:

      * are uniquely identified by a UUID
      * have a creation timestamp and a last modified timestamp
    """

    id: UUID = Field(title="The unique resource id.")

    created: datetime = Field(title="Time when this resource was created.")
    updated: datetime = Field(title="Time when this resource was last updated.")

    def __hash__(self) -> int:
        """Implementation of hash magic method.

        Returns:
            Hash of the UUID.
        """
        return hash((type(self),) + tuple([self.id]))

    def __eq__(self, other: Any) -> bool:
        """Implementation of equality magic method.

        Args:
            other: The other object to compare to.

        Returns:
            True if the other object is of the same type and has the same UUID.
        """
        if isinstance(other, BaseResponseModel):
            return self.id == other.id
        else:
            return False


class UserScopedResponseModel(BaseResponseModel):
    """Base user-owned domain model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: Optional["UserResponseModel"] = Field(
        title="The user that created this resource.", nullable=True
    )


class WorkspaceScopedResponseModel(UserScopedResponseModel):
    """Base workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    workspace: "WorkspaceResponseModel" = Field(
        title="The workspace of this resource."
    )


class ShareableResponseModel(WorkspaceScopedResponseModel):
    """Base shareable workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped and are
    shareable.
    """

    is_shared: bool = Field(
        title=(
            "Flag describing if this resource is shared with other users in "
            "the same workspace."
        ),
    )


# -------------- #
# REQUEST MODELS #
# -------------- #


class BaseRequestModel(AnalyticsTrackedModelMixin):
    """Base request model.

    Used as a base class for all request models.
    """


class UserOwnedRequestModel(BaseRequestModel):
    """Base user-owned request model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: UUID = Field(title="The id of the user that created this resource.")


class WorkspaceScopedRequestModel(UserOwnedRequestModel):
    """Base workspace-scoped request domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    workspace: UUID = Field(title="The workspace to which this resource belongs.")


class ShareableRequestModel(WorkspaceScopedRequestModel):
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


# ------------- #
# UPDATE MODELS #
# ------------- #

T = TypeVar("T", bound="BaseRequestModel")


def update(_cls: Type[T]) -> Type[T]:
    """TODO: @bcdurak describe what this does."""
    for _, value in _cls.__fields__.items():
        value.required = False
        value.allow_none = True

    return _cls
