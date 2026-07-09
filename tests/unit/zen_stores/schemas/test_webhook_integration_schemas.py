from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import WebhookType
from zenml.models import WebhookEventStatsUpdate
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
        received_count=3,
        accepted_count=1,
        auth_failed_count=1,
        invalid_payload_count=1,
        last_received_at=datetime(2026, 7, 9, 8, 0, 0),
        last_accepted_at=datetime(2026, 7, 9, 8, 1, 0),
        last_error_at=datetime(2026, 7, 9, 8, 2, 0),
        last_error_summary="Invalid webhook signature.",
    )


@pytest.mark.parametrize(
    "update",
    [
        WebhookEventStatsUpdate(accepted=True),
        WebhookEventStatsUpdate(auth_failed=True, error_summary="bad auth"),
        WebhookEventStatsUpdate(
            invalid_payload=True, error_summary="bad payload"
        ),
    ],
)
def test_webhook_event_stats_update_accepts_single_outcome(
    update: WebhookEventStatsUpdate,
) -> None:
    assert (
        sum([update.accepted, update.auth_failed, update.invalid_payload]) == 1
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
    with pytest.raises(ValidationError):
        WebhookEventStatsUpdate(**kwargs)


def test_webhook_integration_schema_to_model_includes_body_and_metadata() -> (
    None
):
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


def test_webhook_integration_schema_to_model_can_include_empty_resources() -> (
    None
):
    schema = _webhook_integration_schema()
    schema.user = None

    response = schema.to_model(include_resources=True)

    assert response.get_resources().user is None
