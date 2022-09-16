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


from typing import ClassVar, Type, TypeVar
from uuid import UUID
from pydantic import BaseModel

AnyModel = TypeVar("AnyModel", bound=BaseModel)


class CreateRequest(BaseModel):
    """Base model used for create requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]]

    def to_model(self) -> BaseModel:
        """Create a domain model from this create request.

        Returns:
            The created domain model.
        """
        return self.DOMAIN_MODEL(**self.dict(exclude_none=True))

    @classmethod
    def from_model(cls, model: BaseModel) -> "CreateRequest":
        """Convert a domain model into a create request.

        Args:
            model: The domain model to convert.

        Returns:
            The create request.
        """
        return cls(**model.dict())


class ProjectScopedCreateRequest(CreateRequest):
    """Base model used for project scoped create requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]]

    def to_model(self, project: UUID, user: UUID) -> "BaseModel":
        """Create a domain model from this create request.

        Returns:
            The created domain model.
        """
        return self.DOMAIN_MODEL(
            project=project, user=user, **self.dict(exclude_none=True)
        )


class CreateResponse(BaseModel):
    """Base model used for create responses."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]]

    @classmethod
    def from_model(cls, model: BaseModel) -> "CreateResponse":
        """Convert a domain model into a create response.

        Args:
            model: The domain model to convert.

        Returns:
            The create response.
        """
        return cls(**model.dict())

    def to_model(self) -> BaseModel:
        """Create a domain model from this create response.

        Returns:
            The created domain model.
        """
        return self.DOMAIN_MODEL(**self.dict())


class UpdateRequest(BaseModel):
    """Base model used for update requests."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]]

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
    def from_model(cls, model: BaseModel) -> "UpdateRequest":
        """Convert a domain model into an update request.

        Args:
            model: The domain model to convert.

        Returns:
            The update request.
        """
        return cls(**model.dict())


class UpdateResponse(BaseModel):
    """Base model used for update responses."""

    DOMAIN_MODEL: ClassVar[Type[BaseModel]]

    @classmethod
    def from_model(cls, model: BaseModel) -> "UpdateResponse":
        """Convert a domain model into an update response.

        Args:
            model: The domain model to convert.

        Returns:
            The update response.
        """
        return cls(**model.dict())

    def to_model(self) -> BaseModel:
        """Create a domain model from this update response.

        Returns:
            The created domain model.
        """
        return self.DOMAIN_MODEL(**self.dict())
