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
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from pydantic.json import pydantic_encoder
from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.models.v2.core.service import (
    ServiceRequest,
    ServiceResponse,
    ServiceResponseBody,
    ServiceResponseMetadata,
    ServiceUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.model_schemas import (
        ModelVersionServiceSchema,
    )


class ServiceSchemas(NamedSchema, table=True):
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
    run_name: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    pipeline_step_name: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )
    model_name: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    model_version: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))

    model_versions_services_links: List["ModelVersionServiceSchema"] = (
        Relationship(
            back_populates="service",
            sa_relationship_kwargs={"cascade": "delete"},
        )
    )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ServiceResponse:
        """Convert an `ServiceSchemas` to an `ServiceResponse`.

        Args:
            include_metadata: Whether to include metadata in the response.
            include_resources: Whether to include resources in the response.
            kwargs: Additional keyword arguments.

        Returns:
            The created `ServiceResponse`.
        """
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

        body = ServiceResponseBody(
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            service_type=json.loads(self.service_type),
            labels=json.loads(base64.b64decode(self.labels).decode())
            if self.labels
            else None,
        )

        return ServiceResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )

    def update(
        self,
        update: ServiceUpdate,
    ) -> "ServiceSchemas":
        """Updates a `ServiceSchema` from a `ServiceUpdate`.

        Args:
            update: The `ServiceUpdate` to update from.

        Returns:
            The updated `ServiceSchema`.
        """
        for field, value in update.dict(
            exclude_unset=True, exclude_none=True
        ).items():
            if field == "config":
                self.config = base64.b64encode(
                    json.dumps(update.config, default=pydantic_encoder).encode(
                        "utf-8"
                    )
                )
            elif field == "labels":
                self.labels = base64.b64encode(
                    json.dumps(update.labels, default=pydantic_encoder).encode(
                        "utf-8"
                    )
                )
            elif field == "status":
                self.status = base64.b64encode(
                    json.dumps(update.status, default=pydantic_encoder).encode(
                        "utf-8"
                    )
                )
            elif field == "endpoint":
                self.endpoint = base64.b64encode(
                    json.dumps(
                        update.endpoint, default=pydantic_encoder
                    ).encode("utf-8")
                )
            else:
                setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self

    @classmethod
    def from_request(
        cls, service_request: "ServiceRequest"
    ) -> "ServiceSchemas":
        """Convert a `ServiceRequest` to a `ServiceSchemas`.

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
            service_type=service_request.service_type.json(),
            type=service_request.service_type.type,
            flavor=service_request.service_type.flavor,
            admin_state=service_request.admin_state,
            config=base64.b64encode(
                json.dumps(
                    service_request.config,
                    sort_keys=False,
                    default=pydantic_encoder,
                ).encode("utf-8")
            ),
            labels=base64.b64encode(
                json.dumps(
                    service_request.labels,
                    sort_keys=False,
                    default=pydantic_encoder,
                ).encode("utf-8")
            )
            if service_request.labels
            else None,
            status=base64.b64encode(
                json.dumps(
                    service_request.status,
                    sort_keys=False,
                    default=pydantic_encoder,
                ).encode("utf-8")
            )
            if service_request.status
            else None,
            endpoint=base64.b64encode(
                json.dumps(
                    service_request.endpoint,
                    sort_keys=False,
                    default=pydantic_encoder,
                ).encode("utf-8")
            )
            if service_request.endpoint
            else None,
            prediction_url=service_request.prediction_url,
            health_check_url=service_request.health_check_url,
            run_name=service_request.config.get("run_name"),
            pipeline_step_name=service_request.config.get(
                "pipeline_step_name"
            ),
            model_name=service_request.config.get("model_name"),
            model_version=service_request.config.get("model_version"),
        )
