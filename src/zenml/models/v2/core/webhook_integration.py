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
"""Models for project-scoped webhook integrations."""

from datetime import datetime
from typing import ClassVar

from pydantic import Field, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import WebhookType
from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
from zenml.models.v2.base.filter import EnumFilterOption, StringFilterOption
from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
)
from zenml.utils.secret_utils import (
    NonEmptyPlainSerializedSecretStr,
    PlainSerializedSecretStr,
)


class WebhookIntegrationRequest(ProjectScopedRequest):
    """Request model for creating a webhook integration."""

    name: str = Field(max_length=STR_FIELD_MAX_LENGTH)
    webhook_type: WebhookType
    active: bool = True
    secret: NonEmptyPlainSerializedSecretStr | None = Field(
        default=None,
        description="Optional direct signing secret or ZenML secret "
        "reference. A direct secret is generated when omitted.",
    )


class WebhookIntegrationUpdate(BaseUpdate):
    """Request model for updating a webhook integration."""

    name: str | None = Field(default=None, max_length=STR_FIELD_MAX_LENGTH)
    active: bool | None = None
    secret: NonEmptyPlainSerializedSecretStr | None = Field(
        default=None,
        description="A direct signing secret or ZenML secret reference.",
    )


class WebhookIntegrationResponseBody(ProjectScopedResponseBody):
    """Response body for a webhook integration."""

    webhook_type: WebhookType
    active: bool
    endpoint_path: str


class WebhookIntegrationStats(BaseZenModel):
    """Intake statistics for a webhook integration."""

    received_count: int = 0
    accepted_count: int = 0
    auth_failed_count: int = 0
    invalid_payload_count: int = 0
    last_received_at: datetime | None = None
    last_accepted_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_summary: str | None = None


class WebhookIntegrationResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for a webhook integration."""

    stats: WebhookIntegrationStats = Field(
        default_factory=WebhookIntegrationStats
    )


class WebhookIntegrationResponseResources(ProjectScopedResponseResources):
    """Resources associated with a webhook integration."""


class WebhookIntegrationResponse(
    ProjectScopedResponse[
        WebhookIntegrationResponseBody,
        WebhookIntegrationResponseMetadata,
        WebhookIntegrationResponseResources,
    ]
):
    """Response model for a webhook integration."""

    name: str = Field(max_length=STR_FIELD_MAX_LENGTH)

    def get_hydrated_version(self) -> "WebhookIntegrationResponse":
        """Return the hydrated webhook integration.

        Returns:
            The hydrated webhook integration.
        """
        from zenml.client import Client

        return Client().zen_store.get_webhook_integration(self.id)

    @property
    def webhook_type(self) -> WebhookType:
        """Return the webhook provider type.

        Returns:
            The webhook provider type.
        """
        return self.get_body().webhook_type

    @property
    def active(self) -> bool:
        """Return whether the integration accepts events.

        Returns:
            Whether the integration accepts events.
        """
        return self.get_body().active

    @property
    def endpoint_path(self) -> str:
        """Return the provider-facing event endpoint path.

        Returns:
            The provider-facing event endpoint path.
        """
        return self.get_body().endpoint_path

    @property
    def stats(self) -> WebhookIntegrationStats:
        """Return intake statistics for this webhook integration.

        Returns:
            Intake statistics for this webhook integration.
        """
        return self.get_metadata().stats


class WebhookIntegrationFilter(ProjectScopedFilter):
    """Filter model for webhook integrations."""

    name: StringFilterOption = None
    webhook_type: EnumFilterOption[WebhookType] = None
    API_SINGLE_INPUT_PARAMS: ClassVar[list[str]] = [
        *ProjectScopedFilter.API_SINGLE_INPUT_PARAMS,
        "active",
    ]

    active: bool | None = None


class WebhookIntegrationCreateResponse(BaseZenModel):
    """Creation result with a generated secret when applicable."""

    webhook: WebhookIntegrationResponse
    secret: PlainSerializedSecretStr | None = None


class WebhookIntegrationRotateSecretRequest(BaseZenModel):
    """Request model for rotating a webhook integration secret."""

    secret: NonEmptyPlainSerializedSecretStr | None = Field(
        default=None,
        description="Optional direct replacement secret. Secret references "
        "must be configured through an integration update.",
    )


class WebhookIntegrationSecretResponse(BaseZenModel):
    """One-time response containing a newly active signing secret."""

    secret: PlainSerializedSecretStr


class WebhookEventStatsUpdate(BaseZenModel):
    """Atomic intake statistics update."""

    accepted: bool = False
    auth_failed: bool = False
    invalid_payload: bool = False
    error_summary: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def validate_single_outcome(self) -> "WebhookEventStatsUpdate":
        """Validate that exactly one terminal intake outcome is selected.

        Returns:
            The validated statistics update.

        Raises:
            ValueError: If the update does not contain exactly one outcome or
                an accepted outcome contains an error.
        """
        outcomes = (self.accepted, self.auth_failed, self.invalid_payload)
        if sum(outcomes) != 1:
            raise ValueError("Exactly one webhook intake outcome is required.")
        if self.accepted and self.error_summary is not None:
            raise ValueError(
                "Accepted webhook events cannot include an error."
            )
        return self
