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
"""SQL Model Implementations for Stacks."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Relationship, SQLModel

from zenml.models import StackResponseModel
from zenml.zen_stores.schemas.base_schemas import ShareableSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema

if TYPE_CHECKING:
    from zenml.models.stack_models import StackUpdateModel
    from zenml.zen_stores.schemas import PipelineRunSchema, StackComponentSchema


class StackCompositionSchema(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    __tablename__ = "stack_composition"

    stack_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="stack",  # TODO: how to reference `StackSchema.__tablename__`?
        source_column="stack_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    component_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="stack_component",  # TODO: how to reference `StackComponentSchema.__tablename__`?
        source_column="component_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )


class StackSchema(ShareableSchema, table=True):
    """SQL Model for stacks."""

    __tablename__ = "stack"

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="stacks")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="stacks")

    components: List["StackComponentSchema"] = Relationship(
        back_populates="stacks",
        link_model=StackCompositionSchema,
    )
    runs: List["PipelineRunSchema"] = Relationship(back_populates="stack")

    def update(
        self,
        stack_update: "StackUpdateModel",
        components: List["StackComponentSchema"],
    ) -> "StackSchema":
        """Updates a stack schema with a stack update model.

        Args:
            stack_update: `StackUpdateModel` to update the stack with.
            components: List of `StackComponentSchema` to update the stack with.

        Returns:
            The updated StackSchema.
        """
        for field, value in stack_update.dict(exclude_unset=True).items():
            if field == "components":
                self.components = components

            elif field == "user":
                assert self.user_id == value

            elif field == "project":
                assert self.project_id == value

            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self) -> "StackResponseModel":
        """Converts the schema to a model.

        Returns:
            The converted model.
        """
        return StackResponseModel(
            id=self.id,
            name=self.name,
            user=self.user.to_model() if self.user else None,
            project=self.project.to_model(),
            is_shared=self.is_shared,
            components={c.type: [c.to_model()] for c in self.components},
            created=self.created,
            updated=self.updated,
        )
