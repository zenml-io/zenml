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

from typing import (
    Any,
    Dict,
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
# ------------------ Request Model ------------------


# ------------------ Update Model ------------------


class ServerSettingsUpdate(BaseZenModel):
    """Model for updating server settings."""

    name: Optional[str] = Field(default=None, title="The name of the server.")
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
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The metadata associated with the server.",
    )


# ------------------ Response Model ------------------


class ServerSettingsResponseBody(BaseResponseBody):
    """Response body for server settings."""

    server_id: UUID = Field(
        title="The unique server id.",
    )
    name: str = Field(title="The name of the server.")
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


class ServerSettingsResponseMetadata(BaseResponseMetadata):
    """Response metadata for server settings."""

    metadata: Dict[str, Any] = Field(
        default={},
        title="The metadata associated with the server.",
    )


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
    def name(self) -> str:
        """The `name` property.

        Returns:
            the value of the property.
        """
        return self.get_body().name

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
    def server_metadata(self) -> Dict[str, Any]:
        """The `server_metadata` property.

        Returns:
            the value of the property.
        """
        return self.get_metadata().metadata


# ------------------ Filter Model ------------------

# Server Settings can't be filtered
