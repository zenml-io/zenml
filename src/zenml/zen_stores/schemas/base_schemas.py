from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Field

from zenml.models.base_models import DomainModel


class BaseSchemaMixin(BaseModel, ABC):

    id: UUID = Field(primary_key=True)
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    @abstractmethod
    def to_model(self) -> DomainModel:
        """Creates a `DomainModel` from an instance of a `BaseSchema`.

        Returns:
            A `DomainModel`
        """


class NamedSchemaMixin(BaseSchemaMixin, ABC):

    name: str


class SharableSchemaMixin(NamedSchemaMixin, ABC):

    is_shared: bool
