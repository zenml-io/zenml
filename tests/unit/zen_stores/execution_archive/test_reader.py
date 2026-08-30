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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests of the archive reader.

The reader is exercised on families made authoritative the way compaction
does it: the marker set and the placeholder written into every payload
column whose archived value is not empty.
"""

import threading
from pathlib import Path
from typing import Any, List, Tuple
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, col, select

from tests.unit.zen_stores.execution_archive.service import (
    FaultyStores,
    archiver,
)
from tests.unit.zen_stores.execution_archive.utils import (
    NOW,
    OLDER_THAN,
    Family,
    archive_row,
    count_statements,
    populate_family,
)
from zenml.config.step_configurations import Step
from zenml.enums import ExecutionArchiveState, ExecutionStatus
from zenml.exceptions import ArchiveUnavailableError, EntityExistsError
from zenml.models import (
    PipelineRunFilter,
    PipelineRunUpdate,
    PipelineSnapshotFilter,
    StepRunFilter,
    StepRunRequest,
    StepRunUpdate,
)
from zenml.zen_stores.execution_archive.cache import ExecutionArchiveCache
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.hydrator import (
    ExecutionArchiveHydrator,
)
from zenml.zen_stores.execution_archive.payload import (
    ARCHIVED_CONFIGURATION_FIELDS,
    ARCHIVED_PAYLOAD_PLACEHOLDER,
    ARCHIVED_RUN_FIELDS,
    ARCHIVED_SNAPSHOT_FIELDS,
    ARCHIVED_STEP_FIELDS,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

# Payload columns that are written once, at creation. `exception_info` and
# `orchestrator_environment` may legitimately be written later; a later
# value stays in SQL and wins over the archived one.
IMMUTABLE_PAYLOAD_COLUMNS = (
    "pipeline_configuration",
    "client_environment",
    "pipeline_spec",
    "source_code",
    "config",
    "docstring",
)


def _export(store: SqlZenStore, family: Family, stores=None):  # type: ignore[no-untyped-def]
    return archiver(store, stores).export(
        project_id=family.project_id,
        root_run_id=family.run_id,
        older_than=OLDER_THAN,
    )


def _read_family(store: SqlZenStore, family: Family) -> Any:
    return (
        store.get_run(family.run_id, hydrate=True).metadata,
        store.get_snapshot(family.snapshot_id, hydrate=True).metadata,
        store.get_run_step(family.step_id, hydrate=True).metadata,
        store.get_pipeline_run_dag(family.run_id),
    )


def _placeholder(row: Any, fields: Tuple[str, ...]) -> None:
    for field in fields:
        if getattr(row, field) is not None:
            setattr(row, field, ARCHIVED_PAYLOAD_PLACEHOLDER)


def _make_authoritative(store: SqlZenStore, family: Family) -> UUID:
    """Do what the authority switch and compaction do, directly in SQL.

    Args:
        store: The store.
        family: The exported family.

    Returns:
        The archive ID.
    """
    archive = archive_row(store)
    with Session(store.engine) as session:
        ExecutionArchiveCatalog.transition(
            session,
            archive.id,
            ExecutionArchiveState.COMPACTING,
            committed_at=NOW,
        )
        session.commit()
    with Session(store.engine) as session:
        ExecutionArchiveCatalog.transition(
            session, archive.id, ExecutionArchiveState.COLD, compacted_at=NOW
        )
        run = session.get(PipelineRunSchema, family.run_id)
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert run is not None and snapshot is not None
        _placeholder(run, ARCHIVED_RUN_FIELDS)
        _placeholder(snapshot, ARCHIVED_SNAPSHOT_FIELDS)
        snapshot.execution_archive_id = archive.id
        for step_id in family.step_ids:
            step = session.get(StepRunSchema, step_id)
            assert step is not None
            _placeholder(step, ARCHIVED_STEP_FIELDS)
        for configuration in session.exec(
            select(StepConfigurationSchema).where(
                col(StepConfigurationSchema.snapshot_id) == family.snapshot_id
            )
        ).all():
            _placeholder(configuration, ARCHIVED_CONFIGURATION_FIELDS)
            session.add(configuration)
        session.add_all([run, snapshot])
        session.commit()
    return archive.id


def test_reader_costs_nothing_for_hot_rows(sql_store: SqlZenStore) -> None:
    """Reads and writes of hot families do no archive work.

    No catalog query, no object read — and the pre-scan itself loads no
    relationship: an update of a hot step must not load every step
    configuration of its snapshot.
    """
    family = populate_family(sql_store, steps=3)
    stores = FaultyStores(sql_store)
    sql_store._execution_archive_hydrator = ExecutionArchiveHydrator(stores)

    with count_statements(sql_store, "FROM execution_archive") as statements:
        _read_family(sql_store, family)
        assert sql_store.list_run_steps(StepRunFilter(), hydrate=True).total
        sql_store.update_run(
            family.run_id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
        )
        sql_store.update_run_step(family.step_id, StepRunUpdate(end_time=NOW))
    assert statements == [] and stores.reads == 0

    # The pre-scan must not force a load of every configuration of the
    # snapshot: only targeted single-row lookups may touch the table.
    with count_statements(sql_store, "FROM step_configuration") as statements:
        sql_store.update_run_step(family.step_id, StepRunUpdate(end_time=NOW))
        sql_store.update_run(
            family.run_id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
        )
    # The classic regression is a full relationship load filtered only by
    # the snapshot: flag statements that name the snapshot column without
    # any narrower predicate.
    bulk = [
        statement
        for statement in statements
        if "step_configuration.snapshot_id" in statement
        and "step_configuration.name" not in statement
        and "step_configuration.step_run_id" not in statement
    ]
    assert bulk == []


def test_reader_serves_archived_rows_and_writers_keep_working(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Placeholders are filled from two object reads; writers stay whole."""
    family = populate_family(sql_store, steps=3)
    stores = FaultyStores(sql_store)
    sql_store._execution_archive_hydrator = ExecutionArchiveHydrator(stores)
    hot = _read_family(sql_store, family)

    _export(sql_store, family, stores)
    _make_authoritative(sql_store, family)
    stores.reads = 0
    assert _read_family(sql_store, family) == hot
    assert stores.reads == 2  # one execution and one snapshot object
    with count_statements(sql_store, "FROM execution_archive") as statements:
        assert sql_store.list_runs(PipelineRunFilter()).total == 1
        assert sql_store.list_snapshots(PipelineSnapshotFilter()).total == 1
        assert sql_store.list_run_steps(StepRunFilter()).total == 3
    assert statements == []

    # Updates of archived rows return real payload, never the placeholder.
    updated_run = sql_store.update_run(
        family.run_id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
    )
    assert updated_run.config and updated_run.config.name
    updated_step = sql_store.update_run_step(
        family.step_id, StepRunUpdate(end_time=NOW)
    )
    assert updated_step.source_code == 'print("step-0")'
    assert updated_step.docstring == "Docstring of step-0."
    assert ARCHIVED_PAYLOAD_PLACEHOLDER not in updated_step.model_dump_json()

    # A step that joined the family after the archive keeps its SQL payload.
    late_step_id = uuid4()
    with Session(sql_store.engine) as session:
        step = session.get(StepRunSchema, family.step_id)
        assert step is not None
        session.add(
            StepRunSchema(
                id=late_step_id,
                project_id=step.project_id,
                user_id=step.user_id,
                pipeline_run_id=step.pipeline_run_id,
                snapshot_id=step.snapshot_id,
                name="late-step",
                start_time=step.start_time,
                end_time=step.end_time,
                status=step.status,
                source_code='print("late")',
                docstring="Late docstring.",
                step_type=step.step_type,
                substitutions=step.substitutions,
                version=1,
                is_retriable=False,
                created=step.created,
                updated=step.updated,
            )
        )
        session.add(
            StepConfigurationSchema(
                snapshot_id=step.snapshot_id,
                step_run_id=None,
                index=3,
                name="late-step",
                config=Step.model_validate(
                    {
                        "spec": {
                            "source": "module.step_class",
                            "upstream_steps": [],
                            "inputs": {},
                        },
                        "config": {"name": "late-step"},
                    }
                ).model_dump_json(exclude={"config"}),
                created=step.created,
                updated=step.updated,
            )
        )
        session.commit()
    late = sql_store.get_run_step(late_step_id, hydrate=True)
    assert late.source_code == 'print("late")'
    assert late.docstring == "Late docstring."

    # Step creation reads the archived configuration instead of failing:
    # the only thing wrong with this request is what would be wrong on a
    # hot family too, the step already succeeded.
    with pytest.raises(EntityExistsError, match="already exists"):
        sql_store.create_run_step(
            StepRunRequest(
                name="step-0",
                start_time=NOW,
                status=ExecutionStatus.RUNNING,
                pipeline_run_id=family.run_id,
                project=family.project_id,
            )
        )

    # A checksum mismatch never yields a partially hydrated row.
    payload_file = next((tmp_path / "archive-primary").rglob("executions/*/*"))
    payload_file.write_bytes(b"corrupt")
    sql_store._execution_archive_hydrator = None
    with pytest.raises(ArchiveUnavailableError):
        sql_store.get_run(family.run_id, hydrate=True)


def test_writers_never_touch_payload_columns(sql_store: SqlZenStore) -> None:
    """Ordinary updates of runs and steps never write an immutable column."""
    family = populate_family(sql_store)

    with count_statements(sql_store, "UPDATE") as statements:
        sql_store.update_run(
            family.run_id, PipelineRunUpdate(status=ExecutionStatus.COMPLETED)
        )
        sql_store.update_run_step(family.step_id, StepRunUpdate(end_time=NOW))
    assert any("step_run" in statement for statement in statements)
    touched = [
        column
        for statement in statements
        for column in IMMUTABLE_PAYLOAD_COLUMNS
        if f"{column}=" in statement.replace(" ", "")
    ]
    assert touched == []


def test_cache_shares_loads_and_recovers_from_failures() -> None:
    """Concurrent readers share one load; a failing load leaves no trace."""
    cache: ExecutionArchiveCache[str] = ExecutionArchiveCache(1024)
    loads: List[int] = []
    gate = threading.Barrier(8)

    def loader() -> "tuple[str, int]":
        loads.append(1)
        return "value", 10

    def read() -> None:
        gate.wait()
        assert cache.get_or_load("digest", loader) == "value"

    workers = [threading.Thread(target=read) for _ in range(8)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert len(loads) == 1

    def failing() -> "tuple[str, int]":
        raise OSError("read failed")

    with pytest.raises(OSError):
        cache.get_or_load("other", failing)
    assert cache._loading == {}
    assert cache.get_or_load("other", loader) == "value"
