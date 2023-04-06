#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""SQL Model Implementations for Service Connectors."""

import base64
import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship, SQLModel

from zenml.models import (
    ServiceConnectorRequestModel,
    ServiceConnectorResponseModel,
    ServiceConnectorUpdateModel,
)
from zenml.zen_stores.schemas.base_schemas import ShareableSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class ServiceConnectorSchema(ShareableSchema, table=True):
    """SQL Model for service connectors."""

    __tablename__ = "service_connector"

    type: str
    auth_method: str
    resource_type: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    resource_id: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    configuration: Optional[bytes]
    secret_reference: Optional[UUID]

    labels: List["ServiceConnectorLabelSchema"] = Relationship(
        back_populates="service_connector",
        sa_relationship_kwargs={"cascade": "delete"},
    )

    workspace_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    workspace: "WorkspaceSchema" = Relationship(
        back_populates="service_connectors"
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
        back_populates="service_connectors"
    )

    @classmethod
    def from_request(
        cls,
        connector_request: ServiceConnectorRequestModel,
    ) -> "ServiceConnectorSchema":
        """Create a `ServiceConnectorSchema` from a `ServiceConnectorRequestModel`.

        Args:
            connector_request: The `ServiceConnectorRequestModel` from which to
                create the schema.

        Returns:
            The created `ServiceConnectorSchema`.
        """
        assert connector_request.user is not None, "User must be set."
        return cls(
            workspace_id=connector_request.workspace,
            user_id=connector_request.user,
            is_shared=connector_request.is_shared,
            name=connector_request.name,
            type=connector_request.type,
            auth_method=connector_request.auth_method,
            resource_type=connector_request.resource_type,
            resource_id=connector_request.resource_id,
            configuration=base64.b64encode(
                json.dumps(connector_request.configuration).encode("utf-8")
            )
            if connector_request.configuration
            else None,
            secret_reference=connector_request.secret_reference,
        )

    def update(
        self, connector_update: ServiceConnectorUpdateModel
    ) -> "ServiceConnectorSchema":
        """Updates a `ServiceConnectorSchema` from a `ServiceConnectorUpdateModel`.

        Args:
            connector_update: The `ServiceConnectorUpdateModel` to update from.

        Returns:
            The updated `ServiceConnectorSchema`.
        """
        for field, value in connector_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "configuration":
                self.configuration = (
                    base64.b64encode(
                        json.dumps(connector_update.configuration).encode(
                            "utf-8"
                        )
                    )
                    if connector_update.configuration
                    else None
                )
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(
        self,
    ) -> "ServiceConnectorResponseModel":
        """Creates a `ServiceConnectorModel` from an instance of a `ServiceConnectorSchema`.

        Returns:
            A `ServiceConnectorModel`
        """
        return ServiceConnectorResponseModel(
            id=self.id,
            user=self.user.to_model(True) if self.user else None,
            workspace=self.workspace.to_model(),
            is_shared=self.is_shared,
            created=self.created,
            updated=self.updated,
            name=self.name,
            type=self.type,
            auth_method=self.auth_method,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            configuration=json.loads(
                base64.b64decode(self.configuration).decode()
            )
            if self.configuration
            else None,
            secret_reference=self.secret_reference,
            labels={label.name: label.value for label in self.labels},
        )


class ServiceConnectorLabelSchema(SQLModel, table=True):
    """SQL Model for service connector labels."""

    __tablename__ = "service_connector_label"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    value: str

    service_connector_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=ServiceConnectorSchema.__tablename__,
        source_column="service_connector_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
    )
    service_connector: ServiceConnectorSchema = Relationship(
        back_populates="labels"
    )
