"""Unit tests for server configuration validation."""

import pytest
from pydantic import ValidationError

from zenml.config.server_config import ServerConfiguration


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
