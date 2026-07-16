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
"""SQL schemas for webhook integrations."""

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import Field, Relationship, SQLModel

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.models import (
    WebhookIntegrationRequest,
    WebhookIntegrationResponse,
    WebhookIntegrationResponseBody,
    WebhookIntegrationResponseMetadata,
    WebhookIntegrationResponseResources,
    WebhookIntegrationStats,
    WebhookIntegrationUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas.base_schemas import NamedSchema
from zenml.zen_stores.schemas.project_schemas import ProjectSchema
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.secret_schemas import SecretSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema
from zenml.zen_stores.schemas.utils import jl_arg


class WebhookIntegrationSchema(NamedSchema, table=True):
    """SQL schema for a project-scoped webhook integration."""

    __tablename__ = "webhook_integration"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "name",
            name="unique_webhook_integration_name_in_project",
        ),
        build_index(
            table_name=__tablename__,
            column_names=["webhook_type"],
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
        back_populates="webhook_integrations"
    )
    user_id: UUID | None = build_foreign_key_field(
        source=__tablename__,
        target=UserSchema.__tablename__,
        source_column="user_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    user: UserSchema | None = Relationship()
    secret_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=SecretSchema.__tablename__,
        source_column="secret_id",
        target_column="id",
        ondelete="RESTRICT",
        nullable=False,
    )
    webhook_type: str
    active: bool = Field(default=True)
    stats: "WebhookIntegrationStatsSchema" = Relationship(
        back_populates="webhook",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "single_parent": True,
            "uselist": False,
        },
    )

    @classmethod
    def get_query_options(
        cls,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> Sequence[ExecutableOption]:
        """Get query options for webhook integrations.

        Args:
            include_metadata: Whether statistics will be included.
            include_resources: Whether related resources will be included.
            **kwargs: Additional query option arguments.

        Returns:
            Query options for the requested response shape.
        """
        options: list[ExecutableOption] = []
        if include_metadata:
            options.append(selectinload(jl_arg(cls.stats)))
        if include_resources:
            options.append(joinedload(jl_arg(cls.user)))
        return options

    @classmethod
    def from_request(
        cls, request: WebhookIntegrationRequest, secret_id: UUID
    ) -> "WebhookIntegrationSchema":
        """Create a schema from a request.

        Args:
            request: The webhook integration creation request.
            secret_id: The internal signing secret ID.

        Returns:
            The created webhook integration schema.
        """
        return cls(
            name=request.name,
            project_id=request.project,
            user_id=request.user,
            webhook_type=request.webhook_type.value,
            active=request.active,
            secret_id=secret_id,
        )

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> WebhookIntegrationResponse:
        """Convert the schema to a response model.

        Args:
            include_metadata: Whether to include intake statistics.
            include_resources: Whether to include associated resources.
            **kwargs: Additional conversion options.

        Returns:
            The webhook integration response.
        """
        metadata = None
        if include_metadata:
            metadata = WebhookIntegrationResponseMetadata(
                stats=self.stats.to_model()
            )

        resources = None
        if include_resources:
            resources = WebhookIntegrationResponseResources(
                user=self.user.to_model() if self.user else None,
            )

        return WebhookIntegrationResponse(
            id=self.id,
            name=self.name,
            body=WebhookIntegrationResponseBody(
                user_id=self.user_id,
                project_id=self.project_id,
                created=self.created,
                updated=self.updated,
                webhook_type=self.webhook_type,
                active=self.active,
                endpoint_path=(
                    f"{API}{VERSION_1}{WEBHOOKS}/{self.webhook_type}/"
                    f"{self.id}/events"
                ),
            ),
            metadata=metadata,
            resources=resources,
        )

    def update(
        self, update: WebhookIntegrationUpdate
    ) -> "WebhookIntegrationSchema":
        """Apply a webhook integration update.

        Args:
            update: The webhook integration update.

        Returns:
            The updated webhook integration schema.
        """
        if update.name is not None:
            self.name = update.name
        if update.active is not None:
            self.active = update.active
        self.updated = utc_now()
        return self


class WebhookIntegrationStatsSchema(SQLModel, table=True):
    """SQL schema for webhook intake statistics."""

    __tablename__ = "webhook_integration_stats"

    webhook_id: UUID = build_foreign_key_field(
        source=__tablename__,
        target=WebhookIntegrationSchema.__tablename__,
        source_column="webhook_id",
        target_column="id",
        ondelete="CASCADE",
        nullable=False,
        primary_key=True,
    )
    received_count: int = 0
    accepted_count: int = 0
    auth_failed_count: int = 0
    invalid_payload_count: int = 0
    last_received_at: datetime | None = None
    last_accepted_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_summary: str | None = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )

    webhook: WebhookIntegrationSchema = Relationship(back_populates="stats")

    def to_model(self) -> WebhookIntegrationStats:
        """Convert persisted statistics to their domain model.

        Returns:
            The webhook intake statistics.
        """
        return WebhookIntegrationStats.model_validate(
            self, from_attributes=True
        )
