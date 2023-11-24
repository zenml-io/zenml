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
"""SQL Model Implementations for Flavors."""
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import TEXT, Column
from sqlmodel import Field, Relationship

from zenml.enums import StackComponentType
from zenml.models import (
    FlavorResponse,
    FlavorResponseBody,
    FlavorResponseMetadata,
    FlavorUpdate,
)
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.workspace_schemas import WorkspaceSchema


class FlavorSchema(NamedSchema, table=True):
    """SQL Model for flavors.

    Attributes:
        type: The type of the flavor.
        source: The source of the flavor.
        config_schema: The config schema of the flavor.
        integration: The integration associated with the flavor.
    """

    __tablename__ = "flavor"

    type: StackComponentType
    source: str
    config_schema: str = Field(sa_column=Column(TEXT, nullable=False))
    integration: Optional[str] = Field(default="")
    connector_type: Optional[str]
    connector_resource_type: Optional[str]
    connector_resource_id_attr: Optional[str]

    workspace_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=WorkspaceSchema.__tablename__,
        source_column="workspace_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=True,
    )
    workspace: Optional["WorkspaceSchema"] = Relationship(
        back_populates="flavors"
    )

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: Optional["UserSchema"] = Relationship(back_populates="flavors")

    logo_url: Optional[str] = Field()

    docs_url: Optional[str] = Field()

    sdk_docs_url: Optional[str] = Field()

    is_custom: bool = Field(default=True)

    def update(self, flavor_update: "FlavorUpdate") -> "FlavorSchema":
        """Update a `FlavorSchema` from a `FlavorUpdate`.

        Args:
            flavor_update: The `FlavorUpdate` from which to update the schema.

        Returns:
            The updated `FlavorSchema`.
        """
        for field, value in flavor_update.dict(
            exclude_unset=True, exclude={"workspace", "user"}
        ).items():
            if field == "config_schema":
                setattr(self, field, json.dumps(value))
            else:
                setattr(self, field, value)

        self.updated = datetime.utcnow()
        return self

    def to_model(self, hydrate: bool = False) -> "FlavorResponse":
        """Converts a flavor schema to a flavor model.

        Args:
            hydrate: bool to decide whether to return a hydrated version of the
                model.

        Returns:
            The flavor model.
        """
        body = FlavorResponseBody(
            user=self.user.to_model() if self.user else None,
            type=self.type,
            integration=self.integration,
            logo_url=self.logo_url,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if hydrate:
            metadata = FlavorResponseMetadata(
                workspace=self.workspace.to_model()
                if self.workspace
                else None,
                config_schema=json.loads(self.config_schema),
                connector_type=self.connector_type,
                connector_resource_type=self.connector_resource_type,
                connector_resource_id_attr=self.connector_resource_id_attr,
                source=self.source,
                docs_url=self.docs_url,
                sdk_docs_url=self.sdk_docs_url,
                is_custom=self.is_custom,
            )
        return FlavorResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
        )
