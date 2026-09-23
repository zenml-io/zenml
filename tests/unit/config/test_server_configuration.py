"""Unit tests for server configuration validation."""

import pytest
from pydantic import ValidationError

from zenml.config.server_config import ArchiveSettings, ServerConfiguration


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
        webhook_event_handler_sources="package.First, package.Second, ",
    )

    assert config.event_handler_sources == [
        "package.Handler",
        "package.OtherHandler",
    ]
    assert config.webhook_event_handler_sources == [
        "package.First",
        "package.Second",
    ]


def test_event_sources_reject_invalid_values() -> None:
    """Invalid extension-source values are not silently discarded."""
    with pytest.raises(ValidationError):
        ServerConfiguration(webhook_event_handler_sources={"invalid": True})


def test_archive_rejects_age_below_minimum() -> None:
    """The retention policy requires at least seven days."""
    with pytest.raises(ValidationError, match="after_days"):
        ServerConfiguration(archive={"uri": "s3://b", "after_days": 3})


def test_archive_is_disabled_without_a_uri() -> None:
    """An unconfigured server cannot create archives."""
    config = ServerConfiguration()
    assert not config.archive.configured
    assert not config.archive.new_archives_enabled


def test_configured_storage_allows_manual_archiving() -> None:
    """Configured storage allows manual archiving."""
    config = ServerConfiguration(archive={"uri": "s3://bucket/archive"})

    assert config.archive.new_archives_enabled


def test_archive_settings_come_from_one_nested_group(monkeypatch) -> None:
    """Double-underscore variables address fields of the archive group."""
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__URI", "s3://bucket/archive")
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__AFTER_DAYS", "45")

    config = ServerConfiguration.get_server_config()

    assert config.archive.configured
    assert config.archive.new_archives_enabled
    assert config.archive.uri == "s3://bucket/archive"
    assert config.archive.after_days == 45


def test_archive_can_pause_new_writes_without_losing_storage() -> None:
    """Storage configuration remains available while new archives are paused."""
    archive = ArchiveSettings(uri="/tmp/archive", enabled=False)

    assert archive.configured
    assert not archive.new_archives_enabled
    assert archive.root_uri == "/tmp/archive"


@pytest.mark.parametrize("uri", ["", "   "])
def test_archive_rejects_empty_uri(uri: str) -> None:
    """Empty storage configuration cannot accidentally select a local path."""
    with pytest.raises(ValidationError, match="URI must not be empty"):
        ArchiveSettings(uri=uri)


@pytest.mark.parametrize("removed_field", ["backend", "connector_id"])
def test_archive_rejects_removed_configuration_fields(
    removed_field: str,
) -> None:
    """Removed selectors must not silently change the authentication mode."""
    with pytest.raises(
        ValidationError, match="Extra inputs are not permitted"
    ):
        ArchiveSettings.model_validate(
            {"uri": "s3://bucket/archive", removed_field: "unused"}
        )
