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
"""Models representing server settings."""

from typing import (
    Any,
    Dict,
    Optional,
)

from pydantic import BaseModel, Field

from zenml.models.v2.base.base import (
    BaseResponse,
    BaseResponseBody,
    BaseResponseMetadata,
    BaseResponseResources,
    BaseZenModel,
)

# ------------------ Base Model ------------------


class ServerSettingsBase(BaseModel):
    """Base model for server settings."""


# ------------------ Request Model ------------------


# ------------------ Update Model ------------------


class ServerSettingsUpdate(ServerSettingsBase, BaseZenModel):
    onboarding_state: Optional[Dict[str, Any]] = Field(
        default=None,
        title="The onboarding state of the server.",
    )


# ------------------ Response Model ------------------


class ServerSettingsResponseBody(BaseResponseBody):
    """Response body for server settings."""

    onboarding_state: Dict[str, Any] = Field(
        default={},
        title="The onboarding state of the server.",
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
    def get_hydrated_version(self) -> "ServerSettingsResponse":
        """Get the hydrated version of the settings.

        Returns:
            an instance of the same entity with the metadata field attached.
        """
        from zenml.client import Client

        return Client().zen_store.get_server_settings(hydrate=True)

    # Body and metadata properties

    @property
    def onboarding_state(self) -> Dict[str, Any]:
        """The `onboarding_state` property.

        Returns:
            the value of the property.
        """
        return self.get_body().onboarding_state


# ------------------ Filter Model ------------------

# Server Settings can't be filtered
