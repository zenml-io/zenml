# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Shared fixtures for Zen store unit tests."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import pytest
from sqlalchemy import Engine, event

from tests.unit.zen_stores.retention.fixture_graph import FROZEN_NOW
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def NOW(monkeypatch: pytest.MonkeyPatch) -> Iterator[datetime]:
    """Freeze application and SQLite clocks for retention tests.

    Args:
        monkeypatch: Restore the application clock after the test.

    Yields:
        Deterministic naive UTC timestamp.
    """
    now = FROZEN_NOW
    try:
        from zenml.zen_stores.retention import eligibility
    except ModuleNotFoundError:
        # Package 1 introduces the shared fixture before retention exists.
        eligibility = None
    if eligibility is not None:
        monkeypatch.setattr(eligibility, "utc_now", lambda: now)

    def freeze(connection: Any, record: Any) -> None:
        """Give SQLite's SQL clock the same time as the policy clock.

        Args:
            connection: Newly connected database driver.
            record: SQLAlchemy connection lifecycle record.
        """
        if isinstance(connection, sqlite3.Connection):
            connection.create_function(
                "current_timestamp", 0, lambda: now.isoformat(" ")
            )

    event.listen(Engine, "connect", freeze)
    try:
        yield now
    finally:
        event.remove(Engine, "connect", freeze)


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, NOW: datetime
) -> Iterator[SqlZenStore]:
    """Create an isolated SQLite store.

    Args:
        tmp_path: Temporary test directory.
        monkeypatch: Environment isolation fixture.
        NOW: Shared retention evaluation time.

    Yields:
        The initialized store, disposed after the test.
    """
    config_path = tmp_path / "config"
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(config_path))
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(url=f"sqlite:///{tmp_path / 'db'}"),
        skip_default_registrations=False,
    )
    try:
        yield store
    finally:
        store.engine.dispose()
