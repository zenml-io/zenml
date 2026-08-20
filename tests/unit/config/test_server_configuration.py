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


def test_webhook_event_consumer_sources_accept_comma_separated_value() -> None:
    """Webhook consumer implementations can be configured through the env."""
    config = ServerConfiguration(
        webhook_event_consumer_sources="package.First, package.Second"
    )

    assert config.webhook_event_consumer_sources == [
        "package.First",
        "package.Second",
    ]
