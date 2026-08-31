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
"""Unit tests for webhook schemas and request models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from zenml.models import (
    WebhookEventStatsUpdate,
    WebhookRequest,
    WebhookRotateSecretRequest,
    WebhookStats,
    WebhookUpdate,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.rbac.utils import get_resource_type_for_model
from zenml.zen_stores.schemas.webhook_schemas import (
    WebhookSchema,
    WebhookStatsSchema,
)


def _webhook_schema() -> WebhookSchema:
    schema = WebhookSchema(
        id=uuid4(),
        name="github-intake",
        project_id=uuid4(),
        user_id=uuid4(),
        secret_id=uuid4(),
        webhook_type="github",
        active=True,
    )
    schema.stats = WebhookStatsSchema(
        webhook_id=schema.id,
        **WebhookStats(
            received_count=3,
            accepted_count=1,
            auth_failed_count=1,
            invalid_payload_count=1,
            last_received_at=datetime(2026, 7, 9, 8, 0, 0),
            last_accepted_at=datetime(2026, 7, 9, 8, 1, 0),
            last_error_at=datetime(2026, 7, 9, 8, 2, 0),
            last_error_summary="Invalid webhook signature.",
        ).model_dump(),
    )
    return schema


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"accepted": True, "auth_failed": True},
        {"accepted": True, "error_summary": "unexpected"},
    ],
)
def test_webhook_event_stats_update_rejects_invalid_outcome(
    kwargs: dict[str, object],
) -> None:
    """Webhook stats updates reject missing or conflicting outcomes."""
    with pytest.raises(ValidationError):
        WebhookEventStatsUpdate(**kwargs)


@pytest.mark.parametrize(
    ("model_class", "kwargs"),
    [
        (
            WebhookRequest,
            {
                "name": "github-intake",
                "project": uuid4(),
                "webhook_type": "github",
            },
        ),
        (WebhookRotateSecretRequest, {}),
    ],
    ids=["create", "rotate"],
)
@pytest.mark.parametrize("secret", ["", "   "])
def test_webhook_models_reject_empty_secret(
    model_class: type[BaseModel],
    kwargs: dict[str, object],
    secret: str,
) -> None:
    """Webhook models reject empty signing secrets."""
    with pytest.raises(ValidationError):
        model_class(secret=secret, **kwargs)


def test_webhook_requests_allow_missing_secret() -> None:
    """Webhook requests allow missing secrets for generation."""
    webhook_request = WebhookRequest(
        name="github-intake",
        project=uuid4(),
        webhook_type="github",
    )
    secret_request = WebhookRotateSecretRequest()

    assert webhook_request.secret is None
    assert secret_request.secret is None


def test_webhook_request_accepts_extensible_provider_type() -> None:
    """Webhook provider names are not constrained by a core enum."""
    request = WebhookRequest(
        name="third-party-intake",
        project=uuid4(),
        webhook_type="third-party",
    )

    assert request.webhook_type == "third-party"


def test_webhook_uses_cloud_compatible_rbac_resource_name() -> None:
    """Webhook RBAC checks use the existing Cloud API resource name."""
    request = WebhookRequest(
        name="github-intake",
        project=uuid4(),
        webhook_type="github",
    )

    resource_type = get_resource_type_for_model(request)

    assert resource_type is ResourceType.WEBHOOK_INTEGRATION
    assert resource_type.value == "webhook_integration"


def test_webhook_update_excludes_secret() -> None:
    """Webhook updates are limited to database fields."""
    assert "secret" not in WebhookUpdate.model_fields


def test_webhook_schema_to_model_includes_body_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Webhook schemas include body and stats metadata."""
    schema = _webhook_schema()
    endpoint_url = (
        f"https://zenml.example.com/api/v1/webhooks/github/{schema.id}/events"
    )
    monkeypatch.setattr(
        "zenml.webhooks.urls.get_webhook_intake_url",
        lambda **_: endpoint_url,
    )

    response = schema.to_model(include_metadata=True)

    assert response.id == schema.id
    assert response.name == "github-intake"
    assert response.webhook_type == "github"
    assert response.active is True
    assert response.endpoint_url == endpoint_url
    assert response.stats.received_count == 3
    assert response.stats.accepted_count == 1
    assert response.stats.auth_failed_count == 1
    assert response.stats.invalid_payload_count == 1
    assert response.stats.last_received_at == datetime(2026, 7, 9, 8, 0, 0)
    assert response.stats.last_accepted_at == datetime(2026, 7, 9, 8, 1, 0)
    assert response.stats.last_error_at == datetime(2026, 7, 9, 8, 2, 0)
    assert response.stats.last_error_summary == "Invalid webhook signature."


def test_webhook_stats_schema_defaults_missing_stats() -> None:
    """Webhook stats schemas default missing fields."""
    schema = _webhook_schema()
    schema.stats = WebhookStatsSchema(webhook_id=schema.id, received_count=3)

    response = schema.to_model(include_metadata=True)

    assert response.stats.received_count == 3
    assert response.stats.accepted_count == 0
    assert response.stats.auth_failed_count == 0
    assert response.stats.invalid_payload_count == 0
    assert response.stats.last_received_at is None


def test_webhook_schema_to_model_can_include_empty_resources() -> None:
    """Webhook schemas can include empty resources."""
    schema = _webhook_schema()
    schema.user = None

    response = schema.to_model(include_resources=True)

    assert response.get_resources().user is None
