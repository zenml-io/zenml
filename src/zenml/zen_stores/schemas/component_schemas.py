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
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Relationship

from zenml.enums import StackComponentType
from zenml.models.component_models import (
    ComponentResponseModel,
    ComponentUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import ShareableSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.stack_schemas import StackCompositionSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas import StackSchema


class StackComponentSchema(ShareableSchema, table=True):
    """SQL Model for stack components."""

    __tablename__ = "stack_component"

    type: StackComponentType
    flavor: str
    configuration: bytes

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(back_populates="components")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="components")

    stacks: List["StackSchema"] = Relationship(
        back_populates="components", link_model=StackCompositionSchema
    )

    def update(
        self, component_update: ComponentUpdateModel
    ) -> "StackComponentSchema":
        """Updates a `StackSchema` from a `ComponentUpdateModel`.

        Args:
            component_update: The `ComponentUpdateModel` to update from.

        Returns:
            The updated `StackComponentSchema`.
        """
        for field, value in component_update.dict(
            exclude_unset=True, exclude={"project", "user"}
        ).items():
            if field == "configuration":
                self.configuration = base64.b64encode(
                    json.dumps(component_update.configuration).encode("utf-8")
                )
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

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
            user=self.user.to_model() if self.user else None,
            project=self.project.to_model(),
            is_shared=self.is_shared,
            configuration=json.loads(
                base64.b64decode(self.configuration).decode()
            ),
            created=self.created,
            updated=self.updated,
        )
