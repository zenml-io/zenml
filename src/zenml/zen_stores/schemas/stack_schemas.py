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
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from zenml.models import StackModel

if TYPE_CHECKING:
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

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)

    name: str
    is_shared: bool
    project_id: UUID = Field(
        foreign_key="projectschema.id",
    )
    owner: UUID = Field(
        foreign_key="userschema.id",
    )

    components: List["StackComponentSchema"] = Relationship(
        back_populates="stacks", link_model=StackCompositionSchema
    )

    @classmethod
    def from_create_model(
        cls,
        user_id: UUID,
        project_id: UUID,
        defined_components: List["StackComponentSchema"],
        stack: StackModel,
    ) -> "StackSchema":
        """Create an incomplete StackSchema with `id` and `created_at` missing.

        Returns:
            A StackSchema
        """

        return cls(
            name=stack.name,
            project_id=project_id,
            owner=user_id,
            is_shared=stack.is_shared,
            components=defined_components,
        )

    def from_update_model(
        self,
        defined_components: List["StackComponentSchema"],
        stack: StackModel,
    ) -> "StackSchema":
        """Update the updatable fields on an existing StackSchema.

        Returns:
            A StackSchema
        """
        self.name = stack.name
        self.is_shared = stack.is_shared
        self.components = defined_components
        return self

    def to_model(self) -> "StackModel":
        """Creates a ComponentModel from an instance of a StackSchema.

        Returns:
            a StackModel
        """
        return StackModel(
            id=self.id,
            name=self.name,
            user=self.owner,
            project=self.project_id,
            is_shared=self.is_shared,
            components={c.type: [c.id] for c in self.components},
        )
