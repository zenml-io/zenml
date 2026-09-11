# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Shared fixtures for Zen store unit tests.

Execution retention only runs on MySQL, so its tests use ``retention_store``:
one disposable database per test session on the server named by
``ZENML_RETENTION_TEST_MYSQL_URL``, reset to the store's default rows before
every test. Other store tests keep the SQLite ``sql_store``.
"""

import calendar
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List
from uuid import uuid4

import pymysql
import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, create_engine, event, make_url, select, text
from sqlmodel import SQLModel

from tests.unit.zen_stores.retention.fixture_graph import FROZEN_NOW
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)

RETENTION_MYSQL_URL = "ZENML_RETENTION_TEST_MYSQL_URL"


@pytest.fixture
def NOW(monkeypatch: pytest.MonkeyPatch) -> Iterator[datetime]:
    """Freeze the application clock and every new database session clock.

    Args:
        monkeypatch: Restore the application clock after the test.

    Yields:
        Deterministic naive UTC timestamp.
    """
    now = FROZEN_NOW
    try:
        from zenml.zen_stores.retention import eligibility
    except ModuleNotFoundError:
        eligibility = None
    if eligibility is not None:
        monkeypatch.setattr(eligibility, "utc_now", lambda: now)

    def freeze(connection: Any, record: Any) -> None:
        """Give the SQL clock the same time as the policy clock.

        Args:
            connection: Newly connected database driver.
            record: SQLAlchemy connection lifecycle record.
        """
        if isinstance(connection, sqlite3.Connection):
            connection.create_function(
                "current_timestamp", 0, lambda: now.isoformat(" ")
            )
        elif isinstance(connection, pymysql.connections.Connection):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET @@session.time_zone = '+00:00', "
                    "@@session.timestamp = %s",
                    (calendar.timegm(now.timetuple()),),
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


class RetentionDatabase(BaseModel):
    """A disposable MySQL database holding only the store's default rows."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    url: str
    engine: Engine
    baseline: Dict[str, List[Dict[str, Any]]]

    def reset(self) -> None:
        """Delete every row and restore the default registrations."""
        tables = SQLModel.metadata.sorted_tables
        with self.engine.begin() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in reversed(tables):
                connection.execute(table.delete())
            for table in tables:
                if rows := self.baseline.get(table.name):
                    connection.execute(table.insert(), rows)
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture(scope="session")
def retention_database(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[RetentionDatabase]:
    """Create one disposable MySQL database for the test session.

    Args:
        request: Reads the option that forbids skipping in CI.
        tmp_path_factory: Session-scoped temporary directories.

    Yields:
        The migrated database and its default rows.
    """
    server_url = os.environ.get(RETENTION_MYSQL_URL, "")
    if not server_url:
        message = (
            f"Execution retention tests need MySQL: set {RETENTION_MYSQL_URL} "
            "to a disposable server, for example "
            "mysql://root:<password>@127.0.0.1:3307."
        )
        if request.config.getoption("--require-retention-mysql"):
            pytest.fail(message)
        pytest.skip(message)
    server = make_url(server_url).set(drivername="mysql", database=None)
    url = server.set(database=f"zenml_retention_{uuid4().hex[:12]}")
    rendered = url.render_as_string(hide_password=False)
    with pytest.MonkeyPatch.context() as environment:
        environment.setenv(
            "ZENML_CONFIG_PATH",
            str(tmp_path_factory.mktemp("retention-config")),
        )
        store = SqlZenStore(
            config=SqlZenStoreConfiguration(url=rendered),
            skip_default_registrations=False,
        )
    assert store.engine.dialect.name == "mysql"
    baseline: Dict[str, List[Dict[str, Any]]] = {}
    with store.engine.connect() as connection:
        for table in SQLModel.metadata.sorted_tables:
            rows = connection.execute(select(table)).mappings().all()
            if rows:
                baseline[table.name] = [dict(row) for row in rows]
    store.engine.dispose()
    engine = create_engine(url.set(drivername="mysql+pymysql"))
    try:
        yield RetentionDatabase(url=rendered, engine=engine, baseline=baseline)
    finally:
        engine.dispose()
        admin = create_engine(server.set(drivername="mysql+pymysql"))
        with admin.begin() as connection:
            connection.execute(text(f"DROP DATABASE `{url.database}`"))
        admin.dispose()


@pytest.fixture
def retention_store(
    retention_database: RetentionDatabase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    NOW: datetime,
) -> Iterator[SqlZenStore]:
    """Create a MySQL store over a database reset to its default rows.

    Args:
        retention_database: Session database and default rows.
        tmp_path: Temporary test directory.
        monkeypatch: Environment isolation fixture.
        NOW: Shared retention evaluation time.

    Yields:
        The initialized store, disposed after the test.
    """
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(tmp_path / "config"))
    retention_database.reset()
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(url=retention_database.url),
        skip_default_registrations=False,
    )
    try:
        yield store
    finally:
        store.engine.dispose()
