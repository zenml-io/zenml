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

from typing import List, Tuple

import pytest

from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
)

# Foreign key child columns that a pipeline run deletion cascades along. SQLite
# does not index foreign keys by itself and scans the child table once per
# deleted parent row without an index, which made deleting a run cost time
# proportional to the size of the whole store. Kept in sync with the
# `__table_args__` of the corresponding schemas and with the migration that
# adds them to existing databases.
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
    the migrations, so this also pins the two together: an index added to one
    and not the other would leave new and upgraded stores with different
    schemas.

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
