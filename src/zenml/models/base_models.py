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
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field, SecretStr

from zenml.analytics.models import AnalyticsTrackedModelMixin

if TYPE_CHECKING:
    from zenml.models import UserResponse, WorkspaceResponse


# ------------#
# BASE MODELS #
# ------------#
class BaseZenModel(AnalyticsTrackedModelMixin):
    """Base model class for all ZenML models.

    This class is used as a base class for all ZenML models. It provides
    functionality for tracking analytics events and proper encoding of
    SecretStr values.
    """

    class Config:
        """Pydantic configuration class."""

        # This is needed to allow the REST client and server to unpack SecretStr
        # values correctly.
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value()
            if v is not None
            else None
        }

        # Allow extras on all models to support forwards and backwards
        # compatibility (e.g. new fields in newer versions of ZenML servers
        # are allowed to be present in older versions of ZenML clients and
        # vice versa).
        extra = "allow"


# --------------- #
# RESPONSE MODELS #
# --------------- #


class BaseResponseModel(BaseZenModel):
    """Base domain model.

    Used as a base class for all domain models that have the following common
    characteristics:

      * are uniquely identified by a UUID
      * have a creation timestamp and a last modified timestamp
    """

    id: UUID = Field(title="The unique resource id.")

    created: datetime = Field(title="Time when this resource was created.")
    updated: datetime = Field(
        title="Time when this resource was last updated."
    )

    missing_permissions: bool = False

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

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for base response models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["entity_id"] = self.id
        return metadata


class UserScopedResponseModel(BaseResponseModel):
    """Base user-owned domain model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: Union["UserResponse", None] = Field(
        title="The user that created this resource.", nullable=True
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for user scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        if self.user is not None:
            metadata["user_id"] = self.user.id
        return metadata


class WorkspaceScopedResponseModel(UserScopedResponseModel):
    """Base workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    workspace: "WorkspaceResponse" = Field(
        title="The workspace of this resource."
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for workspace scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["workspace_id"] = self.workspace.id
        return metadata


# -------------- #
# REQUEST MODELS #
# -------------- #


class BaseRequestModel(BaseZenModel):
    """Base request model.

    Used as a base class for all request models.
    """


class UserScopedRequestModel(BaseRequestModel):
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


class WorkspaceScopedRequestModel(UserScopedRequestModel):
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


# ------------- #
# UPDATE MODELS #
# ------------- #

T = TypeVar("T", bound="BaseRequestModel")


def update_model(_cls: Type[T]) -> Type[T]:
    """Base update model.

    This is used as a decorator on top of request models to convert them
    into update models where the fields are optional and can be set to None.

    Args:
        _cls: The class to decorate

    Returns:
        The decorated class.
    """
    for _, value in _cls.__fields__.items():
        value.required = False
        value.allow_none = True

    return _cls
