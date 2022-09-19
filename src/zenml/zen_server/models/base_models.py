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
"""Base REST API model definitions."""


from typing import Any, Generic, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel

AnyModel = TypeVar("AnyModel", bound=BaseModel)


class CreateRequest(BaseModel, Generic[AnyModel]):
    """Base model used for create requests."""

    _MODEL_TYPE: Type[AnyModel]

    def to_model(self, **kwargs: Any) -> AnyModel:
        """Create a domain model from this create request.

        Args:
            kwargs: Additional keyword arguments to pass to the model

        Returns:
            The created domain model.
        """
        return self._MODEL_TYPE(**self.dict(exclude_none=True), **kwargs)

    @classmethod
    def from_model(
        cls, model: AnyModel, **kwargs: Any
    ) -> "CreateRequest[AnyModel]":
        """Convert a domain model into a create request.

        Args:
            model: The domain model to convert.
            kwargs: Additional keyword arguments to pass to the create request.

        Returns:
            The create request.
        """
        return cls(**model.dict(), **kwargs)

    class Config:
        """Pydantic config."""

        underscore_attrs_are_private = True


class ProjectScopedCreateRequest(CreateRequest[AnyModel]):
    """Base model used for project scoped create requests."""

    def to_model(self, project: UUID, user: UUID, **kwargs: Any) -> AnyModel:  # type: ignore[override]
        """Create a domain model from this create request.

        Args:
            project: The project to create the model in.
            user: The user creating the model.
            kwargs: Additional keyword arguments to pass to the model

        Returns:
            The created domain model.
        """
        return super().to_model(project=project, user=user, **kwargs)


class CreateResponse(BaseModel, Generic[AnyModel]):
    """Base model used for create responses."""

    _MODEL_TYPE: Type[AnyModel]

    @classmethod
    def from_model(
        cls, model: AnyModel, **kwargs: Any
    ) -> "CreateResponse[AnyModel]":
        """Convert a domain model into a create response.

        Args:
            model: The domain model to convert.
            kwargs: Additional keyword arguments to pass to the create response.

        Returns:
            The create response.
        """
        return cls(**model.dict(), **kwargs)

    def to_model(self, **kwargs: Any) -> AnyModel:
        """Create a domain model from this create response.

        Args:
            kwargs: Additional keyword arguments to pass to the model

        Returns:
            The created domain model.
        """
        return self._MODEL_TYPE(**self.dict(exclude_none=True), **kwargs)

    class Config:
        """Pydantic config."""

        underscore_attrs_are_private = True


class UpdateRequest(BaseModel, Generic[AnyModel]):
    """Base model used for update requests."""

    _MODEL_TYPE: Type[AnyModel]

    def apply_to_model(self, model: AnyModel) -> AnyModel:
        """Apply the update changes to a domain model.

        Args:
            model: The domain model to update.

        Returns:
            The updated domain model.
        """
        for k, v in self.dict(exclude_none=True).items():
            setattr(model, k, v)
        return model

    @classmethod
    def from_model(
        cls, model: AnyModel, **kwargs: Any
    ) -> "UpdateRequest[AnyModel]":
        """Convert a domain model into a update request.

        Args:
            model: The domain model to convert.
            kwargs: Additional keyword arguments to pass to the update request.

        Returns:
            The create request.
        """
        return cls(**model.dict(), **kwargs)

    class Config:
        """Pydantic config."""

        underscore_attrs_are_private = True


class UpdateResponse(BaseModel, Generic[AnyModel]):
    """Base model used for update responses."""

    _MODEL_TYPE: Type[AnyModel]

    @classmethod
    def from_model(
        cls, model: AnyModel, **kwargs: Any
    ) -> "UpdateResponse[AnyModel]":
        """Convert a domain model into an update response.

        Args:
            model: The domain model to convert.
            kwargs: Additional keyword arguments to pass to the update response.

        Returns:
            The update response.
        """
        return cls(**model.dict(), **kwargs)

    def to_model(self, **kwargs: Any) -> AnyModel:
        """Create a domain model from this update response.

        Args:
            kwargs: Additional keyword arguments to pass to the model

        Returns:
            The created domain model.
        """
        return self._MODEL_TYPE(**self.dict(exclude_none=True), **kwargs)

    class Config:
        """Pydantic config."""

        underscore_attrs_are_private = True
