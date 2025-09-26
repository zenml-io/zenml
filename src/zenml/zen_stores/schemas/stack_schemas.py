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

import base64
import json
from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import joinedload, object_session
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, SQLModel, select

from zenml.enums import SecretResourceTypes, StackComponentType
from zenml.models import (
    StackRequest,
    StackResponse,
    StackResponseBody,
    StackResponseMetadata,
    StackResponseResources,
    StackUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.component_schemas import (
        StackComponentSchema,
    )
    from zenml.zen_stores.schemas.pipeline_build_schemas import (
        PipelineBuildSchema,
    )
    from zenml.zen_stores.schemas.pipeline_snapshot_schemas import (
        PipelineSnapshotSchema,
    )
    from zenml.zen_stores.schemas.secret_schemas import SecretSchema


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
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="unique_stack_name",
        ),
    )

    description: Optional[str] = Field(default=None)
    stack_spec_path: Optional[str]
    labels: Optional[bytes]
    environment: Optional[bytes] = Field(default=None)

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
    snapshots: List["PipelineSnapshotSchema"] = Relationship(
        back_populates="stack",
    )
    secrets: List["SecretSchema"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin=f"and_(foreign(SecretResourceSchema.resource_type)=='{SecretResourceTypes.STACK.value}', foreign(SecretResourceSchema.resource_id)==StackSchema.id)",
            secondary="secret_resource",
            secondaryjoin="SecretSchema.id == foreign(SecretResourceSchema.secret_id)",
            order_by="SecretSchema.name",
            overlaps="secrets",
        ),
    )

    @property
    def has_deployer(self) -> bool:
        """If the stack has a deployer component.

        Returns:
            If the stack has a deployer component.

        Raises:
            RuntimeError: if the stack has no DB session.
        """
        from zenml.zen_stores.schemas import (
            StackComponentSchema,
            StackCompositionSchema,
        )

        if session := object_session(self):
            query = (
                select(StackComponentSchema.id)
                .where(
                    StackComponentSchema.type
                    == StackComponentType.DEPLOYER.value
                )
                .where(
                    StackCompositionSchema.component_id
                    == StackComponentSchema.id
                )
                .where(StackCompositionSchema.stack_id == self.id)
            )

            return session.execute(query).first() is not None
        else:
            raise RuntimeError(
                "Missing DB session to check if stack has a deployer component."
            )

    @classmethod
    def from_request(
        cls,
        request: "StackRequest",
        components: Sequence["StackComponentSchema"],
    ) -> "StackSchema":
        """Create a stack schema from a request.

        Args:
            request: The request from which to create the stack.
            components: List of components to link to the stack.

        Returns:
            The stack schema.
        """
        return cls(
            user_id=request.user,
            stack_spec_path=request.stack_spec_path,
            name=request.name,
            description=request.description,
            components=components,
            labels=base64.b64encode(
                json.dumps(request.labels).encode("utf-8")
            ),
            environment=base64.b64encode(
                json.dumps(request.environment).encode("utf-8")
            ),
        )

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get the query options for the schema.

        Args:
            include_metadata: Whether metadata will be included when converting
                the schema to a model.
            include_resources: Whether resources will be included when
                converting the schema to a model.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            A list of query options.
        """
        options = []

        # if include_metadata:
        #     options.extend(
        #         [
        #             joinedload(jl_arg(StackSchema.components)).joinedload(
        #                 jl_arg(StackComponentSchema.flavor_schema)
        #             ),
        #         ]
        #     )

        if include_resources:
            options.extend([joinedload(jl_arg(StackSchema.user))])

        return options

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
        for field, value in stack_update.model_dump(
            exclude_unset=True,
            exclude={"user", "add_secrets", "remove_secrets"},
        ).items():
            if field == "components":
                self.components = components
            elif field == "labels":
                self.labels = base64.b64encode(
                    json.dumps(stack_update.labels).encode("utf-8")
                )
            elif field == "environment":
                self.environment = base64.b64encode(
                    json.dumps(stack_update.environment).encode("utf-8")
                )
            else:
                setattr(self, field, value)

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "StackResponse":
        """Converts the schema to a model.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic

        Returns:
            The converted model.
        """
        body = StackResponseBody(
            user_id=self.user_id,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            environment = None
            if self.environment:
                environment = json.loads(
                    base64.b64decode(self.environment).decode()
                )
            metadata = StackResponseMetadata(
                components={c.type: [c.to_model()] for c in self.components},
                stack_spec_path=self.stack_spec_path,
                labels=json.loads(base64.b64decode(self.labels).decode())
                if self.labels
                else None,
                description=self.description,
                environment=environment or {},
                secrets=[secret.id for secret in self.secrets],
            )
        resources = None
        if include_resources:
            resources = StackResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return StackResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
