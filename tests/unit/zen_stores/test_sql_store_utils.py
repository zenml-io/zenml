"""Unit tests for SQL Zen Store utility behavior."""

import gzip
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import mysql
from sqlmodel import Session, col, select

from zenml.client import Client
from zenml.constants import ENV_ZENML_DISABLE_DATABASE_MIGRATION
from zenml.utils.time_utils import utc_now
from zenml.zen_stores import sql_zen_store as sql_zen_store_module
from zenml.zen_stores.schemas import (
    ApiTransactionResultSchema,
    ApiTransactionSchema,
    ArtifactVersionSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import (
    SQLDatabaseDriver,
    SqlZenStore,
)


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


def _index_columns(schema: type, index_name: str) -> list[str]:
    indexes = {
        index.name: [column.name for column in index.columns]
        for index in schema.__table__.indexes
    }
    return indexes[index_name]


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
        session.flush()
        session.add_all(
            [
                ApiTransactionResultSchema(
                    id=transaction_id,
                    result=gzip.compress(b'"stale-result"'),
                )
                for transaction_id in expired_transaction_ids
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
        remaining_results = session.exec(
            select(ApiTransactionResultSchema.id).where(
                col(ApiTransactionResultSchema.id).in_(expired_transaction_ids)
            )
        ).all()

    assert len(remaining_expired_completed) == 1
    assert len(remaining_results) == 1
    assert active_transaction is not None


def test_mysql_expired_api_transaction_cleanup_uses_bounded_predicate_delete(
    monkeypatch: pytest.MonkeyPatch,
):
    """MySQL cleanup uses a bounded delete with expiration predicates."""
    compiled_queries: list[str] = []

    class _DeleteResult:
        rowcount = 0

    class _Session:
        def __init__(self, _engine: object) -> None:
            pass

        def __enter__(self) -> "_Session":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def execute(self, query: object) -> _DeleteResult:
            compiled_queries.append(
                str(query.compile(dialect=mysql.dialect()))
            )
            return _DeleteResult()

        def commit(self) -> None:
            pass

    store = object.__new__(SqlZenStore)
    object.__setattr__(
        store, "config", SimpleNamespace(driver=SQLDatabaseDriver.MYSQL)
    )
    object.__setattr__(store, "_engine", object())
    monkeypatch.setattr(sql_zen_store_module, "Session", _Session)

    deleted_count = store.cleanup_expired_api_transactions(batch_size=1)

    assert deleted_count == 0
    assert "DELETE FROM api_transaction" in compiled_queries[0]
    assert "api_transaction.completed" in compiled_queries[0]
    assert "api_transaction.expired" in compiled_queries[0]
    assert "FOR UPDATE" not in compiled_queries[0]
    assert "LIMIT" in compiled_queries[0]


def test_api_transaction_index_covers_expired_completed_cleanup():
    """API transaction index supports completed-expired cleanup scans."""
    assert _index_columns(
        ApiTransactionSchema, "ix_api_transaction_completed_expired"
    ) == ["completed", "expired"]


def test_artifact_version_index_covers_artifact_version_lookup():
    """Artifact version index supports artifact-scoped version lookups."""
    assert _index_columns(
        ArtifactVersionSchema,
        "ix_artifact_version_artifact_id_version_number",
    ) == ["artifact_id", "version_number"]


def test_pipeline_run_index_covers_project_pagination():
    """Pipeline run index keeps project filtering before pagination columns."""
    assert _index_columns(
        PipelineRunSchema, "ix_pipeline_run_project_id_created_id"
    ) == ["project_id", "created", "id"]


def test_pipeline_snapshot_indexes_cover_pagination_and_name_filters():
    """Pipeline snapshot indexes cover the known slow query shapes."""
    assert _index_columns(
        PipelineSnapshotSchema, "ix_pipeline_snapshot_project_id_created_id"
    ) == ["project_id", "created", "id"]
    assert _index_columns(
        PipelineSnapshotSchema, "ix_pipeline_snapshot_project_id_name"
    ) == ["project_id", "name"]


def test_step_configuration_indexes_cover_snapshot_and_run_hydration():
    """Step configuration indexes support snapshot and step-run hydration."""
    assert _index_columns(
        StepConfigurationSchema, "ix_step_configuration_snapshot_id_name"
    ) == ["snapshot_id", "name"]
    assert _index_columns(
        StepConfigurationSchema, "ix_step_configuration_step_run_id"
    ) == ["step_run_id"]


def test_step_run_index_covers_hydrated_listing_query_shape():
    """Step run index keeps equality predicates before pagination columns."""
    assert _index_columns(
        StepRunSchema,
        "ix_step_run_project_id_pipeline_run_id_name_created_id",
    ) == [
        "project_id",
        "pipeline_run_id",
        "name",
        "created",
        "id",
    ]
