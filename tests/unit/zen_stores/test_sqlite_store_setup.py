#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for the journal mode and cascade indexes of a local SQLite store."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import List, Set, Tuple

import pytest
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

import zenml.zen_stores.migrations.versions as migration_versions
import zenml.zen_stores.schemas  # noqa: F401
from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
)

MIGRATION_FILE_NAME = "4f2b8c1d9a37_index_run_cascade_foreign_keys.py"


def _load_cascade_index_migration() -> ModuleType:
    """Load the migration that adds the cascade indexes.

    The file name is not a valid module name, so the module cannot be
    imported directly.

    Returns:
        The migration module.
    """
    path = Path(migration_versions.__file__).parent / MIGRATION_FILE_NAME
    spec = importlib.util.spec_from_file_location("cascade_indexes", path)
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = _load_cascade_index_migration()

# Foreign key child columns that a pipeline run deletion cascades along. SQLite
# does not index foreign keys by itself and scans the child table once per
# deleted parent row without an index, which made deleting a run cost time
# proportional to the size of the whole store. The tests below hold this list
# against both paths into the schema -- the `__table_args__` declarations a
# fresh store is built from, and the migration an existing store is upgraded
# with -- so a column indexed in only one of them cannot pass.
CASCADE_INDEXES: List[Tuple[str, str]] = [
    ("step_run", "pipeline_run_id"),
    ("step_run", "original_step_run_id"),
    ("step_run_input_artifact", "step_id"),
    ("step_run_parents", "child_id"),
    ("logs", "pipeline_run_id"),
    ("logs", "step_run_id"),
    ("hook_invocation", "pipeline_run_id"),
    ("hook_invocation", "step_run_id"),
    ("run_metadata", "publisher_step_id"),
    ("run_metadata_resource", "run_metadata_id"),
    ("model_versions_runs", "pipeline_run_id"),
    ("service", "pipeline_run_id"),
    ("trigger_execution", "pipeline_run_id"),
    ("pipeline_run", "root_run_id"),
    ("pipeline_run", "original_run_id"),
]


def index_name(table_name: str, column_name: str) -> str:
    """Build the name of a single column index.

    Args:
        table_name: Table holding the column.
        column_name: The indexed column.

    Returns:
        The index name, matching `build_index` and the migration.
    """
    return f"ix_{table_name}_{column_name}"


def test_migration_covers_every_cascade_index() -> None:
    """Test that the migration indexes the same columns as the schema.

    An index declared in only one of the two places leaves new and upgraded
    stores with different schemas, and the store that is missing it keeps
    scanning the table on every run deletion.
    """
    assert MIGRATION.INDEXED_COLUMNS == CASCADE_INDEXES


def test_sqlite_store_uses_wal_journal_mode(sql_store: SqlZenStore) -> None:
    """Test that a local store is created in WAL mode.

    In the default rollback journal mode a write transaction blocks all
    readers for its duration, which makes a long delete lock out every other
    client of the store.

    Args:
        sql_store: The store to check.
    """
    with sql_store.engine.connect() as connection:
        journal_mode = connection.exec_driver_sql(
            "PRAGMA journal_mode"
        ).scalar()

        assert journal_mode is not None
        assert journal_mode.lower() == "wal"


def test_sqlite_connections_relax_synchronous_under_wal(
    sql_store: SqlZenStore,
) -> None:
    """Test that WAL mode is paired with `synchronous=NORMAL`.

    Skipping the fsync on every commit is what makes WAL fast. It is only safe
    because in WAL mode a power loss can cost the most recent commits but
    cannot corrupt the database, so it must not be set unless WAL is in use.

    Args:
        sql_store: The store to check.
    """
    with sql_store.engine.connect() as connection:
        journal_mode = connection.exec_driver_sql(
            "PRAGMA journal_mode"
        ).scalar()
        synchronous = connection.exec_driver_sql("PRAGMA synchronous").scalar()
        foreign_keys = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar()

    assert journal_mode is not None and journal_mode.lower() == "wal"
    # 1 is NORMAL, the default of 2 is FULL.
    assert synchronous == 1
    # Enabling `synchronous` must not have displaced the foreign key pragma,
    # which is what makes the database perform the cascade at all.
    assert foreign_keys == 1


@pytest.mark.parametrize(
    "table_name,column_name",
    CASCADE_INDEXES,
    ids=[f"{table}.{column}" for table, column in CASCADE_INDEXES],
)
def test_run_cascade_foreign_key_is_indexed(
    sql_store: SqlZenStore, table_name: str, column_name: str
) -> None:
    """Test that the cascade can find child rows without a table scan.

    A fresh store is built from the schema declarations rather than by replaying
    the migrations, so this covers the `__table_args__` half of the change.

    Args:
        sql_store: The store to check.
        table_name: Table holding the foreign key.
        column_name: The foreign key column.
    """
    with sql_store.engine.connect() as connection:
        plan = connection.exec_driver_sql(
            f"EXPLAIN QUERY PLAN "  # noqa: S608
            f"SELECT 1 FROM `{table_name}` WHERE `{column_name}` = 'x'"
        ).fetchall()

    detail = plan[0][-1]
    assert detail.strip().startswith("SEARCH"), (
        f"{table_name}.{column_name} is not indexed, so deleting a pipeline "
        f"run scans `{table_name}`: {detail}"
    )


@pytest.mark.parametrize(
    "existing_indexes",
    [set(), {"ix_pipeline_run_root_run_id"}],
    ids=["never_migrated", "migrated_through_c2f8d07a91b4"],
)
def test_migration_creates_every_cascade_index(
    tmp_path: Path, existing_indexes: Set[str]
) -> None:
    """Test that upgrading a database reaches the same indexes as a fresh one.

    Covers the migration half of the change, which the test above cannot: a
    store created by `create_all` is stamped at head and never replays the
    migrations. The two parameters are the two shapes an existing database
    comes in, and they disagree about `ix_pipeline_run_root_run_id`.
    `c2f8d07a91b4` creates it, so a database old enough to have run that
    migration has it, while one created from the schema afterwards does not,
    because `PipelineRunSchema` did not declare it until this revision. Both
    have to end up fully indexed.

    Args:
        tmp_path: Directory to hold the database.
        existing_indexes: Cascade indexes the database has before the upgrade.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'upgrade.db'}")
    SQLModel.metadata.create_all(engine)

    with engine.begin() as connection:
        for table_name, column_name in CASCADE_INDEXES:
            name = index_name(table_name, column_name)
            if name not in existing_indexes:
                connection.exec_driver_sql(f"DROP INDEX `{name}`")

    alembic = Alembic(engine)
    alembic.stamp(MIGRATION.down_revision)
    alembic.upgrade(MIGRATION.revision)

    inspector = inspect(engine)
    missing = [
        index_name(table_name, column_name)
        for table_name, column_name in CASCADE_INDEXES
        if index_name(table_name, column_name)
        not in {index["name"] for index in inspector.get_indexes(table_name)}
    ]

    assert not missing, (
        f"the upgrade left an upgraded store without {missing}, so deleting a "
        f"pipeline run there still scans those tables"
    )
