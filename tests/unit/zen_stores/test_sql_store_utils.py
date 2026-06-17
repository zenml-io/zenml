"""Unit tests for SQL Zen Store utility behavior."""

from unittest.mock import MagicMock

import pytest

from zenml.client import Client
from zenml.constants import ENV_ZENML_DISABLE_DATABASE_MIGRATION
from zenml.zen_stores.schemas import (
    ArtifactVersionSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
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


def _index_columns(schema: type, index_name: str) -> list[str]:
    indexes = {
        index.name: [column.name for column in index.columns]
        for index in schema.__table__.indexes
    }
    return indexes[index_name]


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
