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
"""SQL Model Implementations for Stack Components."""

import base64
import json
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship

from zenml.enums import StackComponentType
from zenml.new_models.component_models import ComponentResponseModel
from zenml.zen_stores.schemas.base_schemas import ShareableSchema
from zenml.zen_stores.schemas.stack_schemas import StackCompositionSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import ProjectSchema, UserSchema
    from zenml.zen_stores.schemas.stack_schemas import StackSchema


class StackComponentSchema(ShareableSchema, table=True):
    """SQL Model for stack components."""

    type: StackComponentType
    flavor: str
    configuration: bytes

    user_id: UUID = Field(
        sa_column=Column(ForeignKey("userschema.id", ondelete="SET NULL"))
    )
    project_id: UUID = Field(
        sa_column=Column(ForeignKey("projectschema.id", ondelete="CASCADE"))
    )
    project: "ProjectSchema" = Relationship(back_populates="components")
    user: "UserSchema" = Relationship(back_populates="components")
    stacks: List["StackSchema"] = Relationship(
        back_populates="components", link_model=StackCompositionSchema
    )

    def to_model(self) -> "ComponentResponseModel":
        """Creates a `ComponentModel` from an instance of a `StackSchema`.

        Returns:
            A `ComponentModel`
        """
        return ComponentResponseModel(
            id=self.id,
            name=self.name,
            type=self.type,
            flavor=self.flavor,
            user=self.user.to_model(_block_recursion=True),
            project=self.project.to_model(),
            is_shared=self.is_shared,
            configuration=json.loads(
                base64.b64decode(self.configuration).decode()
            ),
            created=self.created,
            updated=self.updated,
        )
