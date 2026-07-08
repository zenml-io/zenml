# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""SQL schema for webhook integrations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import TEXT, Column, UniqueConstraint
from sqlmodel import Field, Relationship

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
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field
from zenml.zen_stores.schemas.secret_schemas import SecretSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema


class WebhookIntegrationSchema(NamedSchema, table=True):
    """SQL schema for a project-scoped webhook integration."""

    __tablename__ = "webhook_integration"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "project_id",
            name="unique_webhook_integration_name_in_project",
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
        ondelete="CASCADE",
        nullable=False,
    )
    webhook_type: str = Field(index=True)
    active: bool = Field(default=True, index=True)
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
                stats=WebhookIntegrationStats(
                    received_count=self.received_count,
                    accepted_count=self.accepted_count,
                    auth_failed_count=self.auth_failed_count,
                    invalid_payload_count=self.invalid_payload_count,
                    last_received_at=self.last_received_at,
                    last_accepted_at=self.last_accepted_at,
                    last_error_at=self.last_error_at,
                    last_error_summary=self.last_error_summary,
                )
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
