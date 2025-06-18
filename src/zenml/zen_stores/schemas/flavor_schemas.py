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
from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship

from zenml.enums import StackComponentType
from zenml.models import (
    FlavorResponse,
    FlavorResponseBody,
    FlavorResponseMetadata,
    FlavorResponseResources,
    FlavorUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class FlavorSchema(NamedSchema, table=True):
    """SQL Model for flavors.

    Attributes:
        type: The type of the flavor.
        source: The source of the flavor.
        config_schema: The config schema of the flavor.
        integration: The integration associated with the flavor.
    """

    __tablename__ = "flavor"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "type",
            name="unique_flavor_name_and_type",
        ),
    )

    type: str
    source: str
    config_schema: str = Field(sa_column=Column(TEXT, nullable=False))
    integration: Optional[str] = Field(default="")
    connector_type: Optional[str]
    connector_resource_type: Optional[str]
    connector_resource_id_attr: Optional[str]

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
                    joinedload(jl_arg(FlavorSchema.user)),
                ]
            )

        return options

    def update(
        self,
        flavor_update: "FlavorUpdate",
    ) -> "FlavorSchema":
        """Update a `FlavorSchema` from a `FlavorUpdate`.

        Args:
            flavor_update: The `FlavorUpdate` from which to update the schema.

        Returns:
            The updated `FlavorSchema`.
        """
        for field, value in flavor_update.model_dump(
            exclude_unset=True, exclude={"user"}
        ).items():
            if field == "config_schema":
                setattr(self, field, json.dumps(value))
            elif field == "type":
                setattr(self, field, value.value)
            else:
                setattr(self, field, value)

        self.updated = utc_now()
        return self

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "FlavorResponse":
        """Converts a flavor schema to a flavor model.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The flavor model.
        """
        body = FlavorResponseBody(
            user_id=self.user_id,
            type=StackComponentType(self.type),
            integration=self.integration,
            source=self.source,
            logo_url=self.logo_url,
            is_custom=self.is_custom,
            created=self.created,
            updated=self.updated,
        )
        metadata = None
        if include_metadata:
            metadata = FlavorResponseMetadata(
                config_schema=json.loads(self.config_schema),
                connector_type=self.connector_type,
                connector_resource_type=self.connector_resource_type,
                connector_resource_id_attr=self.connector_resource_id_attr,
                docs_url=self.docs_url,
                sdk_docs_url=self.sdk_docs_url,
            )
        resources = None
        if include_resources:
            resources = FlavorResponseResources(
                user=self.user.to_model() if self.user else None,
            )
        return FlavorResponse(
            id=self.id,
            name=self.name,
            body=body,
            metadata=metadata,
            resources=resources,
        )
