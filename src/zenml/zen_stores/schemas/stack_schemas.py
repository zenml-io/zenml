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
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from zenml.models import HydratedStackModel, StackModel

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import (
        PipelineRunSchema,
        ProjectSchema,
        UserSchema,
    )
    from zenml.zen_stores.schemas.component_schemas import StackComponentSchema


class StackCompositionSchema(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    stack_id: UUID = Field(primary_key=True, foreign_key="stackschema.id")
    component_id: UUID = Field(
        primary_key=True, foreign_key="stackcomponentschema.id"
    )


class StackSchema(SQLModel, table=True):
    """SQL Model for stacks."""

    id: UUID = Field(primary_key=True)
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

    name: str
    is_shared: bool

    project_id: UUID = Field(
        sa_column=Column(ForeignKey("projectschema.id", ondelete="CASCADE"))
    )
    project: "ProjectSchema" = Relationship(back_populates="stacks")

    user_id: UUID = Field(
        sa_column=Column(ForeignKey("userschema.id", ondelete="SET NULL"))
    )
    user: "UserSchema" = Relationship(back_populates="stacks")

    components: List["StackComponentSchema"] = Relationship(
        back_populates="stacks", link_model=StackCompositionSchema
    )
    runs: List["PipelineRunSchema"] = Relationship(
        back_populates="stack",
    )

    @classmethod
    def from_create_model(
        cls,
        defined_components: List["StackComponentSchema"],
        stack: StackModel,
    ) -> "StackSchema":
        """Create a StackSchema.

        Args:
            defined_components: The components that are part of the stack.
            stack: The stack model to create the schema from.

        Returns:
            A StackSchema
        """
        return cls(
            id=stack.id,
            name=stack.name,
            project_id=stack.project,
            user_id=stack.user,
            is_shared=stack.is_shared,
            components=defined_components,
        )

    def from_update_model(
        self,
        defined_components: List["StackComponentSchema"],
        stack: StackModel,
    ) -> "StackSchema":
        """Update the updatable fields on an existing `StackSchema`.

        Args:
            defined_components: The components that are part of the stack.
            stack: The stack model to create the schema from.

        Returns:
            A `StackSchema`
        """
        self.name = stack.name
        self.is_shared = stack.is_shared
        self.components = defined_components
        self.updated = datetime.now()
        return self

    def to_model(self) -> "StackModel":
        """Creates a `StackModel` from an instance of a `StackSchema`.

        Returns:
            a `StackModel`.
        """
        # This needs to be updated once multiple stack components per type are
        #  supported
        return StackModel(
            id=self.id,
            name=self.name,
            user=self.user_id,
            project=self.project_id,
            is_shared=self.is_shared,
            components={c.type: [c.id] for c in self.components},
            created=self.created,
            updated=self.updated,
        )

    def to_hydrated_model(self) -> "HydratedStackModel":
        """Creates a `HydratedStackModel` from an instance of a 'StackSchema'.

        Returns:
            a 'HydratedStackModel'.
        """
        return HydratedStackModel(
            id=self.id,
            name=self.name,
            user=self.user.to_model(),
            project=self.project.to_model(),
            is_shared=self.is_shared,
            components={c.type: [c.to_model()] for c in self.components},
            created=self.created,
            updated=self.updated,
        )
