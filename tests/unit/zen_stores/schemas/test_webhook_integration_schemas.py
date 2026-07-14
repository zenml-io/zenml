"""Unit tests for webhook integration schemas and request models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import WebhookType
from zenml.models import (
    WebhookEventStatsUpdate,
    WebhookIntegrationRequest,
    WebhookIntegrationSecretRequest,
    WebhookIntegrationStats,
    WebhookIntegrationUpdate,
)
from zenml.zen_stores.schemas.webhook_integration_schemas import (
    WebhookIntegrationSchema,
)


def _webhook_integration_schema() -> WebhookIntegrationSchema:
    return WebhookIntegrationSchema(
        id=uuid4(),
        name="github-intake",
        project_id=uuid4(),
        user_id=uuid4(),
        secret_id=uuid4(),
        webhook_type=WebhookType.GITHUB.value,
        active=True,
        stats=WebhookIntegrationStats(
            received_count=3,
            accepted_count=1,
            auth_failed_count=1,
            invalid_payload_count=1,
            last_received_at=datetime(2026, 7, 9, 8, 0, 0),
            last_accepted_at=datetime(2026, 7, 9, 8, 1, 0),
            last_error_at=datetime(2026, 7, 9, 8, 2, 0),
            last_error_summary="Invalid webhook signature.",
        ).model_dump_json(),
    )


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
            WebhookIntegrationRequest,
            {
                "name": "github-intake",
                "project": uuid4(),
                "webhook_type": WebhookType.GITHUB,
            },
        ),
        (WebhookIntegrationSecretRequest, {}),
        (WebhookIntegrationUpdate, {}),
    ],
    ids=["create", "rotate", "update"],
)
@pytest.mark.parametrize("secret", ["", "   "])
def test_webhook_integration_models_reject_empty_secret(
    model_class: type[BaseModel],
    kwargs: dict[str, object],
    secret: str,
) -> None:
    """Webhook integration models reject empty signing secrets."""
    with pytest.raises(ValidationError):
        model_class(secret=secret, **kwargs)


def test_webhook_integration_requests_allow_missing_secret() -> None:
    """Webhook integration requests allow missing secrets for generation."""
    integration_request = WebhookIntegrationRequest(
        name="github-intake",
        project=uuid4(),
        webhook_type=WebhookType.GITHUB,
    )
    secret_request = WebhookIntegrationSecretRequest()

    assert integration_request.secret is None
    assert secret_request.secret is None


def test_webhook_integration_update_accepts_secret_reference() -> None:
    """Webhook integration updates accept a secret reference."""
    update = WebhookIntegrationUpdate(secret="{{webhook.secret}}")

    assert update.secret is not None
    assert update.secret.get_secret_value() == "{{webhook.secret}}"


def test_webhook_integration_schema_to_model_includes_body_and_metadata() -> (
    None
):
    """Webhook integration schemas include body and stats metadata."""
    schema = _webhook_integration_schema()

    response = schema.to_model(include_metadata=True)

    assert response.id == schema.id
    assert response.name == "github-intake"
    assert response.webhook_type == WebhookType.GITHUB
    assert response.active is True
    assert response.endpoint_path == (
        f"{API}{VERSION_1}{WEBHOOKS}/{WebhookType.GITHUB.value}/"
        f"{schema.id}/events"
    )
    assert response.stats.received_count == 3
    assert response.stats.accepted_count == 1
    assert response.stats.auth_failed_count == 1
    assert response.stats.invalid_payload_count == 1
    assert response.stats.last_received_at == datetime(2026, 7, 9, 8, 0, 0)
    assert response.stats.last_accepted_at == datetime(2026, 7, 9, 8, 1, 0)
    assert response.stats.last_error_at == datetime(2026, 7, 9, 8, 2, 0)
    assert response.stats.last_error_summary == "Invalid webhook signature."


def test_webhook_integration_schema_to_model_defaults_missing_stats() -> None:
    """Webhook integration schemas default missing stats fields."""
    schema = _webhook_integration_schema()
    schema.stats = '{"received_count": 3, "future_count": 7}'

    response = schema.to_model(include_metadata=True)

    assert response.stats.received_count == 3
    assert response.stats.accepted_count == 0
    assert response.stats.auth_failed_count == 0
    assert response.stats.invalid_payload_count == 0
    assert response.stats.last_received_at is None


def test_webhook_integration_schema_can_update_serialized_stats() -> None:
    """Webhook integration schemas serialize typed stats."""
    schema = _webhook_integration_schema()
    stats = WebhookIntegrationStats(received_count=5)

    schema.set_stats(stats)

    assert schema.parsed_stats.received_count == 5
    assert schema.parsed_stats.accepted_count == 0


def test_webhook_integration_schema_to_model_can_include_empty_resources() -> (
    None
):
    """Webhook integration schemas can include empty resources."""
    schema = _webhook_integration_schema()
    schema.user = None

    response = schema.to_model(include_resources=True)

    assert response.get_resources().user is None
