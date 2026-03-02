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
"""Resource pool subject policy schemas."""

from typing import TYPE_CHECKING, Any, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.models import (
    ResourcePoolSubjectPolicyRequest,
    ResourcePoolSubjectPolicyResponse,
    ResourcePoolSubjectPolicyResponseBody,
    ResourcePoolSubjectPolicyResponseMetadata,
    ResourcePoolSubjectPolicyResponseResources,
    ResourcePoolSubjectPolicyUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import BaseSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.resource_pool_schemas import (
        ResourcePoolSchema,
    )


class ResourcePoolSubjectPolicySchema(BaseSchema, table=True):
    """Resource pool subject policy schema."""

    __tablename__ = "resource_pool_subject_policy"
    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "pool_id",
            name="unique_component_id_pool_id",
        ),
        build_index(
            table_name=__tablename__,
            column_names=["pool_id", "priority", "component_id"],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["component_id", "priority", "pool_id"],
        ),
        build_index(
            table_name=__tablename__,
            column_names=["pool_id", "component_id"],
        ),
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

    component_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="component_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    component: "StackComponentSchema" = Relationship()
    pool_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target="resource_pool",
        source_column="pool_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    pool: "ResourcePoolSchema" = Relationship()

    priority: int
    resources: List["ResourcePoolSubjectPolicyResourceSchema"] = Relationship(
        back_populates="policy",
        sa_relationship_kwargs={
            "passive_deletes": True,
            "cascade": "all, delete-orphan",
        },
    )

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Gets query options for this schema.

        Args:
            include_metadata: If metadata should be included.
            include_resources: If resources should be included.

        Returns:
            The query options.
        """
        options: List[ExecutableOption] = [
            selectinload(jl_arg(ResourcePoolSubjectPolicySchema.resources)),
        ]

        if include_resources:
            options.extend(
                [
                    selectinload(
                        jl_arg(ResourcePoolSubjectPolicySchema.component)
                    ),
                    selectinload(jl_arg(ResourcePoolSubjectPolicySchema.pool)),
                    selectinload(jl_arg(ResourcePoolSubjectPolicySchema.user)),
                ]
            )

        return options

    @classmethod
    def from_request(
        cls, request: ResourcePoolSubjectPolicyRequest
    ) -> "ResourcePoolSubjectPolicySchema":
        """Creates a schema instance from a request model.

        Args:
            request: The request model.

        Returns:
            The schema instance.
        """
        return cls(
            user_id=request.user,
            component_id=request.component_id,
            pool_id=request.pool_id,
            priority=request.priority,
        )

    def update(
        self, update: ResourcePoolSubjectPolicyUpdate
    ) -> "ResourcePoolSubjectPolicySchema":
        """Updates this schema from an update model.

        Args:
            update: The update model.

        Returns:
            The updated schema.
        """
        if update.priority is not None:
            self.priority = update.priority

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "ResourcePoolSubjectPolicyResponse":
        """Converts this schema to a response model.

        Args:
            include_metadata: Whether to include metadata.
            include_resources: Whether to include nested resources.
            **kwargs: Additional keyword arguments.

        Returns:
            The response model.
        """
        body = ResourcePoolSubjectPolicyResponseBody(
            created=self.created,
            updated=self.updated,
            user_id=self.user_id,
            priority=self.priority,
            reserved={
                resource.key: resource.reserved for resource in self.resources
            },
            limit={
                resource.key: resource.limit
                for resource in self.resources
                if resource.limit is not None
            },
        )

        metadata = None
        if include_metadata:
            metadata = ResourcePoolSubjectPolicyResponseMetadata()

        resources = None
        if include_resources:
            resources = ResourcePoolSubjectPolicyResponseResources(
                user=self.user.to_model() if self.user else None,
                component=self.component.to_model(),
                pool=self.pool.to_model(
                    include_metadata=False, include_resources=False
                ),
            )

        return ResourcePoolSubjectPolicyResponse(
            id=self.id,
            body=body,
            metadata=metadata,
            resources=resources,
        )


class ResourcePoolSubjectPolicyResourceSchema(BaseSchema, table=True):
    """Resource pool subject policy resource schema."""

    __tablename__ = "resource_pool_subject_policy_resource"
    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "key",
            name="unique_resource_pool_subject_policy_resource",
        ),
    )
    policy_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ResourcePoolSubjectPolicySchema.__tablename__,
        source_column="policy_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        custom_constraint_name="fk_pool_subject_policy_resource_policy_id",
    )
    key: str
    reserved: int = Field(default=0, nullable=False)
    limit: Optional[int] = Field(default=None, nullable=True)

    policy: Optional["ResourcePoolSubjectPolicySchema"] = Relationship(
        back_populates="resources"
    )
