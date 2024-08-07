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
"""Models representing server settings stored in the database."""

from datetime import datetime
from typing import (
    Optional,
)
from uuid import UUID

from pydantic import Field

from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseZenModel,
)

# ------------------ Base Model ------------------

# ------------------ Update Model ------------------


class ServerSettingsUpdate(BaseZenModel):
    """Model for updating server settings."""

    server_name: Optional[str] = Field(
        default=None, title="The name of the server."
    )
    logo_url: Optional[str] = Field(
        default=None, title="The logo URL of the server."
    )
    enable_analytics: Optional[bool] = Field(
        default=None,
        title="Whether to enable analytics for the server.",
    )
    display_announcements: Optional[bool] = Field(
        default=None,
        title="Whether to display announcements about ZenML in the dashboard.",
    )
    display_updates: Optional[bool] = Field(
        default=None,
        title="Whether to display notifications about ZenML updates in the dashboard.",
    )


# ------------------ Response Model ------------------


class ServerSettingsResponseBody(BaseResponseBody):
    """Response body for server settings."""

    server_id: UUID = Field(
        title="The unique server id.",
    )
    server_name: str = Field(title="The name of the server.")
    logo_url: Optional[str] = Field(
        default=None, title="The logo URL of the server."
    )
    active: bool = Field(
        title="Whether the server has been activated or not.",
    )
    enable_analytics: bool = Field(
        title="Whether analytics are enabled for the server.",
    )
    display_announcements: Optional[bool] = Field(
        title="Whether to display announcements about ZenML in the dashboard.",
    )
    display_updates: Optional[bool] = Field(
        title="Whether to display notifications about ZenML updates in the dashboard.",
    )
    last_user_activity: datetime = Field(
        title="The timestamp when the last user activity was detected.",
    )
    updated: datetime = Field(
        title="The timestamp when this resource was last updated."
    )


class ServerSettingsResponseMetadata(BaseResponseMetadata):
    """Response metadata for server settings."""


class ServerSettingsResponseResources(BaseResponseResources):
    """Response resources for server settings."""


class ServerSettingsResponse(
    BaseResponse[
        ServerSettingsResponseBody,
        ServerSettingsResponseMetadata,
        ServerSettingsResponseResources,
    ]
):
    """Response model for server settings."""

    def get_hydrated_version(self) -> "ServerSettingsResponse":
        """Get the hydrated version of the server settings.

        Returns:
            An instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_server_settings(hydrate=True)

    # Body and metadata properties

    @property
    def server_id(self) -> UUID:
        """The `server_id` property.

        Returns:
            the value of the property.
        """
        return self.get_body().server_id

    @property
    def server_name(self) -> str:
        """The `server_name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().server_name

    @property
    def logo_url(self) -> Optional[str]:
        """The `logo_url` property.

        Returns:
            the value of the property.
        """
        return self.get_body().logo_url

    @property
    def enable_analytics(self) -> bool:
        """The `enable_analytics` property.

        Returns:
            the value of the property.
        """
        return self.get_body().enable_analytics

    @property
    def display_announcements(self) -> Optional[bool]:
        """The `display_announcements` property.

        Returns:
            the value of the property.
        """
        return self.get_body().display_announcements

    @property
    def display_updates(self) -> Optional[bool]:
        """The `display_updates` property.

        Returns:
            the value of the property.
        """
        return self.get_body().display_updates

    @property
    def active(self) -> bool:
        """The `active` property.

        Returns:
            the value of the property.
        """
        return self.get_body().active

    @property
    def last_user_activity(self) -> datetime:
        """The `last_user_activity` property.

        Returns:
            the value of the property.
        """
        return self.get_body().last_user_activity

    @property
    def updated(self) -> datetime:
        """The `updated` property.

        Returns:
            the value of the property.
        """
        return self.get_body().updated


# ------------------ Filter Model ------------------

# Server Settings can't be filtered

# ------------------ Request Model ------------------


class ServerActivationRequest(ServerSettingsUpdate):
    """Model for activating the server."""

    admin_username: Optional[str] = Field(
        default=None,
        title="The username of the default admin account to create. Leave "
        "empty to skip creating the default admin account.",
    )

    admin_password: Optional[str] = Field(
        default=None,
        title="The password of the default admin account to create. Leave "
        "empty to skip creating the default admin account.",
    )
