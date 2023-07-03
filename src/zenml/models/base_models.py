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
from datetime import date, datetime, time, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    ForwardRef,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import Field, SecretStr, create_model

from zenml.utils.analytics_utils import AnalyticsTrackedModelMixin

if TYPE_CHECKING:
    from zenml.models.filter_models import BaseFilterModel
    from zenml.models.user_models import UserResponseModel
    from zenml.models.workspace_models import WorkspaceResponseModel

    REQUEST_MODEL = TypeVar("REQUEST_MODEL", bound="BaseRequestModel")
    RESPONSE_MODEL = TypeVar("RESPONSE_MODEL", bound="BaseResponseModel")
    FILTER_MODEL = TypeVar("FILTER_MODEL", bound="BaseFilterModel")


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


class WorkspaceScopedResponseModel(UserScopedResponseModel):
    """Base workspace-scoped domain model.

    Used as a base class for all domain models that are workspace-scoped.
    """

    workspace: "WorkspaceResponseModel" = Field(
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

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for workspace scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["is_shared"] = self.is_shared
        return metadata


# -------------------- #
# SLIM RESPONSE MODELS #
# -------------------- #


def slim_model(_cls: Type["RESPONSE_MODEL"]) -> Type["RESPONSE_MODEL"]:
    """Slim response model decorator.

    This decorator is used to turn response models into slim response models
    that do not contain any other response models as fields.

    Args:
        _cls: The response model class to decorate.
        # TODO: add a list of fields to exclude

    Returns:
        The slim response model class.
    """
    fields = {}

    type_replacer = TypeReplacer(
        types_to_replace=[BaseResponseModel],
        type_instances_to_replace=[ForwardRef],
        replacement_type=UUID,
    )

    for field_name, field in _cls.__fields__.items():
        type_ = type_replacer(field.annotation)
        fields[field_name] = (type_, field.field_info)

    SlimModel = create_model(
        _cls.__name__,
        **fields,
        __config__=_cls.__config__,
        __module__=_cls.__module__,
    )

    # Preserve docstring
    SlimModel.__doc__ = _cls.__doc__

    return SlimModel


class TypeReplacer:
    """Callable class to replace types.

    Example:
    ```python
    type_replacer = TypeReplacer(
        types_to_replace=[int, A],
        replacement_type=B,
        recursive=True,
    )
    type_replacer(int)  # B
    type_replacer(A)  # B
    type_replacer(str)  # str
    type_replacer(bool)  # bool
    type_replacer(List[int])  # List[B]
    type_replacer(Dict[str, A])  # Dict[str, B]
    type_replacer(Union[A, C, None] # Union[B, C, None]
    ```
    """

    def __init__(
        self,
        types_to_replace: Optional[List[Type[Any]]] = None,
        type_instances_to_replace: Optional[List[Any]] = None,
        replacement_type: Optional[Type[Any]] = None,
        recursive: bool = False,
    ) -> None:
        """Initialize the type replacer.

        Args:
            types_to_replace: A list of types (classes) to replace.
            type_instances_to_replace: A list of types where `isinstance` checks
                will be performed to determine if the type should be replaced.
                This is needed for some typing types like `ForwardRef`.
            replacement_type: The type to replace the `types_to_replace` with.
                If not set, all replaced types will be replaced with `None`.
            recursive: If True, also replace subtypes of Union, List, Dict.
        """
        self.replacement_type = replacement_type
        self.types_to_replace = tuple(types_to_replace or [])
        self.type_instances_to_replace = tuple(type_instances_to_replace or [])
        self.recursive = recursive

    def __call__(self, type_: Any) -> Any:
        """Replace the given type with the replacement type if applicable.

        Args:
            type_: The type to replace. In case of a container type, the
                subtypes will be replaced recursively.

        Returns:
            The replaced type if applicable, otherwise the original type.
        """
        if isinstance(type_, type):
            if issubclass(type_, self.types_to_replace):
                return self.replacement_type
        if isinstance(type_, self.type_instances_to_replace):
            return self.replacement_type
        if self.recursive:
            if _is_union_type(type_):
                return Union[tuple(self._replace_subtypes(type_))]
            if _is_dict_type(type_):
                return Dict[tuple(self._replace_subtypes(type_))]
            if _is_list_type(type_):
                return List[self._replace_subtypes(type_)[0]]
        return type_

    def _replace_subtypes(self, type_: Any) -> List[Any]:
        """Replace the subtypes of a container type.

        Args:
            type_: The container type to get the subtypes of.

        Returns:
            The subtypes of the container type with model types replaced with UUIDs.
        """
        return [self(subtype) for subtype in _get_subtypes(type_)]


def _is_union_type(type_: Any) -> bool:
    """Check if a type is a union type.

    Args:
        type_: The type to check.

    Returns:
        True if the type is a union type.
    """
    return type_.__dict__.get("__origin__", None) == Union


def _is_dict_type(type_: Any) -> bool:
    """Check if a type is a dict type.

    Args:
        type_: The type to check.

    Returns:
        True if the type is a dict type.
    """
    return type_.__dict__.get("__origin__", None) == dict


def _is_list_type(type_: Any) -> bool:
    """Check if a type is a list type.

    Args:
        type_: The type to check.

    Returns:
        True if the type is a list type.
    """
    return type_.__dict__.get("__origin__", None) == list


def _get_subtypes(type_: Any) -> List[Any]:
    """Get the subtypes of a container type.

    Args:
        type_: The container type to get the subtypes of.

    Returns:
        The subtypes of the container type.
    """
    return type_.__dict__.get("__args__", [])


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

    def get_analytics_metadata(self) -> Dict[str, Any]:
        """Fetches the analytics metadata for workspace scoped models.

        Returns:
            The analytics metadata.
        """
        metadata = super().get_analytics_metadata()
        metadata["is_shared"] = self.is_shared
        return metadata


# ------------- #
# UPDATE MODELS #
# ------------- #


def update_model(_cls: Type["REQUEST_MODEL"]) -> Type["REQUEST_MODEL"]:
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


def filter_model(_cls: Type["FILTER_MODEL"]) -> Type["FILTER_MODEL"]:
    """Adjust the fields of a filter model to be suitable for filtering.

    This sets all fields that are not explicitly excluded from filtering as
    optional with default None and turns their typing into
    `Union[<TYPE>, str, None]`.

    Args:
        _cls: The class to decorate.

    Returns:
        The decorated class.
    """
    from zenml.config.source import Source

    type_replacer = TypeReplacer(
        types_to_replace=[Source],
        replacement_type=str,
    )

    fields = {}
    for field_name, field in _cls.__fields__.items():
        type_ = type_replacer(field.annotation)  # Convert Source to str
        if not _type_can_be_filtered_by(type_):
            continue
        field_info = field.field_info
        if field_name not in _cls.FILTER_EXCLUDE_FIELDS:
            type_ = Union[type_, str, None]
            field_info.default = None
            field_info.default_factory = None
        fields[field_name] = (type_, field_info)

    FilterModel = create_model(
        _cls.__name__,
        **fields,
        __config__=_cls.__config__,
        __module__=_cls.__module__,
    )

    # Preserve docstring
    FilterModel.__doc__ = _cls.__doc__

    return FilterModel


def _type_can_be_filtered_by(type_: Any) -> bool:
    """Check if a type can be filtered by.

    Only the following types and their unions are supported for filtering:
    - UUID
    - str
    - int
    - float
    - bool
    - datetime.datetime
    - datetime.date
    - datetime.time
    - datetime.timedelta
    - None

    Args:
        type_: The type to check.

    Returns:
        True if the type can be filtered by, False otherwise.
    """
    if type_ is None or type_ is type(None):
        return True
    if isinstance(type_, type):
        return issubclass(
            type_,
            (UUID, str, int, float, bool, datetime, date, time, timedelta),
        )
    if _is_union_type(type_):
        return all(
            _type_can_be_filtered_by(subtype)
            for subtype in _get_subtypes(type_)
        )
    return False
