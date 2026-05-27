#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Resource request schemas."""

from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.step_run_schemas import StepRunSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.resource_pool_schemas import (
        ResourcePoolSchema,
    )


class ResourceRequestSchema(BaseSchema, table=True):
    """Resource request schema."""

    __tablename__ = "resource_request"
    __table_args__ = (
        UniqueConstraint(
            "step_run_id",
            name="unique_resource_request_step_run_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=["step_run_id", "status", "id"],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["component_id", "status", "created", "id"],
        ),
    )

    component_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="component_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    step_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StepRunSchema.__tablename__,
        source_column="step_run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    preemption_initiated_by_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=__tablename__,
        source_column="preemption_initiated_by_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship()
    component: Optional["StackComponentSchema"] = Relationship()
    step_run: Optional["StepRunSchema"] = Relationship(
        back_populates="resource_request"
    )
    preemption_initiated_by: Optional["ResourceRequestSchema"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[ResourceRequestSchema.preemption_initiated_by_id]",
            "remote_side": "ResourceRequestSchema.id",
        }
    )

    requested_resources: List["ResourceRequestResourceSchema"] = Relationship(
        back_populates="request",
        sa_relationship_kwargs={
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        },
    )
    pool: Optional["ResourcePoolSchema"] = Relationship(
        sa_relationship_kwargs={
            "secondary": "resource_pool_allocation",
            "primaryjoin": (
                "ResourceRequestSchema.id == ResourcePoolAllocationSchema.request_id"
            ),
            "secondaryjoin": (
                "ResourcePoolSchema.id == ResourcePoolAllocationSchema.pool_id"
            ),
            "uselist": False,
            "viewonly": True,
        }
    )
    status: str
    status_reason: Optional[str] = Field(default=None, nullable=True)
    preemptible: bool

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get the query options for the schema.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            **kwargs: Additional keyword arguments.

        Returns:
            A list of query options.
        """
        options = [
            selectinload(jl_arg(ResourceRequestSchema.requested_resources)),
        ]

        if include_resources:
            options.extend(
                [
                    selectinload(jl_arg(ResourceRequestSchema.component)),
                    selectinload(
                        jl_arg(ResourceRequestSchema.step_run)
                    ).joinedload(jl_arg(StepRunSchema.pipeline_run)),
                    selectinload(jl_arg(ResourceRequestSchema.pool)),
                    selectinload(jl_arg(ResourceRequestSchema.user)),
                ]
            )

        return options


class ResourceRequestResourceSchema(BaseSchema, table=True):
    """Resource request resource schema."""

    __tablename__ = "resource_request_resource"
    __table_args__ = (
        UniqueConstraint(
            "request_id",
            "key",
            name="unique_resource_request_resource_request_id_key",
        ),
    )

    request_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourceRequestSchema.__tablename__,
        source_column="request_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    request: "ResourceRequestSchema" = Relationship(
        back_populates="requested_resources"
    )
    key: str
    amount: int
