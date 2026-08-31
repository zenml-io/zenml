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
"""Models for project-scoped webhooks."""

from datetime import datetime
from typing import ClassVar

from pydantic import Field, model_validator

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
from zenml.models.v2.base.filter import StringFilterOption
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


class WebhookRequest(ProjectScopedRequest):
    """Request model for creating a webhook."""

    name: str = Field(max_length=STR_FIELD_MAX_LENGTH)
    webhook_type: str = Field(
        min_length=1,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    active: bool = True
    secret: NonEmptyPlainSerializedSecretStr | None = Field(
        default=None,
        description="Optional signing secret. A secret is generated when "
        "omitted.",
    )


class WebhookUpdate(BaseUpdate):
    """Request model for updating a webhook."""

    name: str | None = Field(default=None, max_length=STR_FIELD_MAX_LENGTH)
    active: bool | None = None


class WebhookResponseBody(ProjectScopedResponseBody):
    """Response body for a webhook."""

    webhook_type: str = Field(
        min_length=1,
        max_length=STR_FIELD_MAX_LENGTH,
    )
    active: bool
    endpoint_url: str | None = None


class WebhookStats(BaseZenModel):
    """Intake statistics for a webhook."""

    received_count: int = 0
    accepted_count: int = 0
    auth_failed_count: int = 0
    invalid_payload_count: int = 0
    last_received_at: datetime | None = None
    last_accepted_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_summary: str | None = None


class WebhookResponseMetadata(ProjectScopedResponseMetadata):
    """Response metadata for a webhook."""

    stats: WebhookStats = Field(default_factory=WebhookStats)


class WebhookResponseResources(ProjectScopedResponseResources):
    """Resources associated with a webhook."""


class WebhookResponse(
    ProjectScopedResponse[
        WebhookResponseBody,
        WebhookResponseMetadata,
        WebhookResponseResources,
    ]
):
    """Response model for a webhook."""

    name: str = Field(max_length=STR_FIELD_MAX_LENGTH)

    @model_validator(mode="after")
    def _set_endpoint_url(self) -> "WebhookResponse":
        """Populate the externally reachable webhook intake URL."""
        if self.body is not None and self.body.endpoint_url is None:
            from zenml.webhooks.urls import get_webhook_intake_url

            self.body.endpoint_url = get_webhook_intake_url(
                webhook_type=self.body.webhook_type,
                webhook_id=self.id,
            )
        return self

    def get_hydrated_version(self) -> "WebhookResponse":
        """Return the hydrated webhook.

        Returns:
            The hydrated webhook.
        """
        from zenml.client import Client

        return Client().zen_store.get_webhook(self.id)

    @property
    def webhook_type(self) -> str:
        """Return the webhook provider type.

        Returns:
            The webhook provider type.
        """
        return self.get_body().webhook_type

    @property
    def active(self) -> bool:
        """Return whether the webhook accepts events.

        Returns:
            Whether the webhook accepts events.
        """
        return self.get_body().active

    @property
    def endpoint_url(self) -> str | None:
        """Return the provider-facing event endpoint URL.

        Returns:
            The absolute endpoint URL, if the server URL is configured.
        """
        return self.get_body().endpoint_url

    @property
    def stats(self) -> WebhookStats:
        """Return intake statistics for this webhook.

        Returns:
            Intake statistics for this webhook.
        """
        return self.get_metadata().stats


class WebhookFilter(ProjectScopedFilter):
    """Filter model for webhooks."""

    name: StringFilterOption = None
    webhook_type: StringFilterOption = None
    API_SINGLE_INPUT_PARAMS: ClassVar[list[str]] = [
        *ProjectScopedFilter.API_SINGLE_INPUT_PARAMS,
        "active",
    ]

    active: bool | None = None


class WebhookCreateResponse(BaseZenModel):
    """Creation result with a generated secret when applicable."""

    webhook: WebhookResponse
    secret: PlainSerializedSecretStr | None = None


class WebhookRotateSecretRequest(BaseZenModel):
    """Request model for rotating a webhook secret."""

    secret: NonEmptyPlainSerializedSecretStr | None = Field(
        default=None,
        description="Optional direct replacement secret.",
    )


class WebhookSecretResponse(BaseZenModel):
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
