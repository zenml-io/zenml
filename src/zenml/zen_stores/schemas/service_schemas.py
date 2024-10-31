#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""SQLModel implementation of service table."""

import base64
import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.v2.core.service import (
    ServiceRequest,
    ServiceResponse,
    ServiceResponseBody,
    ServiceResponseMetadata,
    ServiceResponseResources,
    ServiceUpdate,
)
from zenml.utils.dict_utils import dict_to_bytes
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.model_schemas import ModelVersionSchema
from zenml.zen_stores.schemas.pipeline_run_schemas import PipelineRunSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class ServiceSchema(NamedSchema, table=True):
    """SQL Model for service."""

    __tablename__ = "service"

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(back_populates="services")

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="services")
    service_source: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    service_type: str = Field(sa_column=Column(TEXT, nullable=False))
    type: str = Field(sa_column=Column(TEXT, nullable=False))
    flavor: str = Field(sa_column=Column(TEXT, nullable=False))
    admin_state: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    state: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    labels: Optional[bytes]
    config: bytes
    status: Optional[bytes]
    endpoint: Optional[bytes]
    prediction_url: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    health_check_url: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    pipeline_name: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    pipeline_step_name: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    model_version_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=ModelVersionSchema.__tablename__,  # type: ignore[has-type]
        source_column="model_version_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    model_version: Optional["ModelVersionSchema"] = Relationship(
        back_populates="services",
    )
    pipeline_run_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target="pipeline_run",
        source_column="pipeline_run_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    pipeline_run: Optional["PipelineRunSchema"] = Relationship(
        back_populates="services",
    )

    # TODO: In Pydantic v2, the `model_` is a protected namespaces for all
    #  fields defined under base models. If not handled, this raises a warning.
    #  It is possible to suppress this warning message with the following
    #  configuration, however the ultimate solution is to rename these fields.
    #  Even though they do not cause any problems right now, if we are not
    #  careful we might overwrite some fields protected by pydantic.
    model_config = ConfigDict(protected_namespaces=())  # type: ignore[assignment]

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ServiceResponse:
        """Convert an `ServiceSchema` to an `ServiceResponse`.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            kwargs: Additional keyword arguments.

        Returns:
            The created `ServiceResponse`.
        """
        body = ServiceResponseBody(
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            service_type=json.loads(self.service_type),
            labels=json.loads(base64.b64decode(self.labels).decode())
            if self.labels
            else None,
            state=self.state,
        )
        metadata = None
        if include_metadata:
            metadata = ServiceResponseMetadata(
                workspace=self.workspace.to_model(),
                service_source=self.service_source,
                config=json.loads(base64.b64decode(self.config).decode()),
                status=json.loads(base64.b64decode(self.status).decode())
                if self.status
                else None,
                endpoint=json.loads(base64.b64decode(self.endpoint).decode())
                if self.endpoint
                else None,
                admin_state=self.admin_state or None,
                prediction_url=self.prediction_url or None,
                health_check_url=self.health_check_url,
            )
        resources = None
        if include_resources:
            resources = ServiceResponseResources(
                model_version=self.model_version.to_model()
                if self.model_version
                else None,
                pipeline_run=self.pipeline_run.to_model()
                if self.pipeline_run
                else None,
            )
        return ServiceResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )

    def update(
        self,
        update: ServiceUpdate,
    ) -> "ServiceSchema":
        """Updates a `ServiceSchema` from a `ServiceUpdate`.

        Args:
            update: The `ServiceUpdate` to update from.

        Returns:
            The updated `ServiceSchema`.
        """
        for field, value in update.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            if field == "labels":
                self.labels = (
                    dict_to_bytes(update.labels) if update.labels else None
                )
            elif field == "status":
                self.status = (
                    dict_to_bytes(update.status) if update.status else None
                )
                self.state = (
                    update.status.get("state") if update.status else None
                )
            elif field == "endpoint":
                self.endpoint = (
                    dict_to_bytes(update.endpoint) if update.endpoint else None
                )
            else:
                setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self

    @classmethod
    def from_request(
        cls, service_request: "ServiceRequest"
    ) -> "ServiceSchema":
        """Convert a `ServiceRequest` to a `ServiceSchema`.

        Args:
            service_request: The request model to convert.

        Returns:
            The converted schema.
        """
        return cls(
            name=service_request.name,
            workspace_id=service_request.workspace,
            user_id=service_request.user,
            service_source=service_request.service_source,
            service_type=service_request.service_type.model_dump_json(),
            type=service_request.service_type.type,
            flavor=service_request.service_type.flavor,
            admin_state=service_request.admin_state,
            config=dict_to_bytes(service_request.config),
            labels=dict_to_bytes(service_request.labels)
            if service_request.labels
            else None,
            status=dict_to_bytes(service_request.status)
            if service_request.status
            else None,
            endpoint=dict_to_bytes(service_request.endpoint)
            if service_request.endpoint
            else None,
            state=service_request.status.get("state")
            if service_request.status
            else None,
            model_version_id=service_request.model_version_id,
            pipeline_run_id=service_request.pipeline_run_id,
            prediction_url=service_request.prediction_url,
            health_check_url=service_request.health_check_url,
            pipeline_name=service_request.config.get("pipeline_name"),
            pipeline_step_name=service_request.config.get(
                "pipeline_step_name"
            ),
        )
