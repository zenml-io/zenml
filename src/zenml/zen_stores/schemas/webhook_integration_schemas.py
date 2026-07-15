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
"""SQL schema for webhook integrations."""

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
from zenml.zen_stores.schemas.schema_utils import (
    build_foreign_key_field,
    build_index,
)
from zenml.zen_stores.schemas.secret_schemas import SecretSchema
from zenml.zen_stores.schemas.user_schemas import UserSchema


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
        ondelete="CASCADE",
        nullable=False,
    )
    webhook_type: str
    active: bool = Field(default=True)
    stats: str = Field(
        default=WebhookIntegrationStats().model_dump_json(),
        sa_column=Column(TEXT, nullable=False),
    )

    @property
    def parsed_stats(self) -> WebhookIntegrationStats:
        """Parse persisted intake statistics.

        Returns:
            The typed intake statistics.
        """
        return WebhookIntegrationStats.model_validate_json(self.stats or "{}")

    def set_stats(self, stats: WebhookIntegrationStats) -> None:
        """Persist typed intake statistics.

        Args:
            stats: The typed intake statistics to persist.
        """
        self.stats = stats.model_dump_json()

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
                stats=self.parsed_stats
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
