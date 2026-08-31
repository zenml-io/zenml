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


def test_execution_archive_lease_covers_the_pass_budget() -> None:
    """The outer lease cannot expire during the configured pass budget."""
    with pytest.raises(ValidationError, match="archive_lease_seconds"):
        ServerConfiguration(
            execution_archive_time_budget=60,
            execution_archive_lease_seconds=59,
        )


def test_execution_archive_scan_and_work_limits_are_bounded() -> None:
    """Misconfiguration cannot turn one maintenance pass into a full scan."""
    with pytest.raises(ValidationError, match="execution_archive_scan_limit"):
        ServerConfiguration(execution_archive_scan_limit=1001)
    with pytest.raises(ValidationError, match="execution_archive_work_limit"):
        ServerConfiguration(execution_archive_work_limit=101)


def test_execution_archive_configuration_accepts_only_json_objects() -> None:
    """Environment input is parsed without accepting another JSON shape."""
    config = ServerConfiguration(
        execution_archive_configuration='{"path": "s3://archive"}'
    )
    assert config.execution_archive_configuration == {"path": "s3://archive"}

    with pytest.raises(ValidationError, match="must be a JSON object"):
        ServerConfiguration(execution_archive_configuration="[]")
