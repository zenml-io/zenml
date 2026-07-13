import hashlib
import hmac
from collections.abc import Mapping

import pytest

from zenml.enums import WebhookType
from zenml.webhooks.adapters import (
    BaseWebhookAdapter,
    CustomWebhookAdapter,
    GitHubWebhookAdapter,
    WebhookAuthenticationError,
    WebhookPayloadError,
    get_webhook_adapter,
)


class _BodyMetadataBearerAdapter(BaseWebhookAdapter):
    """Test adapter with bearer auth and body-derived event metadata."""

    webhook_type = WebhookType.CUSTOM

    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        if headers.get("authorization") != f"Bearer {secret}":
            raise WebhookAuthenticationError("Invalid bearer token.")

    def get_event_type(self, payload: dict, headers: Mapping[str, str]) -> str:
        event_type = payload.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise WebhookPayloadError("Missing event type in request body.")
        return event_type

    def get_delivery_id(
        self, payload: dict, headers: Mapping[str, str]
    ) -> str | None:
        delivery_id = payload.get("webhookId")
        return delivery_id if isinstance(delivery_id, str) else None


def _signature(secret: str, body: bytes) -> str:
    return (
        "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )


@pytest.mark.parametrize(
    "webhook_type, adapter_type",
    [
        (WebhookType.GITHUB, GitHubWebhookAdapter),
        (WebhookType.CUSTOM, CustomWebhookAdapter),
    ],
)
def test_get_webhook_adapter_returns_registered_adapter(
    webhook_type: WebhookType, adapter_type: type
) -> None:
    adapter = get_webhook_adapter(webhook_type)

    assert isinstance(adapter, adapter_type)
    assert adapter.webhook_type == webhook_type


@pytest.mark.parametrize(
    "adapter, headers, expected_event_type, expected_delivery_id",
    [
        (
            GitHubWebhookAdapter(),
            {
                "x-github-event": "push",
                "x-github-delivery": "github-delivery-id",
            },
            "push",
            "github-delivery-id",
        ),
        (
            CustomWebhookAdapter(),
            {
                "x-zenml-event": "pipeline.ready",
                "x-zenml-delivery": "custom-delivery-id",
            },
            "pipeline.ready",
            "custom-delivery-id",
        ),
    ],
)
def test_validate_returns_provider_event_for_signed_request(
    adapter: GitHubWebhookAdapter | CustomWebhookAdapter,
    headers: dict[str, str],
    expected_event_type: str,
    expected_delivery_id: str,
) -> None:
    secret = "webhook-secret"
    body = b'{"repository":"zenml","run_id":42}'
    headers[adapter.signature_header] = _signature(secret, body)

    event = adapter.validate(body=body, headers=headers, secret=secret)

    assert event.webhook_type == adapter.webhook_type
    assert event.event_type == expected_event_type
    assert event.delivery_id == expected_delivery_id
    assert event.payload == {"repository": "zenml", "run_id": 42}


def test_validate_supports_bearer_auth_and_body_event_metadata() -> None:
    adapter = _BodyMetadataBearerAdapter()
    body = b'{"type":"monitor.page","webhookId":"delivery-id"}'

    event = adapter.validate(
        body=body,
        headers={"authorization": "Bearer webhook-secret"},
        secret="webhook-secret",
    )

    assert event.event_type == "monitor.page"
    assert event.delivery_id == "delivery-id"


def test_parse_rejects_missing_body_event_type() -> None:
    adapter = _BodyMetadataBearerAdapter()

    with pytest.raises(
        WebhookPayloadError, match="Missing event type in request body"
    ):
        adapter.parse(body=b'{"webhookId":"delivery-id"}', headers={})


def test_authentication_uses_exact_raw_body_bytes() -> None:
    adapter = CustomWebhookAdapter()
    secret = "webhook-secret"
    signed_body = b'{"repository":"zenml","run_id":42}'
    equivalent_body = b'{\n  "repository": "zenml",\n  "run_id": 42\n}'
    headers = {
        "x-zenml-event": "pipeline.ready",
        "x-zenml-signature-256": _signature(secret, signed_body),
    }

    with pytest.raises(WebhookAuthenticationError):
        adapter.validate(body=equivalent_body, headers=headers, secret=secret)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"x-zenml-signature-256": "not-prefixed"},
        {"x-zenml-signature-256": "sha256=invalid"},
    ],
)
def test_authentication_rejects_missing_malformed_or_invalid_signature(
    headers: Mapping[str, str],
) -> None:
    adapter = CustomWebhookAdapter()

    with pytest.raises(WebhookAuthenticationError):
        adapter.authenticate(
            body=b'{"repository":"zenml"}',
            headers=headers,
            secret="webhook-secret",
        )


@pytest.mark.parametrize(
    "body, headers",
    [
        (b'{"repository":"zenml"}', {}),
        (b"not-json", {"x-zenml-event": "pipeline.ready"}),
        (b'["not", "an", "object"]', {"x-zenml-event": "pipeline.ready"}),
    ],
)
def test_parse_rejects_missing_event_header_or_invalid_payload(
    body: bytes, headers: Mapping[str, str]
) -> None:
    adapter = CustomWebhookAdapter()

    with pytest.raises(WebhookPayloadError):
        adapter.parse(body=body, headers=headers)
