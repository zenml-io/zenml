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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, cast
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.models import (
    ServiceConnectorRequest,
    ServiceConnectorResponse,
    ServiceConnectorResponseBody,
    ServiceConnectorResponseMetadata,
    ServiceConnectorResponseResources,
    ServiceConnectorUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg

if TYPE_CHECKING:
    from zenml.zen_stores.schemas.component_schemas import StackComponentSchema


class ServiceConnectorSchema(NamedSchema, table=True):
    """SQL Model for service connectors."""

    __tablename__ = "service_connector"
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="unique_service_connector_name",
        ),
    )

    connector_type: str = Field(sa_column=Column(TEXT))
    description: str
    auth_method: str = Field(sa_column=Column(TEXT))
    resource_types: bytes
    resource_id: Optional[str] = Field(sa_column=Column(TEXT, nullable=True))
    supports_instances: bool
    configuration: Optional[bytes]
    secret_id: Optional[UUID]
    expires_at: Optional[datetime]
    expires_skew_tolerance: Optional[int]
    expiration_seconds: Optional[int]
    labels: Optional[bytes]

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
    components: List["StackComponentSchema"] = Relationship(
        back_populates="connector",
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

        if include_resources:
            options.extend([joinedload(jl_arg(ServiceConnectorSchema.user))])

        return options

    @property
    def resource_types_list(self) -> List[str]:
        """Returns the resource types as a list.

        Returns:
            The resource types as a list.
        """
        resource_types = json.loads(
            base64.b64decode(self.resource_types).decode()
        )
        assert isinstance(resource_types, list)
        return resource_types

    @property
    def labels_dict(self) -> Dict[str, str]:
        """Returns the labels as a dictionary.

        Returns:
            The labels as a dictionary.
        """
        if self.labels is None:
            return {}
        labels_dict = json.loads(base64.b64decode(self.labels).decode())
        return cast(Dict[str, str], labels_dict)

    def has_labels(self, labels: Dict[str, Optional[str]]) -> bool:
        """Checks if the connector has the given labels.

        Args:
            labels: The labels to check for.

        Returns:
            Whether the connector has the given labels.
        """
        return all(
            self.labels_dict.get(key, None) == value
            for key, value in labels.items()
            if value is not None
        ) and all(
            key in self.labels_dict
            for key, value in labels.items()
            if value is None
        )

    @classmethod
    def from_request(
        cls,
        connector_request: ServiceConnectorRequest,
        secret_id: Optional[UUID] = None,
    ) -> "ServiceConnectorSchema":
        """Create a `ServiceConnectorSchema` from a `ServiceConnectorRequest`.

        Args:
            connector_request: The `ServiceConnectorRequest` from which to
                create the schema.
            secret_id: The ID of the secret to use for this connector.

        Returns:
            The created `ServiceConnectorSchema`.
        """
        assert connector_request.user is not None, "User must be set."
        return cls(
            user_id=connector_request.user,
            name=connector_request.name,
            description=connector_request.description,
            connector_type=connector_request.type,
            auth_method=connector_request.auth_method,
            resource_types=base64.b64encode(
                json.dumps(connector_request.resource_types).encode("utf-8")
            ),
            resource_id=connector_request.resource_id,
            supports_instances=connector_request.supports_instances,
            configuration=base64.b64encode(
                json.dumps(connector_request.configuration).encode("utf-8")
            )
            if connector_request.configuration
            else None,
            secret_id=secret_id,
            expires_at=connector_request.expires_at,
            expires_skew_tolerance=connector_request.expires_skew_tolerance,
            expiration_seconds=connector_request.expiration_seconds,
            labels=base64.b64encode(
                json.dumps(connector_request.labels).encode("utf-8")
            )
            if connector_request.labels
            else None,
        )

    def update(
        self,
        connector_update: ServiceConnectorUpdate,
        secret_id: Optional[UUID] = None,
    ) -> "ServiceConnectorSchema":
        """Updates a `ServiceConnectorSchema` from a `ServiceConnectorUpdate`.

        Args:
            connector_update: The `ServiceConnectorUpdate` to update from.
            secret_id: The ID of the secret to use for this connector.

        Returns:
            The updated `ServiceConnectorSchema`.
        """
        for field, value in connector_update.model_dump(
            exclude_unset=False,
            exclude={"user", "secrets"},
        ).items():
            if value is None:
                if field == "resource_id":
                    # The resource ID field in the update is special: if set
                    # to None in the update, it triggers the existing resource
                    # ID to be cleared.
                    self.resource_id = None
                if field == "expiration_seconds":
                    # The expiration_seconds field in the update is special:
                    # if set to None in the update, it triggers the existing
                    # expiration_seconds to be cleared.
                    self.expiration_seconds = None
                continue
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
            elif field == "resource_types":
                self.resource_types = base64.b64encode(
                    json.dumps(connector_update.resource_types).encode("utf-8")
                )
            elif field == "labels":
                self.labels = (
                    base64.b64encode(
                        json.dumps(connector_update.labels).encode("utf-8")
                    )
                    if connector_update.labels
                    else None
                )
            else:
                setattr(self, field, value)
        self.secret_id = secret_id
        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "ServiceConnectorResponse":
        """Creates a `ServiceConnector` from a `ServiceConnectorSchema`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            A `ServiceConnectorModel`
        """
        body = ServiceConnectorResponseBody(
            user_id=self.user_id,
            created=self.created,
            updated=self.updated,
            description=self.description,
            connector_type=self.connector_type,
            auth_method=self.auth_method,
            resource_types=self.resource_types_list,
            resource_id=self.resource_id,
            supports_instances=self.supports_instances,
            expires_at=self.expires_at,
            expires_skew_tolerance=self.expires_skew_tolerance,
        )
        metadata = None
        if include_metadata:
            metadata = ServiceConnectorResponseMetadata(
                configuration=json.loads(
                    base64.b64decode(self.configuration).decode()
                )
                if self.configuration
                else {},
                secret_id=self.secret_id,
                expiration_seconds=self.expiration_seconds,
                labels=self.labels_dict,
            )
        resources = None
        if include_resources:
            resources = ServiceConnectorResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return ServiceConnectorResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
