# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Populated marker upgrades through the FK-enabled CLI engine path."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa

from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.schemas import ArchiveBundleSchema
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


def test_marker_upgrade_preserves_referencing_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the additive upgrade after initialization has enabled foreign keys."""
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(tmp_path / "config"))
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{tmp_path / 'old.db'}"
        ),
        skip_migrations=True,
        skip_default_registrations=True,
    )
    # Keep the pre-marker fixture small, but preserve the actual cascade that
    # makes replacing a referenced pipeline_run table destructive.
    metadata = sa.MetaData()
    project = sa.Table(
        "project", metadata, sa.Column("id", sa.Uuid(), primary_key=True)
    )
    snapshot = sa.Table(
        "pipeline_snapshot",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
    )
    run = sa.Table(
        "pipeline_run",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("project.id")),
        sa.Column(
            "snapshot_id", sa.Uuid(), sa.ForeignKey("pipeline_snapshot.id")
        ),
    )
    step = sa.Table(
        "step_run",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            sa.Uuid(),
            sa.ForeignKey("pipeline_run.id", ondelete="CASCADE"),
        ),
        sa.Column("step_configuration", sa.Text(), nullable=False),
    )
    metadata.create_all(store.engine)
    project_id, snapshot_id, run_id, step_id = (uuid4() for _ in range(4))
    with store.engine.begin() as connection:
        assert (
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        )
        connection.execute(project.insert().values(id=project_id))
        connection.execute(snapshot.insert().values(id=snapshot_id))
        connection.execute(
            run.insert().values(
                id=run_id, project_id=project_id, snapshot_id=snapshot_id
            )
        )
        connection.execute(
            step.insert().values(
                id=step_id,
                pipeline_run_id=run_id,
                step_configuration='{"name":"keep"}',
            )
        )
    migrations = Alembic(store.engine)
    migrations.stamp("9f2b8c7d6e5a")
    statements: list[str] = []

    def record_statement(
        connection: sa.Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    sa.event.listen(store.engine, "before_cursor_execute", record_statement)
    try:
        migrations.upgrade("7a1c3d9e2b4f")
    finally:
        sa.event.remove(
            store.engine, "before_cursor_execute", record_statement
        )
    with store.engine.begin() as connection:
        assert (
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        )
        assert connection.execute(
            sa.select(step.c.id, step.c.step_configuration)
        ).all() == [(step_id, '{"name":"keep"}')]
        assert connection.execute(sa.select(run.c.id)).scalars().all() == [
            run_id
        ]
        assert connection.execute(
            sa.select(snapshot.c.id)
        ).scalars().all() == [snapshot_id]
        inspector = sa.inspect(connection)
        for table in ("pipeline_run", "pipeline_snapshot", "step_run"):
            columns = {
                column["name"]: column
                for column in inspector.get_columns(table)
            }
            assert "offloaded_at" not in columns
            assert columns["archive_bundle_id"]["nullable"] is True
            assert not any(
                "archive_bundle_id" in index["column_names"]
                for index in inspector.get_indexes(table)
            )
            assert not any(
                "archive_bundle_id" in fk["constrained_columns"]
                for fk in inspector.get_foreign_keys(table)
            )
        project_columns = {
            column["name"]: column
            for column in inspector.get_columns("project")
        }
        for name in ("retention_settings", "retention_state"):
            assert isinstance(project_columns[name]["type"], sa.TEXT)
            assert project_columns[name]["nullable"] is True
        step_columns = {
            column["name"]: column
            for column in inspector.get_columns("step_run")
        }
        assert step_columns["step_type"]["nullable"] is True
        assert step_columns["substitutions"]["nullable"] is True
        catalog_columns = {
            column["name"]: column
            for column in inspector.get_columns("archive_bundle")
        }
        assert set(catalog_columns) == set(
            ArchiveBundleSchema.__table__.columns.keys()
        )
        for column in ArchiveBundleSchema.__table__.columns:
            assert catalog_columns[column.name]["nullable"] == column.nullable
        for name in ("uri", "size_bytes", "manifest_hash"):
            assert catalog_columns[name]["nullable"] is True
        assert (
            str(catalog_columns["claim_token"]["default"]).strip("'\"") == "1"
        )
        indexes = {
            index["name"]: index
            for index in inspector.get_indexes("archive_bundle")
        }
        assert set(indexes) == {
            "ix_archive_bundle_active_root_id",
            "ix_archive_bundle_root_created_id",
        }
        assert indexes["ix_archive_bundle_active_root_id"]["unique"]
        assert indexes["ix_archive_bundle_active_root_id"]["column_names"] == [
            "active_root_id"
        ]
        assert indexes["ix_archive_bundle_root_created_id"][
            "column_names"
        ] == ["root_run_id", "created", "id"]
        upgraded = sa.Table(
            "pipeline_run", sa.MetaData(), autoload_with=connection
        )
        assert (
            connection.execute(sa.select(upgraded.c.retain)).scalar_one()
            is False
        )
        # Old writers omit the new column during a rolling upgrade.
        second_run_id = uuid4()
        connection.execute(
            run.insert().values(
                id=second_run_id,
                project_id=project_id,
                snapshot_id=snapshot_id,
            )
        )
        assert connection.execute(
            sa.select(upgraded.c.retain)
        ).scalars().all() == [False, False]
        assert (
            connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        )
    assert not any(
        "DROP TABLE" in statement.upper() for statement in statements
    )
    assert migrations.current_revisions() == ["7a1c3d9e2b4f"]

    migrations.downgrade("9f2b8c7d6e5a")
    with store.engine.begin() as connection:
        assert (
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        )
        assert set(connection.execute(sa.select(run.c.id)).scalars()) == {
            run_id,
            second_run_id,
        }
        assert connection.execute(sa.select(step.c.id)).scalars().all() == [
            step_id
        ]
        assert connection.execute(
            sa.select(snapshot.c.id)
        ).scalars().all() == [snapshot_id]
        assert (
            connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        )
        inspector = sa.inspect(connection)
        assert "archive_bundle" not in inspector.get_table_names()
        assert {
            column["name"] for column in inspector.get_columns("pipeline_run")
        }.isdisjoint({"archive_bundle_id", "retain"})
        assert {
            column["name"] for column in inspector.get_columns("step_run")
        }.isdisjoint({"archive_bundle_id", "step_type", "substitutions"})
        assert "archive_bundle_id" not in {
            column["name"]
            for column in inspector.get_columns("pipeline_snapshot")
        }
    assert migrations.current_revisions() == ["9f2b8c7d6e5a"]
    store.engine.dispose()
