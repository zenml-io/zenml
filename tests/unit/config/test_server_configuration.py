"""Unit tests for server configuration validation."""

import pytest
from pydantic import ValidationError

from zenml.config.server_config import ServerConfiguration


@pytest.mark.parametrize(
    ("server_url", "root_url_path", "expected"),
    [
        (
            "https://zenml.example.com/",
            "",
            "https://zenml.example.com/api/v1",
        ),
        (
            "https://zenml.example.com/base/",
            "/workspace/",
            "https://zenml.example.com/base/workspace/api/v1",
        ),
        (None, "/workspace", None),
    ],
)
def test_server_api_url(
    server_url: str | None,
    root_url_path: str,
    expected: str | None,
) -> None:
    """The external API URL is absolute, normalized, and optional."""
    config = ServerConfiguration(
        server_url=server_url,
        root_url_path=root_url_path,
    )

    assert config.server_api_url == expected


def test_api_transaction_cleanup_time_budget_cannot_exceed_interval() -> None:
    """Cleanup passes must not outlive their scheduling interval."""
    with pytest.raises(ValidationError, match="cleanup_time_budget"):
        ServerConfiguration(
            api_transaction_cleanup_interval=1,
            api_transaction_cleanup_time_budget=2,
        )


def test_api_transaction_cleanup_time_budget_can_match_interval() -> None:
    """Cleanup passes may use the full interval."""
    config = ServerConfiguration(
        api_transaction_cleanup_interval=1,
        api_transaction_cleanup_time_budget=1,
    )

    assert config.api_transaction_cleanup_time_budget == 1


def test_event_sources_accept_comma_separated_values() -> None:
    """Event extensions can be configured through comma-separated env vars."""
    config = ServerConfiguration(
        event_handler_sources="package.Handler, , package.OtherHandler",
        webhook_event_consumer_sources="package.First, package.Second, ",
    )

    assert config.event_handler_sources == [
        "package.Handler",
        "package.OtherHandler",
    ]
    assert config.webhook_event_consumer_sources == [
        "package.First",
        "package.Second",
    ]


def test_event_sources_reject_invalid_values() -> None:
    """Invalid extension-source values are not silently discarded."""
    with pytest.raises(ValidationError):
        ServerConfiguration(webhook_event_consumer_sources={"invalid": True})
