#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for explicit execution archive authority changes."""

from pathlib import Path

import pytest
from sqlmodel import Session, col, select

from tests.unit.zen_stores.execution_archive.service import (
    authority,
    exporter,
)
from tests.unit.zen_stores.execution_archive.utils import populate_family
from zenml.enums import ExecutionArchiveState, ExecutionStatus
from zenml.exceptions import (
    ArchiveUnavailableError,
    ExecutionArchiveParityError,
    ExecutionArchiveRestoreRequiredError,
    ExecutionArchiveStateError,
    IllegalOperationError,
)
from zenml.models import (
    PipelineRunUpdate,
    PipelineSnapshotUpdate,
    StepRunUpdate,
)
from zenml.zen_stores.execution_archive.capture import ExecutionArchiveCapturer
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.payload_mover import (
    ExecutionArchivePayloadMover,
)
from zenml.zen_stores.execution_archive_utils import archived_payload_id
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_compact_and_restore_round_trip(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Compaction is explicit, bounded, fail-closed, and reversible."""
    family = populate_family(sql_store, steps=3, with_projection=False)
    original = ExecutionArchiveCapturer(sql_store.engine).capture(
        project_id=family.project_id, root_run_id=family.run_id
    )
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    cold = authority(sql_store, tmp_path).compact(
        archive_id=archive.id, project_id=family.project_id
    )

    assert cold.state == ExecutionArchiveState.COLD
    assert cold.requires_restore
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, family.run_id)
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        step = session.get(StepRunSchema, family.step_id)
        configuration = session.exec(
            select(StepConfigurationSchema).where(
                col(StepConfigurationSchema.snapshot_id) == family.snapshot_id
            )
        ).first()
        assert run is not None and run.execution_archive_id == archive.id
        assert snapshot is not None
        assert snapshot.execution_archive_id == archive.id
        assert step is not None and step.substitutions is not None
        assert configuration is not None
        for value in (
            run.orchestrator_environment,
            snapshot.pipeline_configuration,
            step.source_code,
            configuration.config,
        ):
            assert archived_payload_id(value) == archive.id

    assert sql_store.get_run(family.run_id, hydrate=False).metadata is None
    assert (
        sql_store.get_run_step(family.step_id, hydrate=False).metadata is None
    )
    with pytest.raises(ExecutionArchiveRestoreRequiredError):
        sql_store.get_run(family.run_id)
    with pytest.raises(ExecutionArchiveRestoreRequiredError):
        sql_store.get_run_step(family.step_id)

    restored = authority(sql_store, tmp_path).restore(
        archive_id=archive.id, project_id=family.project_id
    )

    assert restored.state == ExecutionArchiveState.RESTORED
    assert not restored.requires_restore
    recaptured = ExecutionArchiveCapturer(sql_store.engine).capture(
        project_id=family.project_id, root_run_id=family.run_id
    )
    assert recaptured.source_fingerprint == original.source_fingerprint
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, family.run_id)
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert run is not None and run.execution_archive_id is None
        assert snapshot is not None and snapshot.execution_archive_id is None


def test_compaction_requires_the_deployment_gate(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Verified export remains non-destructive while compaction is disabled."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    with pytest.raises(ExecutionArchiveStateError, match="disabled"):
        authority(sql_store, tmp_path, compaction_enabled=False).compact(
            archive_id=archive.id, project_id=family.project_id
        )

    assert (
        ExecutionArchiveCatalog(sql_store.engine).require(archive.id).state
        == ExecutionArchiveState.VERIFIED
    )
    assert sql_store.get_run(family.run_id).id == family.run_id


def test_interrupted_compaction_resumes_after_the_gate_is_disabled(
    sql_store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Turning off new compaction never strands authoritative SQL payload."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    def interrupt(
        mover: ExecutionArchivePayloadMover, *args: object, **kwargs: object
    ) -> None:
        del mover, args, kwargs
        raise RuntimeError("interrupted after authority moved")

    with monkeypatch.context() as context:
        context.setattr(ExecutionArchivePayloadMover, "compact", interrupt)
        with pytest.raises(RuntimeError, match="interrupted"):
            authority(sql_store, tmp_path).compact(
                archive_id=archive.id, project_id=family.project_id
            )

    assert (
        ExecutionArchiveCatalog(sql_store.engine).require(archive.id).state
        == ExecutionArchiveState.COMPACTING
    )
    resumed = authority(sql_store, tmp_path, compaction_enabled=False).compact(
        archive_id=archive.id, project_id=family.project_id
    )
    assert resumed.state == ExecutionArchiveState.COLD


def test_compaction_refuses_sql_changed_after_verification(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """The locked authority switch never trusts a stale verified object."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None
        snapshot.source_code = 'print("changed after verification")'
        session.add(snapshot)
        session.commit()

    with pytest.raises(ExecutionArchiveParityError, match="changed"):
        authority(sql_store, tmp_path).compact(
            archive_id=archive.id, project_id=family.project_id
        )

    failed = ExecutionArchiveCatalog(sql_store.engine).require(archive.id)
    assert failed.state == ExecutionArchiveState.FAILED
    assert not failed.requires_restore
    assert sql_store.get_run(family.run_id).id == family.run_id


def test_cold_corruption_keeps_restore_required(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A damaged authoritative object never makes incomplete SQL readable."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    service = authority(sql_store, tmp_path)
    service.compact(archive_id=archive.id, project_id=family.project_id)
    Path(
        ExecutionArchiveCatalog(sql_store.engine).object_key(archive.id)
    ).write_bytes(b"corrupt")

    with pytest.raises(ArchiveUnavailableError, match="corrupt"):
        service.restore(archive_id=archive.id, project_id=family.project_id)

    failed = ExecutionArchiveCatalog(sql_store.engine).require(archive.id)
    assert failed.state == ExecutionArchiveState.CORRUPT
    assert failed.requires_restore
    with pytest.raises(ExecutionArchiveRestoreRequiredError):
        sql_store.get_run(family.run_id)


def test_cold_execution_writes_are_fenced_until_restore(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Run, step, and snapshot mutations cannot cross archive authority."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    service = authority(sql_store, tmp_path)
    service.compact(archive_id=archive.id, project_id=family.project_id)

    with pytest.raises(IllegalOperationError, match="Restore"):
        sql_store.update_snapshot(
            family.snapshot_id,
            PipelineSnapshotUpdate(description="changed"),
        )
    with pytest.raises(IllegalOperationError, match="Restore"):
        sql_store.update_run(
            family.run_id,
            PipelineRunUpdate(status=ExecutionStatus.COMPLETED),
        )
    with pytest.raises(IllegalOperationError, match="Restore"):
        sql_store.update_run_step(
            family.step_id,
            StepRunUpdate(status=ExecutionStatus.COMPLETED),
        )
    with pytest.raises(IllegalOperationError, match="Restore"):
        sql_store.delete_run(family.run_id)
    with pytest.raises(IllegalOperationError, match="Restore"):
        sql_store.delete_snapshot(family.snapshot_id)

    service.restore(archive_id=archive.id, project_id=family.project_id)
    updated = sql_store.update_snapshot(
        family.snapshot_id,
        PipelineSnapshotUpdate(description="changed"),
    )
    assert updated.metadata is not None
    assert updated.metadata.description == "changed"


def test_restore_skips_rows_deleted_while_cold(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """User-deleted rows do not strand restoration or its family markers."""
    family = populate_family(sql_store, steps=2)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    service = authority(sql_store, tmp_path)
    service.compact(archive_id=archive.id, project_id=family.project_id)
    with Session(sql_store.engine) as session:
        step = session.get(StepRunSchema, family.step_id)
        assert step is not None
        session.delete(step)
        session.commit()

    restored = service.restore(
        archive_id=archive.id, project_id=family.project_id
    )

    assert restored.state == ExecutionArchiveState.RESTORED
    with Session(sql_store.engine) as session:
        assert session.get(StepRunSchema, family.step_id) is None
        run = session.get(PipelineRunSchema, family.run_id)
        assert run is not None and run.execution_archive_id is None
