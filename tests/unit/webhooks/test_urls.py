"""Tests for webhook endpoint URL utilities."""

from uuid import uuid4

import pytest

from zenml.webhooks import urls


def test_get_webhook_intake_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The intake URL extends the normalized server API URL."""
    webhook_id = uuid4()
    monkeypatch.setattr(
        urls,
        "get_server_api_url",
        lambda: "https://zenml.example.com/api/v1",
    )

    assert urls.get_webhook_intake_url(
        webhook_type="github",
        webhook_id=webhook_id,
    ) == (
        f"https://zenml.example.com/api/v1/webhooks/github/{webhook_id}/events"
    )


def test_get_webhook_intake_url_requires_external_server_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No intake URL is advertised without an external server URL."""
    monkeypatch.setattr(urls, "get_server_api_url", lambda: None)

    assert (
        urls.get_webhook_intake_url(
            webhook_type="custom",
            webhook_id=uuid4(),
        )
        is None
    )
