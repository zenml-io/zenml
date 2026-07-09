import hashlib
import hmac
from collections.abc import Mapping

import pytest

from zenml.enums import WebhookType
from zenml.webhooks.adapters import (
    CustomWebhookAdapter,
    GitHubWebhookAdapter,
    WebhookAuthenticationError,
    WebhookPayloadError,
    get_webhook_adapter,
)


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
    "adapter, headers",
    [
        (
            GitHubWebhookAdapter(),
            {
                "x-github-event": "push",
                "x-github-delivery": "github-delivery-id",
            },
        ),
        (
            CustomWebhookAdapter(),
            {
                "x-zenml-event": "pipeline.ready",
                "x-zenml-delivery": "custom-delivery-id",
            },
        ),
    ],
)
def test_validate_returns_provider_event_for_signed_request(
    adapter: GitHubWebhookAdapter | CustomWebhookAdapter,
    headers: dict[str, str],
) -> None:
    secret = "webhook-secret"
    body = b'{"repository":"zenml","run_id":42}'
    headers[adapter.signature_header] = _signature(secret, body)

    event = adapter.validate(body=body, headers=headers, secret=secret)

    assert event.webhook_type == adapter.webhook_type
    assert event.event_type == headers[adapter.event_header]
    assert event.delivery_id == headers[adapter.delivery_header]
    assert event.payload == {"repository": "zenml", "run_id": 42}


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
