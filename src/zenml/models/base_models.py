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
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar, Union, \
    List
from uuid import UUID

from dataclasses import dataclass

from fastapi import Query
from pydantic import Field, BaseModel, root_validator, validator

from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin
from zenml.utils.enum_utils import StrEnum

if TYPE_CHECKING:
    from zenml.models.project_models import ProjectResponseModel
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

    user: Optional["UserResponseModel"] = Field(
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


class ProjectScopedResponseModel(UserScopedResponseModel):
    """Base project-scoped domain model.

    Used as a base class for all domain models that are project-scoped.
    """

    project: "ProjectResponseModel" = Field(
        title="The project of this resource."
    )

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for project scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["project_id"] = self.project.id
        return metadata


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

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for project scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["is_shared"] = self.is_shared
        return metadata


# -------------- #
# REQUEST MODELS #
# -------------- #


class BaseRequestModel(AnalyticsTrackedModelMixin):
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


class ProjectScopedRequestModel(UserScopedRequestModel):
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

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for project scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["is_shared"] = self.is_shared
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


# ------------------ #
# QUERY PARAM MODELS #
# ------------------ #

@dataclass
class RawParams:
    limit: int
    offset: int


class GenericFilterOps(StrEnum):
    """Ops for all filters for string values on list methods"""

    EQUALS = "equals"
    CONTAINS = "contains"
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"


class Filter(BaseModel):
    operation: GenericFilterOps
    value: str


class ListBaseModel(BaseModel):
    dict_of_filters: Dict[str, Filter] = {}
    sort_by: str = Query("created")

    page: int = Query(1, ge=1, description="Page number")
    size: int = Query(50, ge=1, le=100, description="Page size")

    id: UUID = Query(None, description="Id for this resource")
    created: datetime = Query(None, description="Created")
    updated: datetime = Query(None, description="Updated")

    def get_pagination_params(self) -> RawParams:
        return RawParams(
            limit=self.size,
            offset=self.size * (self.page - 1),
        )

    @validator("sort_by", pre=True)
    def sort_column(cls, v):
        if v in ["sort_by", "dict_of_filters", "page", "size"]:
            raise ValueError(
                f"This resource can not be sorted by this field: '{v}'"
            )
        elif v in cls.__fields__:
            return v
        else:
            raise ValueError(
                "You can only sort by valid fields of this resource"
            )

    @root_validator()
    def change(cls, values):
        values["dict_of_filters"] = {}

        for key, value in values.items():
            if key not in ["sort_by", "dict_of_filters", "page", "size"] and value:
                if isinstance(value, str):
                    for op in GenericFilterOps.values():
                        if value.startswith(f"{op}:"):
                            values["dict_of_filters"][key] = Filter(
                                operation=op, value=value.lstrip(op)
                            )
                    else:
                        values["dict_of_filters"][key] = Filter(
                            operation=GenericFilterOps("equals"), value=value
                        )
                else:
                    values["dict_of_filters"][key] = Filter(
                        operation=GenericFilterOps("equals"), value=value
                    )
        return values
    #
    # @validator("*", pre=True)
    # def change(cls, v, values, config, field):
    #     if field.type_ == Union[str, Filter]:
    #         for op in StringFilterOps.values():
    #             if not isinstance(v, UUID) and v.startswith(f'{op}:'):
    #                 return Filter(operation=StringFilterOps(op),
    #                               value=v.lstrip(op))
    #         else:
    #             return Filter(
    #                 operation=StringFilterOps("equals"),
    #                 value=v
    #             )
    #
    #     if field.type_ == Union[str, UUID, Filter]:
    #         if isinstance(v, str):
    #             for op in StringFilterOps.values():
    #                 if not isinstance(v, UUID) and v.startswith(f'{op}:'):
    #                     return Filter(operation=StringFilterOps(op),
    #                                   value=v.lstrip(op))
    #         else:
    #             return Filter(
    #                 operation=StringFilterOps("equals"),
    #                 value=v
    #             )
    #
    #     elif field.type_ == Union[UUID, Filter]:
    #         return Filter(
    #             operation=GenericFilterOps("equals"),
    #             value=str(v)
    #         )
    #
    #     elif field.type_ == Union[int, Filter]:
    #         for op in IntFilterOps.values():
    #             if v.startswith(f'{op}:'):
    #                 return Filter(operation=IntFilterOps(op),
    #                               value=v.lstrip(op))
    #         else:
    #             return Filter(
    #                 operation=IntFilterOps("equals"),
    #                 value=int(v)
    #             )
    #
    #     else:
    #         return v


R = TypeVar("R", bound="BaseResponseModel")


def filter_model(_cls: Type[R]) -> Type[R]:
    """Base update model.

    This is used as a decorator on top of request models to convert them
    into update models where the fields are optional and can be set to None.

    Args:
        _cls: The class to decorate

    Returns:
        The decorated class.
    """
    # TODO add methods to translate queries into the appropriate methods
    for field in _cls.__fields__.keys():
        _cls.__setattr__(field, Query(None, max_length=200))
    return _cls
