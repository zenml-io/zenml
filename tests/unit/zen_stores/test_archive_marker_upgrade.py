# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Populated upgrade must preserve referencing rows and support old writers."""

from uuid import uuid4

import sqlalchemy as sa

from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


def test_marker_upgrade_preserves_referencing_rows(tmp_path, monkeypatch):
    """A real cascading FK detects destructive table replacement during upgrade."""
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(tmp_path / "config"))
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url=f"sqlite:///{tmp_path / 'old.db'}"
        ),
        skip_migrations=True,
        skip_default_registrations=True,
    )
    metadata = sa.MetaData()
    tables = {}
    for name in (
        "project",
        "server_settings",
        "pipeline_snapshot",
        "pipeline_run",
        "step_run",
    ):
        columns = [sa.Column("id", sa.Uuid(), primary_key=True)]
        if name == "pipeline_run":
            # The sweep's keyset index is built over this column.
            columns.append(sa.Column("end_time", sa.DateTime()))
        if name == "step_run":
            columns.extend(
                [
                    sa.Column(
                        "pipeline_run_id",
                        sa.Uuid(),
                        sa.ForeignKey("pipeline_run.id", ondelete="CASCADE"),
                    ),
                    sa.Column("step_configuration", sa.Text(), nullable=False),
                ]
            )
        tables[name] = sa.Table(name, metadata, *columns)
    metadata.create_all(store.engine)
    identities = {name: uuid4() for name in tables}
    with store.engine.begin() as connection:
        assert (
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        )
        for name, table in tables.items():
            values = {"id": identities[name]}
            if name == "step_run":
                values.update(
                    pipeline_run_id=identities["pipeline_run"],
                    step_configuration='{"name":"keep"}',
                )
            connection.execute(table.insert().values(**values))
    migrations = Alembic(store.engine)
    migrations.stamp("9f2b8c7d6e5a")
    migrations.upgrade("c3f5a9e1d7b2")
    with store.engine.begin() as connection:
        for name, table in tables.items():
            assert connection.execute(
                sa.select(table.c.id)
            ).scalars().all() == [identities[name]]
        assert (
            connection.execute(
                sa.select(tables["step_run"].c.step_configuration)
            ).scalar_one()
            == '{"name":"keep"}'
        )
        inspector = sa.inspect(connection)
        for name in ("pipeline_run", "pipeline_snapshot", "step_run"):
            columns = {c["name"]: c for c in inspector.get_columns(name)}
            assert columns["archive_bundle_id"]["nullable"] is True
        upgraded = sa.Table(
            "pipeline_run", sa.MetaData(), autoload_with=connection
        )
        # A rolling deployment's old writer omits the marker column.
        connection.execute(tables["pipeline_run"].insert().values(id=uuid4()))
        assert connection.execute(
            sa.select(upgraded.c.archive_bundle_id)
        ).scalars().all() == [None, None]
        assert {
            index["name"] for index in inspector.get_indexes("pipeline_run")
        } >= {"ix_pipeline_run_end_time_id"}
        assert (
            connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        )
        assert (
            connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        )
    assert migrations.current_revisions() == ["c3f5a9e1d7b2"]
    store.engine.dispose()
