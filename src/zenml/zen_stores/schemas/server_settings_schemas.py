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
"""SQLModel implementation for the server settings table."""

import json
from datetime import datetime
from typing import Any, Optional, Set
from uuid import UUID

from sqlmodel import Field, SQLModel

from zenml.models import (
    ServerSettingsResponse,
    ServerSettingsResponseBody,
    ServerSettingsResponseMetadata,
    ServerSettingsResponseResources,
    ServerSettingsUpdate,
)


class ServerSettingsSchema(SQLModel, table=True):
    """SQL Model for the server settings."""

    __tablename__ = "server_settings"

    id: UUID = Field(primary_key=True)
    server_name: str
    logo_url: Optional[str] = Field(nullable=True)
    active: bool = Field(default=False)
    enable_analytics: bool = Field(default=False)
    display_announcements: Optional[bool] = Field(nullable=True)
    display_updates: Optional[bool] = Field(nullable=True)
    onboarding_state: Optional[str] = Field(nullable=True)
    updated: datetime = Field(default_factory=datetime.utcnow)

    def update(
        self, settings_update: ServerSettingsUpdate
    ) -> "ServerSettingsSchema":
        """Update a `ServerSettingsSchema` from a `ServerSettingsUpdate`.

        Args:
            settings_update: The `ServerSettingsUpdate` from which
                to update the schema.

        Returns:
            The updated `ServerSettingsSchema`.
        """
        for field, value in settings_update.model_dump(
            exclude_unset=True
        ).items():
            if hasattr(self, field):
                setattr(self, field, value)

        self.updated = datetime.utcnow()

        return self

    def update_onboarding_state(
        self, completed_steps: Set[str]
    ) -> "ServerSettingsSchema":
        onboarding_state = set(
            json.loads(self.onboarding_state) if self.onboarding_state else []
        )
        onboarding_state.union(completed_steps)
        self.onboarding_state = json.dumps(onboarding_state)
        self.updated = datetime.utcnow()

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> ServerSettingsResponse:
        """Convert an `ServerSettingsSchema` to an `ServerSettingsResponse`.

        Args:
            include_metadata: Whether the metadata will be filled.
            include_resources: Whether the resources will be filled.
            **kwargs: Keyword arguments to allow schema specific logic


        Returns:
            The created `SettingsResponse`.
        """
        body = ServerSettingsResponseBody(
            server_id=self.id,
            server_name=self.server_name,
            logo_url=self.logo_url,
            enable_analytics=self.enable_analytics,
            display_announcements=self.display_announcements,
            display_updates=self.display_updates,
            active=self.active,
            updated=self.updated,
        )

        metadata = None
        resources = None

        if include_metadata:
            metadata = ServerSettingsResponseMetadata()

        if include_resources:
            resources = ServerSettingsResponseResources()

        return ServerSettingsResponse(
            body=body, metadata=metadata, resources=resources
        )
