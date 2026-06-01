"""Unit tests for SQL Zen Store utility behavior."""

from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlmodel import Session, col, select

from zenml.client import Client
from zenml.constants import ENV_ZENML_DISABLE_DATABASE_MIGRATION
from zenml.models import ApiTransactionRequest
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import ApiTransactionSchema
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_run_migrations_helper_func(monkeypatch):
    """Test that database migrations run when enabled."""
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
    """Test that database migrations are skipped when configured."""
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


def test_expired_api_transaction_cleanup_is_batched(clean_client):
    """Expired API transaction cleanup deletes a bounded batch."""
    store = clean_client.zen_store

    if not isinstance(store, SqlZenStore):
        pytest.skip(
            "API transaction cleanup is testable only for SQL ZenML store"
        )

    now = utc_now()
    user_id = clean_client.active_user.id
    expired_transaction_ids = [uuid4() for _ in range(3)]
    active_transaction_id = uuid4()

    with Session(store.engine) as session:
        session.add_all(
            [
                ApiTransactionSchema(
                    id=transaction_id,
                    method="GET",
                    url=f"/api/{transaction_id}",
                    user_id=user_id,
                    completed=True,
                    expired=now,
                )
                for transaction_id in expired_transaction_ids
            ]
            + [
                ApiTransactionSchema(
                    id=active_transaction_id,
                    method="GET",
                    url="/api/active",
                    user_id=user_id,
                    completed=False,
                    expired=now,
                )
            ]
        )
        session.commit()

    deleted_count = store.cleanup_expired_api_transactions(batch_size=2)

    assert deleted_count == 2

    with Session(store.engine) as session:
        remaining_expired_completed = session.exec(
            select(ApiTransactionSchema.id).where(
                col(ApiTransactionSchema.completed),
                col(ApiTransactionSchema.expired) <= now,
            )
        ).all()
        active_transaction = session.get(
            ApiTransactionSchema, active_transaction_id
        )

    assert len(remaining_expired_completed) == 1
    assert active_transaction is not None


def test_completed_expired_api_transaction_is_recreated(clean_client):
    """Completed expired API transactions are treated as cache misses."""
    store = clean_client.zen_store

    if not isinstance(store, SqlZenStore):
        pytest.skip(
            "API transaction recreation is testable only for SQL ZenML store"
        )

    transaction_id = uuid4()
    user_id = clean_client.active_user.id
    expired_at = utc_now() - timedelta(seconds=1)

    with Session(store.engine) as session:
        session.add(
            ApiTransactionSchema(
                id=transaction_id,
                method="POST",
                url="/api/retry",
                user_id=user_id,
                completed=True,
                expired=expired_at,
            )
        )
        session.commit()

    api_transaction, created = store.get_or_create_api_transaction(
        ApiTransactionRequest(
            transaction_id=transaction_id,
            method="POST",
            url="/api/retry",
        )
    )

    assert created is True
    assert api_transaction.id == transaction_id
    assert api_transaction.completed is False

    with Session(store.engine) as session:
        transaction = session.get(ApiTransactionSchema, transaction_id)

    assert transaction is not None
    assert transaction.completed is False
    assert transaction.expired is None
