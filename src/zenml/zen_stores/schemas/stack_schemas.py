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

from zenml.new_models.stack_models import StackResponseModel, StackUpdateModel
from zenml.zen_stores.schemas.base_schemas import ShareableSchema

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


class StackSchema(ShareableSchema, table=True):
    """SQL Model for stacks."""

    user_id: UUID = Field(
        sa_column=Column(ForeignKey("userschema.id", ondelete="SET NULL"))
    )
    project_id: UUID = Field(
        sa_column=Column(ForeignKey("projectschema.id", ondelete="CASCADE"))
    )
    project: "ProjectSchema" = Relationship(back_populates="stacks")
    user: "UserSchema" = Relationship(back_populates="stacks")

    components: List["StackComponentSchema"] = Relationship(
        back_populates="stacks",
        link_model=StackCompositionSchema,
    )
    runs: List["PipelineRunSchema"] = Relationship(back_populates="stack")

    def update(
        self,
        stack_update: StackUpdateModel,
        components: List["StackComponentSchema"],
    ):
        for field, value in stack_update.dict(exclude_unset=True).items():
            if field == "components":
                self.components = components

            elif field == "user":
                assert self.user_id == value

            elif field == "project":
                assert self.project_id == value

            else:
                setattr(self, field, value)

        self.updated = datetime.now()
        return self

    def to_model(self) -> StackResponseModel:
        """Creates a `HydratedStackModel` from an instance of a 'StackSchema'.

        Returns:
            a 'HydratedStackModel'.
        """
        return StackResponseModel(
            id=self.id,
            name=self.name,
            user=self.user.to_model(),
            project=self.project.to_model(),
            is_shared=self.is_shared,
            components={c.type: [c.to_model()] for c in self.components},
            created=self.created,
            updated=self.updated,
        )
