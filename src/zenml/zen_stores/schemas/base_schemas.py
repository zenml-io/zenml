from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from zenml.models.base_models import DomainModel


class BaseSchema(SQLModel):

    id: UUID = Field(primary_key=True)
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    def to_model(self) -> DomainModel:
        """Creates a `DomainModel` from an instance of a `BaseSchema`.

        Returns:
            A `DomainModel`
        """
        raise NotImplementedError(
            "This method is not implemented in the base " "models."
        )


class NamedSchema(BaseSchema):

    name: str

    def to_model(self) -> DomainModel:
        """Creates a `DomainModel` from an instance of a `NamedSchema`.

        Returns:
            A `DomainModel`
        """
        raise NotImplementedError(
            "This method is not implemented in the base " "models."
        )


class SharableSchema(NamedSchema):

    is_shared: bool

    def to_model(self) -> DomainModel:
        """Creates a `DomainModel` from an instance of a `NamedSchema`.

        Returns:
            A `DomainModel`
        """
        raise NotImplementedError(
            "This method is not implemented in the base " "models."
        )
