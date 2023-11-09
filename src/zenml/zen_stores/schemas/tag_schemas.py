#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""SQLModel implementation of tag tables."""


from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, List, Optional
from uuid import UUID

from sqlalchemy import SMALLINT, Column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlmodel import Field, Relationship

from zenml.enums import ColorVariants, TaggableResourceTypes
from zenml.models import (
    TagRequestModel,
    TagResourceRequestModel,
    TagResourceResponseModel,
    TagResponseModel,
    TagUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.model_schemas import ModelSchema


class TagSchema(NamedSchema, table=True):
    """SQL Model for tag."""

    __tablename__ = "tag"

    color: int = Field(sa_column=Column(SMALLINT, nullable=False))
    links: List["TagResourceSchema"] = Relationship(
        back_populates="tag",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    @classmethod
    def from_request(cls, request: TagRequestModel) -> "TagSchema":
        """Convert an `TagRequestModel` to an `TagSchema`.

        Args:
            tag_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=request.name,
            color=getattr(ColorVariants, request.color.upper()).value,
        )

    def to_model(self) -> TagResponseModel:
        """Convert an `TagSchema` to an `TagResponseModel`.

        Returns:
            The created `TagResponseModel`.
        """
        return TagResponseModel(
            id=self.id,
            name=self.name,
            color=ColorVariants(self.color).name.lower(),
            created=self.created,
            updated=self.updated,
            tagged_count=len(self.links),
        )

    def update(
        self,
        update: TagUpdateModel,
    ) -> "TagSchema":
        """Updates a `TagSchema` from a `TagUpdateModel`.

        Args:
            update: The `TagUpdateModel` to update from.

        Returns:
            The updated `TagSchema`.
        """
        for field, value in update.dict(exclude_unset=True).items():
            setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self


class TagResourceSchema(BaseSchema, table=True):
    """SQL Model for tag resource relationship."""

    __tablename__ = "tag_resource"

    tag_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=TagSchema.__tablename__,
        source_column="tag_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    tag: "TagSchema" = Relationship(back_populates="links")
    model_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="model",
        source_column="model_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    model: "ModelSchema" = Relationship(back_populates="tags")

    # extend to self.model_id or self.other_resource_id going forward
    resource_id: ClassVar[Optional[UUID]] = hybrid_property(
        lambda self: self.model_id or None
    )

    @classmethod
    def from_request(
        cls, request: TagResourceRequestModel
    ) -> "TagResourceSchema":
        """Convert an `TagResourceRequestModel` to an `TagResourceSchema`.

        Args:
            request: The request model version to convert.

        Returns:
            The converted schema.
        """
        if request.resource_type == TaggableResourceTypes.MODEL:
            return cls(
                id=request.tag_resource_id,
                tag_id=request.tag_id,
                model_id=request.resource_id,
            )
        else:
            raise NotImplementedError(
                f"Not yet supported `resource_type`=`{request.resource_type}` provided."
            )

    def to_model(self) -> TagResourceResponseModel:
        """Convert an `TagResourceSchema` to an `TagResourceResponseModel`.

        Returns:
            The created `TagResourceResponseModel`.
        """
        return TagResourceResponseModel(
            id=self.id,
            tag_id=self.tag_id,
            resource_id=self.resource_id,
            created=self.created,
            updated=self.updated,
        )

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
