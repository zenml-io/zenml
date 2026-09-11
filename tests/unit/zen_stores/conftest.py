# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Disposable MySQL database; CI must require this tier explicitly."""

import calendar
import os
from datetime import datetime
from uuid import uuid4

import pymysql
import pytest
from sqlalchemy import Engine, create_engine, event, make_url, select, text
from sqlmodel import SQLModel

from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def NOW():
    """Freeze the database clock for age, lease, and grace-period assertions."""
    now = datetime(2026, 1, 1)

    def freeze(connection, record):
        if isinstance(connection, pymysql.connections.Connection):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET @@session.time_zone = '+00:00', @@session.timestamp = %s",
                    (calendar.timegm(now.timetuple()),),
                )

    event.listen(Engine, "connect", freeze)
    try:
        yield now
    finally:
        event.remove(Engine, "connect", freeze)


@pytest.fixture(scope="session")
def retention_database(request, tmp_path_factory):
    """Migrate a unique database, save its default rows, and drop it on exit."""
    server_url = os.environ.get("ZENML_RETENTION_TEST_MYSQL_URL")
    if not server_url:
        message = (
            "Set ZENML_RETENTION_TEST_MYSQL_URL to a disposable MySQL server."
        )
        if request.config.getoption("--require-retention-mysql"):
            pytest.fail(message)
        pytest.skip(message)
    server = make_url(server_url).set(drivername="mysql", database=None)
    url = server.set(database=f"zenml_retention_{uuid4().hex[:12]}")
    config = SqlZenStoreConfiguration(
        url=url.render_as_string(hide_password=False)
    )
    with pytest.MonkeyPatch.context() as environment:
        environment.setenv(
            "ZENML_CONFIG_PATH", str(tmp_path_factory.mktemp("retention"))
        )
        store = SqlZenStore(config=config)
    with store.engine.connect() as connection:
        baseline = {
            table: [
                dict(row)
                for row in connection.execute(select(table)).mappings()
            ]
            for table in SQLModel.metadata.sorted_tables
        }
    store.engine.dispose()
    engine = create_engine(url.set(drivername="mysql+pymysql"))
    try:
        yield config, engine, baseline
    finally:
        engine.dispose()
        admin = create_engine(server.set(drivername="mysql+pymysql"))
        with admin.begin() as connection:
            connection.execute(text(f"DROP DATABASE `{url.database}`"))
        admin.dispose()


@pytest.fixture
def retention_store(retention_database, tmp_path, monkeypatch, NOW):
    """Reset the isolated database before each test, preserving registrations."""
    config, engine, baseline = retention_database
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(tmp_path / "config"))
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(baseline):
            connection.execute(table.delete())
        for table, rows in baseline.items():
            if rows:
                connection.execute(table.insert(), rows)
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    store = SqlZenStore(config=config)
    try:
        yield store
    finally:
        store.engine.dispose()
