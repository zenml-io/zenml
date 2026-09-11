# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Execution retention startup diagnostics."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock

import pytest

from zenml.zen_server import zen_server_api


def test_enabled_retention_warns_when_archive_store_cannot_load(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A broken configured store is visible without failing server startup.

    Args:
        monkeypatch: Isolate server configuration and store access.
        caplog: Capture the startup warning.
    """
    store = Mock()
    type(store).archive_artifact_store = PropertyMock(
        side_effect=RuntimeError("unavailable")
    )
    monkeypatch.setattr(
        zen_server_api,
        "server_config",
        Mock(return_value=SimpleNamespace(archive_enabled=True)),
    )
    monkeypatch.setattr(zen_server_api, "zen_store", Mock(return_value=store))

    with caplog.at_level(logging.WARNING):
        zen_server_api._check_archive_store_on_startup()

    assert "archive_artifact_store_id could not be loaded" in caplog.text
