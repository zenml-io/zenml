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
"""SQLModel implementation of server settings tables."""

import json
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import TEXT, Column
from sqlmodel import Field

from zenml.models import (
    ServerSettingsResponse,
    ServerSettingsResponseBody,
    ServerSettingsResponseMetadata,
    ServerSettingsResponseResources,
    ServerSettingsUpdate,
)
from zenml.zen_stores.schemas.base_schemas import BaseSchema

if TYPE_CHECKING:
    pass


class ServerSettingsSchema(BaseSchema, table=True):
    """SQL Model for settings."""

    __tablename__ = "server_settings"

    onboarding_state: Optional[str] = Field(
        default=None, sa_column=Column(TEXT, nullable=True)
    )

    def update(
        self, server_settings_update: ServerSettingsUpdate
    ) -> "ServerSettingsSchema":
        """Update a `ServerSettingsSchema` from a `ServerSettingsUpdate`.

        Args:
            server_settings_update: The `ServerSettingsUpdate` from which
                to update the schema.

        Returns:
            The updated `ServerSettingsSchema`.
        """
        if server_settings_update.onboarding_state is not None:
            self.onboarding_state = json.dumps(
                server_settings_update.onboarding_state
            )

        return self

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
            The created `ServerSettingsResponse`.
        """
        body = ServerSettingsResponseBody(
            onboarding_state=json.loads(self.onboarding_state)
            if self.onboarding_state
            else {},
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
