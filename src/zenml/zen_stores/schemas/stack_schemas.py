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

from zenml.models import (
    StackResponse,
    StackResponseBody,
    StackResponseMetadata,
    StackUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.component_schemas import (
        StackComponentSchema,
    )
    from zenml.zen_stores.schemas.pipeline_build_schemas import (
        PipelineBuildSchema,
    )
    from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
        PipelineDeploymentSchema,
    )


class StackCompositionSchema(SQLModel, table=True):
    """SQL Model for stack definitions.

    Join table between Stacks and StackComponents.
    """

    __tablename__ = "stack_composition"

    stack_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="stack",
        source_column="stack_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    component_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="stack_component",
        source_column="component_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )


class StackSchema(NamedSchema, table=True):
    """SQL Model for stacks."""

    __tablename__ = "stack"
    stack_spec_path: Optional[str]

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="stacks")

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
    builds: List["PipelineBuildSchema"] = Relationship(back_populates="stack")
    deployments: List["PipelineDeploymentSchema"] = Relationship(
        back_populates="stack",
    )

    def update(
        self,
        stack_update: "StackUpdate",
        components: List["StackComponentSchema"],
    ) -> "StackSchema":
        """Updates a stack schema with a stack update model.

        Args:
            stack_update: `StackUpdate` to update the stack with.
            components: List of `StackComponentSchema` to update the stack with.

        Returns:
            The updated StackSchema.
        """
        for field, value in stack_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "components":
                self.components = components
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self, hydrate: bool = False) -> "StackResponse":
        """Converts the schema to a model.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The converted model.
        """
        body = StackResponseBody(
            user=self.user.to_model() if self.user else None,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if hydrate:
            metadata = StackResponseMetadata(
                workspace=self.workspace.to_model(),
                components={c.type: [c.to_model()] for c in self.components},
                stack_spec_path=self.stack_spec_path,
            )

        return StackResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )
