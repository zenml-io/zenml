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
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

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

    type: str = Field(sa_column=Column(TEXT, nullable=False))
    admin_state: str = Field(sa_column=Column(TEXT, nullable=False))
    labels: Optional[bytes]
    configuration: bytes = Field(sa_column=Column(TEXT, nullable=False))
    status: bytes = Field(sa_column=Column(TEXT, nullable=False))
    endpoint: Optional[bytes]
    endpoint_url: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    health_check_url: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True)
    )

    model_versions_services_links: List[
        "ModelVersionServiceSchema"
    ] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    def to_model(
        self,
        hydrate: bool = False,
    ) -> ServiceResponse:
        """Convert an `ServiceSchemas` to an `ServiceResponse`.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The created `ServiceResponse`.
        """
        metadata = None
        if hydrate:
            metadata = ServiceResponseMetadata(
                workspace=self.workspace.to_model(),
                configuration=json.loads(self.configuration),
                status=json.loads(self.status),
                endpoint=json.loads(self.endpoint) if self.endpoint else None,
                admin_state=self.admin_state,
                endpoint_url=self.endpoint_url,
                health_check_url=self.health_check_url,
            )

        body = ServiceResponseBody(
            user=self.user.to_model() if self.user else None,
            workspace=self.workspace.to_model(),
            created=self.created,
            updated=self.updated,
            type=json.loads(self.type),
        )

        return ServiceResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )

    def update(
        self,
        service_update: ServiceUpdate,
    ) -> "ServiceSchemas":
        """Updates a `ServiceSchema` from a `ServiceUpdate`.

        Args:
            service_update: The `ServiceUpdate` to update from.

        Returns:
            The updated `ServiceSchema`.
        """
        for field, value in service_update.dict(
            exclude_unset=True, exclude_none=True
        ).items():
            if field == "configuration":
                self.configuration = base64.b64encode(
                    json.dumps(service_update.configuration).encode("utf-8")
                )
            elif field == "labels":
                self.labels = base64.b64encode(
                    json.dumps(service_update.labels).encode("utf-8")
                )
            elif field == "status":
                self.status = base64.b64encode(
                    json.dumps(service_update.status).encode("utf-8")
                )
            elif field == "endpoint":
                self.endpoint = base64.b64encode(
                    json.dumps(service_update.endpoint).encode("utf-8")
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
            type=service_request.type.json(),
            admin_state=service_request.admin_state,
            configuration=json.dumps(service_request.configuration),
            labels=json.dumps(service_request.labels).encode("utf-8")
            if service_request.labels
            else None,
            status=json.dumps(service_request.status),
            endpoint=json.dumps(service_request.endpoint)
            if service_request.endpoint
            else None,
            endpoint_url=service_request.endpoint_url,
            health_check_url=service_request.health_check_url,
        )
