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
"""Base classes for SQLModel schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.models.v2.base.base import BaseResponse

    B = TypeVar("B", bound=BaseResponse)  # type: ignore[type-arg]


class BaseSchema(SQLModel):
    """Base SQL Model for ZenML entities."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created: datetime = Field(default_factory=utc_now)
    updated: datetime = Field(default_factory=utc_now)

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Any:
        """In case the Schema has a corresponding Model, this allows conversion to that model.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Raises:
            NotImplementedError: When the base class fails to implement this.
        """
        raise NotImplementedError(
            "No 'to_model()' method implemented for this"
            f"schema: '{self.__class__.__name__}'."
        )


class NamedSchema(BaseSchema):
    """Base Named SQL Model."""

    name: str
