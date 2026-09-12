"""Unit tests for server configuration validation."""

import pytest
from pydantic import ValidationError

from zenml.config.server_config import ServerConfiguration
from zenml.enums import ArchiveBackend


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


@pytest.mark.parametrize(
    ("settings", "missing"),
    [
        ({"backend": "s3"}, "ZENML_SERVER_ARCHIVE__URI"),
        (
            {"backend": "s3", "uri": "gs://bucket"},
            "ZENML_SERVER_ARCHIVE__URI must start with s3://",
        ),
        (
            {"backend": "local", "uri": "s3://bucket"},
            "must be a local directory path",
        ),
        (
            {"backend": "s3", "uri": "s3://b", "schedule": "not a cron"},
            "ZENML_SERVER_ARCHIVE__SCHEDULE",
        ),
        ({"backend": "s3", "uri": "s3://b", "after_days": 3}, "after_days"),
    ],
)
def test_archive_settings_name_the_offending_variable(
    settings: dict, missing: str
) -> None:
    """An incomplete or inconsistent archive group names what is wrong."""
    with pytest.raises(ValidationError, match=missing):
        ServerConfiguration(archive=settings)


def test_archive_is_disabled_without_a_backend() -> None:
    """A server that names no backend never archives, whatever else is set."""
    config = ServerConfiguration(archive={"uri": "s3://bucket/archive"})

    assert not config.archive.enabled
    assert config.archive.backend == ArchiveBackend.DISABLED


def test_archive_settings_come_from_one_nested_group(monkeypatch) -> None:
    """Double-underscore variables address fields of the archive group."""
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__BACKEND", "s3")
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__URI", "s3://bucket/archive")
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__AFTER_DAYS", "45")
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__SCHEDULE", "0 3 * * 0")

    config = ServerConfiguration.get_server_config()

    assert config.archive.enabled
    assert config.archive.uri == "s3://bucket/archive"
    assert config.archive.after_days == 45
    assert config.archive.schedule == "0 3 * * 0"
    assert config.archive.max_runs_per_pass == 200
