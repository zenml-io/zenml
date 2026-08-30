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
"""Tests for non-destructive execution archive export."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from tests.unit.zen_stores.execution_archive.service import (
    CallbackStorage,
    exporter,
    local_storage,
)
from tests.unit.zen_stores.execution_archive.utils import (
    OLD,
    populate_family,
)
from zenml.enums import ExecutionArchiveState, ExecutionStatus
from zenml.exceptions import (
    ArchiveUnavailableError,
    ExecutionArchiveNotEligibleError,
    ExecutionArchiveParityError,
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapturer,
)
from zenml.zen_stores.execution_archive.catalog import (
    ExecutionArchiveCatalog,
)
from zenml.zen_stores.execution_archive.codec import decompress
from zenml.zen_stores.execution_archive.payload import ExecutionArchivePayload
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _archive_row(store: SqlZenStore) -> ExecutionArchiveSchema:
    with Session(store.engine) as session:
        return session.exec(
            select(ExecutionArchiveSchema).order_by(
                ExecutionArchiveSchema.generation.desc()
            )
        ).one()


def test_export_writes_one_verified_object_and_keeps_sql_authoritative(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A retry verifies the same generation and keeps SQL authoritative."""
    family = populate_family(sql_store, steps=2)
    service = exporter(sql_store, tmp_path)

    first = service.export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    catalog = ExecutionArchiveCatalog(sql_store.engine)
    committed_key = Path(catalog.object_key(first.id))
    obsolete_attempt = committed_key.parent / "999.json.gz"
    unrelated_object = committed_key.parent / "manifest.json"
    obsolete_attempt.write_bytes(b"obsolete")
    unrelated_object.write_bytes(b"unrelated")

    second = service.export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    assert first.id == second.id
    assert not obsolete_attempt.exists()
    assert unrelated_object.exists()
    assert second.state == ExecutionArchiveState.VERIFIED
    assert second.object is not None
    assert second.object.stored_bytes < second.object.decoded_bytes
    [listed] = catalog.list(
        project_id=family.project_id, state=ExecutionArchiveState.VERIFIED
    )
    assert listed == second
    assert catalog.get(second.id, project_id=family.project_id) == second

    encoded = Path(catalog.object_key(second.id)).read_bytes()
    payload = ExecutionArchivePayload.model_validate_json(decompress(encoded))
    assert payload.archive_id == second.id
    assert {run.id for run in payload.runs} == {family.run_id}
    assert {step.id for step in payload.steps} == set(family.step_ids)
    assert {snapshot.id for snapshot in payload.snapshots} == {
        family.snapshot_id
    }

    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, family.run_id)
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert run is not None and run.execution_archive_id is None
        assert snapshot is not None
        assert snapshot.execution_archive_id is None
        assert snapshot.source_code == 'print("pipeline")'


def test_source_change_during_export_fails_and_uses_a_new_generation(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A changed SQL source never becomes a verified archive."""
    family = populate_family(sql_store)
    storage = local_storage(sql_store, tmp_path)

    def mutate() -> None:
        with Session(sql_store.engine) as session:
            snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
            assert snapshot is not None
            snapshot.source_code = 'print("changed")'
            snapshot.updated = OLD
            session.add(snapshot)
            session.commit()

    service = exporter(
        sql_store,
        tmp_path,
        storage=CallbackStorage(storage, mutate),
    )
    with pytest.raises(ExecutionArchiveParityError):
        service.export(project_id=family.project_id, root_run_id=family.run_id)
    assert _archive_row(sql_store).state == ExecutionArchiveState.FAILED.value
    assert not list(tmp_path.rglob("*.json.gz"))

    retried = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    assert retried.state == ExecutionArchiveState.VERIFIED
    assert retried.generation == 2
    with Session(sql_store.engine) as session:
        generations = session.exec(
            select(ExecutionArchiveSchema).order_by(
                ExecutionArchiveSchema.generation
            )
        ).all()
        assert generations[0].purge_pending_at is not None
        assert generations[1].purge_pending_at is None


def test_corrupt_verified_object_is_detected_and_recorded(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A checksum failure is durable and SQL remains authoritative."""
    family = populate_family(sql_store)
    service = exporter(sql_store, tmp_path)
    archive = service.export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    Path(
        ExecutionArchiveCatalog(sql_store.engine).object_key(archive.id)
    ).write_bytes(b"corrupt")

    with pytest.raises(ArchiveUnavailableError, match="corrupt"):
        service.export(project_id=family.project_id, root_run_id=family.run_id)
    assert _archive_row(sql_store).state == ExecutionArchiveState.CORRUPT.value
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None
        assert snapshot.source_code == 'print("pipeline")'


def test_corrupt_compacted_generation_must_be_restored_before_export(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A corrupt cold generation cannot be replaced from incomplete SQL."""
    family = populate_family(sql_store)
    service = exporter(sql_store, tmp_path)
    archive = service.export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    with Session(sql_store.engine) as session:
        row = session.get(ExecutionArchiveSchema, archive.id)
        assert row is not None
        row.state = ExecutionArchiveState.CORRUPT.value
        row.compacted_at = OLD
        session.add(row)
        session.commit()

    with pytest.raises(ExecutionArchiveStateError, match="restore"):
        service.export(project_id=family.project_id, root_run_id=family.run_id)


def test_fencing_token_rejects_an_expired_worker(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Only the newest claimant can mutate a generation."""
    family = populate_family(sql_store)
    capture = ExecutionArchiveCapturer(sql_store.engine).capture(
        project_id=family.project_id, root_run_id=family.run_id
    )
    storage = local_storage(sql_store, tmp_path)
    catalog = ExecutionArchiveCatalog(sql_store.engine)
    first = catalog.start_export(
        project_id=family.project_id,
        root_run_id=family.run_id,
        source_fingerprint=capture.source_fingerprint,
        source_updated_at=capture.family.latest_mutation,
        storage_target_digest=storage.target_digest,
        source_bytes=capture.family.source_bytes,
        owner="worker-a",
        lease_seconds=600,
    )
    with Session(sql_store.engine) as session:
        row = session.get(ExecutionArchiveSchema, first.archive_id)
        assert row is not None
        row.owner_expires_at = OLD
        session.add(row)
        session.commit()
    second = catalog.start_export(
        project_id=family.project_id,
        root_run_id=family.run_id,
        source_fingerprint=capture.source_fingerprint,
        source_updated_at=capture.family.latest_mutation,
        storage_target_digest=storage.target_digest,
        source_bytes=capture.family.source_bytes,
        owner="worker-b",
        lease_seconds=600,
    )

    assert second.token > first.token
    with pytest.raises(ExecutionArchiveStateError, match="newer worker"):
        catalog.record_error(first, "stale")
    assert not catalog.try_record_failure(first, RuntimeError("stale"))
    recorded = catalog.record_error(second, "x" * 5000)
    assert recorded.last_error is not None
    assert len(recorded.last_error) == 4096
    catalog.release(second)
    with Session(sql_store.engine) as session:
        row = session.get(ExecutionArchiveSchema, second.archive_id)
        assert row is not None
        session.delete(row)
        session.commit()
    catalog.release(second)


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.RUNNING,
        ExecutionStatus.FAILED,
        ExecutionStatus.STOPPED,
        ExecutionStatus.CANCELLED,
    ],
)
def test_noncompleted_pipeline_run_is_rejected(
    sql_store: SqlZenStore, tmp_path: Path, status: ExecutionStatus
) -> None:
    """Only successfully completed pipeline runs can become cold."""
    family = populate_family(sql_store)
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, family.run_id)
        assert run is not None
        run.status = status.value
        session.add(run)
        session.commit()

    with pytest.raises(
        ExecutionArchiveNotEligibleError, match="completed successfully"
    ):
        exporter(sql_store, tmp_path).export(
            project_id=family.project_id, root_run_id=family.run_id
        )
    with Session(sql_store.engine) as session:
        assert session.exec(select(ExecutionArchiveSchema)).first() is None


def test_finished_step_outcomes_remain_exportable(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Cached, skipped, and retried steps are valid completed history."""
    family = populate_family(sql_store, steps=3)
    statuses = (
        ExecutionStatus.CACHED,
        ExecutionStatus.SKIPPED,
        ExecutionStatus.RETRIED,
    )
    with Session(sql_store.engine) as session:
        for step_id, status in zip(family.step_ids, statuses):
            step = session.get(StepRunSchema, step_id)
            assert step is not None
            step.status = status.value
            session.add(step)
        session.commit()

    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    assert archive.state == ExecutionArchiveState.VERIFIED


def test_family_row_limit_blocks_capture_before_loading_the_closure(
    sql_store: SqlZenStore,
) -> None:
    """Many tiny rows cannot bypass the archive memory bound."""
    family = populate_family(sql_store, steps=2)
    capturer = ExecutionArchiveCapturer(sql_store.engine, max_rows=2)

    with pytest.raises(ExecutionArchiveNotEligibleError, match="row archive"):
        capturer.inspect(
            project_id=family.project_id, root_run_id=family.run_id
        )
    with pytest.raises(ExecutionArchiveNotEligibleError, match="row archive"):
        capturer.capture(
            project_id=family.project_id, root_run_id=family.run_id
        )


def test_external_snapshot_reference_blocks_archiving(
    sql_store: SqlZenStore,
) -> None:
    """A shared snapshot is detected without loading every reference."""
    family = populate_family(sql_store, suffix="-owned")
    other = populate_family(sql_store, suffix="-external")
    with Session(sql_store.engine) as session:
        external_run = session.get(PipelineRunSchema, other.run_id)
        assert external_run is not None
        external_run.snapshot_id = family.snapshot_id
        session.add(external_run)
        session.commit()

    inspected = ExecutionArchiveCapturer(sql_store.engine).inspect(
        project_id=family.project_id, root_run_id=family.run_id
    )

    assert "a snapshot is shared outside the execution tree" in (
        inspected.blockers
    )


def test_export_catalog_refuses_a_deleted_project(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A generation cannot appear after project purge was queued."""
    storage = local_storage(sql_store, tmp_path)

    with pytest.raises(ExecutionArchiveStateError, match="no longer exists"):
        ExecutionArchiveCatalog(sql_store.engine).start_export(
            project_id=uuid4(),
            root_run_id=uuid4(),
            source_fingerprint="0" * 64,
            source_updated_at=OLD,
            storage_target_digest=storage.target_digest,
            source_bytes=1,
            owner="late-exporter",
            lease_seconds=60,
        )
