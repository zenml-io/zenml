# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Execution retention startup checks."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from zenml.zen_server import zen_server_api
from zenml.zen_stores.sql_zen_store import SQLDatabaseDriver


def configure(monkeypatch: pytest.MonkeyPatch, driver, probe) -> None:
    """Enable archiving over a store with the given driver and probe."""
    store = SimpleNamespace(
        config=SimpleNamespace(driver=driver),
        archive_storage=SimpleNamespace(probe=probe),
    )
    monkeypatch.setattr(
        zen_server_api,
        "server_config",
        Mock(return_value=SimpleNamespace(archive_enabled=True)),
    )
    monkeypatch.setattr(zen_server_api, "zen_store", Mock(return_value=store))


def test_archive_uri_on_sqlite_stops_startup(monkeypatch) -> None:
    """Archiving is MySQL-only, so a SQLite server refuses to start."""
    configure(monkeypatch, SQLDatabaseDriver.SQLITE, Mock(return_value=True))

    with pytest.raises(RuntimeError, match="requires a MySQL database"):
        zen_server_api._check_archive_store_on_startup()


def test_unusable_storage_only_warns(monkeypatch, caplog) -> None:
    """A failed probe is logged without failing startup."""
    configure(monkeypatch, SQLDatabaseDriver.MYSQL, Mock(return_value=False))

    with caplog.at_level(logging.WARNING):
        zen_server_api._check_archive_store_on_startup()

    assert "cannot be written and read back" in caplog.text
