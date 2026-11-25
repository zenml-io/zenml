"""Unit tests for server configuration validation."""

import os

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
    ("dashboard_url", "classic_url"),
    [
        ("https://cloud.zenml.io", "https://classic.cloud.zenml.io"),
        ("https://cloud.zenml.io/", "https://classic.cloud.zenml.io"),
        (
            "https://staging.cloud.zenml.io",
            "https://classic.staging.cloud.zenml.io",
        ),
        ("https://enterprise.example.com", None),
        ("https://cloud.zenml.io.example.com", None),
        ("http://cloud.zenml.io", None),
    ],
)
@pytest.mark.parametrize(
    "custom_origins",
    [None, "*", "https://custom.example.com,https://classic.cloud.zenml.io"],
)
def test_pro_server_cors_includes_hosted_classic_dashboard(
    monkeypatch: pytest.MonkeyPatch,
    dashboard_url: str,
    classic_url: str | None,
    custom_origins: str | None,
) -> None:
    """Hosted dashboards allow Classic without changing enterprise origins."""
    for name in os.environ:
        if name.startswith("ZENML_SERVER_"):
            monkeypatch.delenv(name)
    values = {
        "DEPLOYMENT_TYPE": "cloud",
        "SERVER_URL": "https://workspace.example.com",
        "PRO_DASHBOARD_URL": dashboard_url,
        "PRO_API_URL": "https://api.example.com",
        "PRO_OAUTH2_CLIENT_SECRET": "test-secret",
        "PRO_OAUTH2_AUDIENCE": "test-audience",
        "PRO_ORGANIZATION_ID": "00000000-0000-0000-0000-000000000001",
        "PRO_WORKSPACE_ID": "00000000-0000-0000-0000-000000000002",
        "PRO_WORKSPACE_NAME": "test-workspace",
    }
    if custom_origins is not None:
        values["CORS_ALLOW_ORIGINS"] = custom_origins
    for name, value in values.items():
        monkeypatch.setenv(f"ZENML_SERVER_{name}", value)

    config = ServerConfiguration.get_server_config()

    expected = {
        dashboard_url.rstrip("/"),
        "https://api.example.com",
        "https://workspace.example.com",
    }
    if custom_origins and custom_origins != "*":
        expected.update(custom_origins.split(","))
    if classic_url:
        expected.add(classic_url)
    assert config.cors_allow_origins is not None
    assert set(config.cors_allow_origins) == expected
    assert len(config.cors_allow_origins) == len(expected)
    assert config.dashboard_url == (
        f"{dashboard_url.rstrip('/')}/workspaces/test-workspace"
    )
