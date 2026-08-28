"""Tests for server URL utilities."""

from types import SimpleNamespace

import pytest

from zenml.config.server_config import ServerConfiguration
from zenml.utils.server_utils import get_server_api_url


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
def test_get_server_api_url(
    monkeypatch: pytest.MonkeyPatch,
    server_url: str | None,
    root_url_path: str,
    expected: str | None,
) -> None:
    """The API URL is absolute, normalized, and optional."""
    monkeypatch.setattr(
        ServerConfiguration,
        "get_server_config",
        classmethod(
            lambda _: SimpleNamespace(
                server_url=server_url,
                root_url_path=root_url_path,
            )
        ),
    )

    assert get_server_api_url() == expected
