from unittest.mock import MagicMock

import pytest

from zenml.client import Client
from zenml.constants import ENV_ZENML_DISABLE_DATABASE_MIGRATION
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_run_migrations_helper_func(monkeypatch):
    store = Client().zen_store

    if not isinstance(store, SqlZenStore):
        pytest.skip(
            "Run migration helper function is testable only for SQL ZenML store"
        )

    fake_migrate = MagicMock(return_value=None)

    with monkeypatch.context() as m:
        m.setattr(SqlZenStore, "migrate_database", fake_migrate)
        store.skip_migrations = False
        m.setenv(ENV_ZENML_DISABLE_DATABASE_MIGRATION, "false")

        store._run_migrations()

        fake_migrate.assert_called_once()


def test_run_run_migrations_skipped(monkeypatch):
    store = Client().zen_store

    if not isinstance(store, SqlZenStore):
        pytest.skip(
            "Run migration helper function is testable only for SQL ZenML store"
        )

    fake_migrate = MagicMock(return_value=None)

    # check skip migrations via store.skip_migrations works

    with monkeypatch.context() as m:
        m.setattr(SqlZenStore, "migrate_database", fake_migrate)
        store.skip_migrations = True
        m.setenv(ENV_ZENML_DISABLE_DATABASE_MIGRATION, "false")

        store._run_migrations()

        fake_migrate.assert_not_called()

    # check skip migrations via env var works

    with monkeypatch.context() as m:
        m.setattr(SqlZenStore, "migrate_database", fake_migrate)
        store.skip_migrations = False
        m.setenv(ENV_ZENML_DISABLE_DATABASE_MIGRATION, "true")

        store._run_migrations()

        fake_migrate.assert_not_called()
