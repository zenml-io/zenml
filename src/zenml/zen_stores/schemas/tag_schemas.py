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

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import VARCHAR, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from zenml.enums import ColorVariants, TaggableResourceTypes
from zenml.models import (
    TagRequest,
    TagResourceRequest,
    TagResourceResponse,
    TagResourceResponseBody,
    TagResponse,
    TagResponseBody,
    TagResponseMetadata,
    TagUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema, NamedSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema


class TagSchema(NamedSchema, table=True):
    """SQL Model for tag."""

    __tablename__ = "tag"
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="unique_tag_name",
        ),
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="tags")

    color: str = Field(sa_column=Column(VARCHAR(255), nullable=False))
    exclusive: bool = Field(default=False)

    links: List["TagResourceSchema"] = Relationship(
        back_populates="tag",
        sa_relationship_kwargs={"overlaps": "tags", "cascade": "delete"},
    )

    @classmethod
    def from_request(cls, request: TagRequest) -> "TagSchema":
        """Convert an `TagRequest` to an `TagSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=request.name,
            exclusive=request.exclusive,
            color=request.color.value,
            user_id=request.user,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> TagResponse:
        """Convert an `TagSchema` to an `TagResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `TagResponse`.
        """
        metadata = None
        if include_metadata:
            metadata = TagResponseMetadata()
        return TagResponse(
            id=self.id,
            name=self.name,
            body=TagResponseBody(
                user=self.user.to_model() if self.user else None,
                created=self.created,
                updated=self.updated,
                color=ColorVariants(self.color),
                exclusive=self.exclusive,
                tagged_count=len(self.links),
            ),
            metadata=metadata,
        )

    def update(self, update: TagUpdate) -> "TagSchema":
        """Updates a `TagSchema` from a `TagUpdate`.

        Args:
            update: The `TagUpdate` to update from.

        Returns:
            The updated `TagSchema`.
        """
        for field, value in update.model_dump(exclude_unset=True).items():
            if field == "color":
                setattr(self, field, value.value)
            else:
                setattr(self, field, value)

        self.updated = utc_now()
        return self


class TagResourceSchema(BaseSchema, table=True):
    """SQL Model for tag resource relationship."""

    __tablename__ = "tag_resource"
    __table_args__ = (
        build_index(
            table_name=__tablename__,
            column_names=[
                "resource_id",
                "resource_type",
                "tag_id",
            ],
        ),
    )

    tag_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=TagSchema.__tablename__,
        source_column="tag_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    tag: "TagSchema" = Relationship(
        back_populates="links", sa_relationship_kwargs={"overlaps": "tags"}
    )
    resource_id: UUID
    resource_type: str = Field(sa_column=Column(VARCHAR(255), nullable=False))

    @classmethod
    def from_request(cls, request: TagResourceRequest) -> "TagResourceSchema":
        """Convert an `TagResourceRequest` to an `TagResourceSchema`.

        Args:
            request: The request model version to convert.

        Returns:
            The converted schema.
        """
        return cls(
            tag_id=request.tag_id,
            resource_id=request.resource_id,
            resource_type=request.resource_type.value,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> TagResourceResponse:
        """Convert an `TagResourceSchema` to an `TagResourceResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `TagResourceResponse`.
        """
        return TagResourceResponse(
            id=self.id,
            body=TagResourceResponseBody(
                tag_id=self.tag_id,
                resource_id=self.resource_id,
                created=self.created,
                updated=self.updated,
                resource_type=TaggableResourceTypes(self.resource_type),
            ),
        )
