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
from typing import Any
from uuid import UUID

from pydantic import Field

from zenml.models.project_models import ProjectModel
from zenml.models.user_management_models import UserModel
from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

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


class UserOwnedResponseModel(BaseResponseModel):
    """Base user-owned domain model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: UserModel = Field(title="The user that created this resource.")


class ProjectScopedResponseModel(UserOwnedResponseModel):
    """Base project-scoped domain model.

    Used as a base class for all domain models that are project-scoped.
    """

    project: ProjectModel = Field(title="The project of this resource.")


class ShareableResponseModel(ProjectScopedResponseModel):
    """Base shareable project-scoped domain model.

    Used as a base class for all domain models that are project-scoped and are
    shareable.
    """

    is_shared: bool = Field(
        title=(
            "Flag describing if this resource is shared with other users in "
            "the same project."
        ),
    )


# -------------- #
# REQUEST MODELS #
# -------------- #


class BaseRequestModel(AnalyticsTrackedModelMixin):
    """ """


class UserOwnedRequestModel(BaseRequestModel):
    """Base user-owned domain model.

    Used as a base class for all domain models that are "owned" by a user.
    """

    user: UUID = Field(title="The id of the user that created this resource.")


class ProjectScopedRequestModel(UserOwnedRequestModel):
    """Base project-scoped domain model.

    Used as a base class for all domain models that are project-scoped.
    """

    project: UUID = Field(title="The project to which this resource belongs.")


class ShareableRequestModel(ProjectScopedRequestModel):
    """Base shareable project-scoped domain model.

    Used as a base class for all domain models that are project-scoped and are
    shareable.
    """

    is_shared: bool = Field(
        default=False,
        title=(
            "Flag describing if this resource is shared with other users in "
            "the same project."
        ),
    )


# # ------------ #
# # UPDATE MODEL #
# # ------------ #
#
# NON_UPDATABLE_FIELDS = ["user", "project"]
#
#
# def update_model(*fields):
#     def dec(_cls):
#         for field in fields:
#             if field not in NON_UPDATABLE_FIELDS:
#                 _cls.__fields__[field].required = False
#         return _cls
#
#     if (
#         fields
#         and inspect.isclass(fields[0])
#         and issubclass(fields[0], BaseModel)
#     ):
#         cls = fields[0]
#         fields = cls.__fields__
#         return dec(cls)
#
#     return dec
