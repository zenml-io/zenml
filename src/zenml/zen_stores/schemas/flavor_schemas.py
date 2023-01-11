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
"""SQL Model Implementations for Flavors."""

from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import StackComponentType
from zenml.models.flavor_models import FlavorResponseModel
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema


class FlavorSchema(NamedSchema, table=True):
    """SQL Model for flavors.

    Attributes:
        type: The type of the flavor.
        source: The source of the flavor.
        config_schema: The config schema of the flavor.
        integration: The integration associated with the flavor.
    """

    __tablename__ = "flavor"

    type: StackComponentType
    source: str
    config_schema: str = Field(sa_column=Column(TEXT, nullable=False))
    integration: Optional[str] = Field(default="")

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="flavors")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="flavors")

    def to_model(self) -> FlavorResponseModel:
        """Converts a flavor schema to a flavor model.

        Returns:
            The flavor model.
        """
        return FlavorResponseModel(
            id=self.id,
            name=self.name,
            type=self.type,
            source=self.source,
            config_schema=self.config_schema,
            integration=self.integration,
            user=self.user.to_model() if self.user else None,
            project=self.project.to_model(),
            created=self.created,
            updated=self.updated,
        )
