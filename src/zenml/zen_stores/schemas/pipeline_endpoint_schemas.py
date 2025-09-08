#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""SQLModel implementation of pipeline endpoint table."""

import json
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, String

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.enums import PipelineEndpointStatus
from zenml.models.v2.core.pipeline_endpoint import (
    PipelineEndpointRequest,
    PipelineEndpointResponse,
    PipelineEndpointResponseBody,
    PipelineEndpointResponseMetadata,
    PipelineEndpointResponseResources,
    PipelineEndpointUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.component_schemas import StackComponentSchema
from zenml.zen_stores.schemas.pipeline_deployment_schemas import (
    PipelineDeploymentSchema,
)
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class PipelineEndpointSchema(NamedSchema, table=True):
    """SQL Model for pipeline endpoint."""

    __tablename__ = "pipeline_endpoint"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_pipeline_endpoint_name_in_project",
        ),
    )

    project_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ProjectSchema.__tablename__,
        source_column="project_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    project: "ProjectSchema" = Relationship(
        back_populates="pipeline_endpoints"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(
        back_populates="pipeline_endpoints"
    )

    status: str
    url: Optional[str] = Field(
        default=None,
        sa_column=Column(TEXT, nullable=True),
    )
    auth_key: Optional[str] = Field(
        default=None,
        sa_column=Column(TEXT, nullable=True),
    )
    endpoint_metadata: str = Field(
        default="{}",
        sa_column=Column(
            String(length=MEDIUMTEXT_MAX_LENGTH).with_variant(
                MEDIUMTEXT, "mysql"
            ),
            nullable=False,
        ),
    )
    pipeline_deployment_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_deployment",
        source_column="pipeline_deployment_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline_deployment: Optional["PipelineDeploymentSchema"] = Relationship(
        back_populates="pipeline_endpoints",
    )

    deployer_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=StackComponentSchema.__tablename__,
        source_column="deployer_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    deployer: Optional["StackComponentSchema"] = Relationship()

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

        if include_resources:
            options.extend(
                [
                    joinedload(jl_arg(PipelineEndpointSchema.user)),
                    joinedload(
                        jl_arg(PipelineEndpointSchema.pipeline_deployment)
                    ),
                    joinedload(jl_arg(PipelineEndpointSchema.deployer)),
                ]
            )

        return options

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> PipelineEndpointResponse:
        """Convert a `PipelineEndpointSchema` to a `PipelineEndpointResponse`.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            kwargs: Additional keyword arguments.

        Returns:
            The created `PipelineEndpointResponse`.
        """
        body = PipelineEndpointResponseBody(
            user_id=self.user_id,
            project_id=self.project_id,
            created=self.created,
            updated=self.updated,
            url=self.url,
            status=self.status,
        )

        metadata = None
        if include_metadata:
            metadata = PipelineEndpointResponseMetadata(
                pipeline_deployment_id=self.pipeline_deployment_id,
                deployer_id=self.deployer_id,
                endpoint_metadata=json.loads(self.endpoint_metadata),
                auth_key=self.auth_key,
            )

        resources = None
        if include_resources:
            resources = PipelineEndpointResponseResources(
                user=self.user.to_model() if self.user else None,
                pipeline_deployment=self.pipeline_deployment.to_model()
                if self.pipeline_deployment
                else None,
                deployer=self.deployer.to_model() if self.deployer else None,
            )

        return PipelineEndpointResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(
        self,
        update: PipelineEndpointUpdate,
    ) -> "PipelineEndpointSchema":
        """Updates a `PipelineEndpointSchema` from a `PipelineEndpointUpdate`.

        Args:
            update: The `PipelineEndpointUpdate` to update from.

        Returns:
            The updated `PipelineEndpointSchema`.
        """
        for field, value in update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            if field == "endpoint_metadata":
                setattr(self, field, json.dumps(value))
            elif hasattr(self, field):
                setattr(self, field, value)

        self.updated = utc_now()
        return self

    @classmethod
    def from_request(
        cls, request: PipelineEndpointRequest
    ) -> "PipelineEndpointSchema":
        """Convert a `PipelineEndpointRequest` to a `PipelineEndpointSchema`.

        Args:
            request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=request.name,
            project_id=request.project,
            user_id=request.user,
            status=PipelineEndpointStatus.UNKNOWN.value,
            pipeline_deployment_id=request.pipeline_deployment_id,
            deployer_id=request.deployer_id,
            auth_key=request.auth_key,
        )
