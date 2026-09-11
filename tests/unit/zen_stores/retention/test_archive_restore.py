# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive and restore round trips, races, atomicity, and pass progress."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import timedelta
from pathlib import Path
from threading import Event, current_thread
from uuid import UUID

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from tests.unit.zen_stores.retention.fixture_graph import (
    dynamic_step,
    insert_rows,
)
from tests.unit.zen_stores.retention.fixture_graph import (
    read_tables as rows,
)
from zenml.enums import (
    ExecutionStatus,
    RestoreOutcome,
    RetentionOutcome,
)
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
)
from zenml.models import (
    PipelineRunRequest,
    PipelineRunUpdate,
    ProjectUpdate,
    StepRunFilter,
)
from zenml.models.v2.misc.exception_info import ExceptionInfo
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.retention import archiver, fences
from zenml.zen_stores.retention.state import RetentionState
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    ProjectSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def saved_state(store: SqlZenStore, project_id: UUID) -> RetentionState:
    """Read a project's saved pass state.

    Args:
        store: Metadata store.
        project_id: Project.

    Returns:
        The saved state.
    """
    with Session(store.engine) as session:
        project = session.get(ProjectSchema, project_id)
        assert project is not None
        return RetentionState.load(project.retention_state)


def stored_objects(storage) -> list:
    """List archive object names below the storage root.

    Args:
        storage: Archive storage over a local directory.

    Returns:
        Names of the stored archive objects.
    """
    return sorted(path.name for path in Path(storage.root).rglob("*.json.gz"))


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_archive_restore_round_trip(
    retention_store, kind, run_factory, archive_run, storage
):
    """Restore recovers every SQL payload and the original detailed responses."""
    ids = run_factory(retention_store, kind)
    calls = [
        lambda: retention_store.get_run(ids.run),
        lambda: retention_store.get_run_step(ids.consumer),
        lambda: retention_store.get_snapshot(ids.snapshot),
        lambda: retention_store.get_pipeline_run_dag(ids.run),
        lambda: retention_store.list_run_steps(
            StepRunFilter(pipeline_run_id=ids.run), hydrate=True
        ),
    ]
    before = [call().model_dump() for call in calls]
    sql_before = rows(retention_store)
    bundle_id = archive_run(retention_store, ids)
    with Session(retention_store.engine) as session:
        run = session.get(PipelineRunSchema, ids.run)
        step = session.get(StepRunSchema, ids.consumer)
        assert run.orchestrator_environment is None
        assert step.step_configuration is None and step.exception_info is None
        assert step.archive_bundle_id == bundle_id
        bundle = session.get(ArchiveBundleSchema, bundle_id)
        assert bundle.run_id == ids.run and bundle.restored_at is None
    assert rows(retention_store)["step_configuration"] == []
    assert storage.read(bundle.uri, bundle.size_bytes)
    header = retention_store.get_run_step(
        ids.consumer, hydrate=False
    ).get_body()
    assert header.type == before[1]["body"]["type"]
    assert header.substitutions == before[1]["body"]["substitutions"]
    with pytest.raises(ExecutionArchivedError):
        retention_store.get_run(ids.run)

    restored = retention_store.restore_pipeline_run(ids.run)

    assert restored.outcome == RestoreOutcome.RESTORED
    assert restored.restored_at is not None
    assert [call().model_dump() for call in calls] == before
    sql_after = rows(retention_store)
    # These new columns are derived header projections, not archived payload.
    for source in (sql_before, sql_after):
        for step in source["step_run"]:
            step.pop("step_type")
            step.pop("substitutions")
    assert sql_after == sql_before
    with Session(retention_store.engine) as session:
        assert session.get(ArchiveBundleSchema, bundle_id).restored_at


def test_update_after_retirement_fails_with_the_restore_command(
    retention_store, run_factory, storage, monkeypatch
):
    """A write waiting on retirement's lock sees the marker and fails."""
    ids = run_factory(retention_store)
    locked, release = Event(), Event()
    original = archiver._clear_detail

    def pause_before_clearing(*args, **kwargs):
        locked.set()
        assert release.wait(20)
        return original(*args, **kwargs)

    monkeypatch.setattr(archiver, "_clear_detail", pause_before_clearing)
    with (
        ThreadPoolExecutor(1, thread_name_prefix="archive") as archivers,
        ThreadPoolExecutor(1, thread_name_prefix="writer") as writers,
    ):
        archive = archivers.submit(
            retention_store.archive_project, ids.project
        )
        assert locked.wait(20)
        writer = writers.submit(
            retention_store.update_run,
            ids.run,
            PipelineRunUpdate(exception_info=ExceptionInfo(traceback="late")),
        )
        try:
            with pytest.raises(FutureTimeout):
                writer.result(timeout=1)
        finally:
            release.set()
        assert archive.result(timeout=20).outcome == RetentionOutcome.SUCCEEDED
        with pytest.raises(
            ExecutionArchivedError, match="pipeline runs restore"
        ):
            writer.result(timeout=20)


def test_losing_pass_removes_its_object(
    retention_store, run_factory, storage, monkeypatch, NOW
):
    """Two passes racing on one run leave one bundle and one object."""
    ids = run_factory(retention_store)
    uploaded, release = Event(), Event()
    original = storage.write

    def pause_after_upload(uri, data):
        original(uri, data)
        if current_thread().name.startswith("stale") and uri.endswith(
            ".json.gz"
        ):
            uploaded.set()
            assert release.wait(20)

    monkeypatch.setattr(storage, "write", pause_after_upload)
    with ThreadPoolExecutor(1, thread_name_prefix="stale") as pool:
        stale = pool.submit(retention_store.archive_project, ids.project)
        try:
            assert uploaded.wait(20)
            with Session(retention_store.engine) as session:
                project = session.get(ProjectSchema, ids.project)
                state = RetentionState.load(project.retention_state)
                state.operation_expires_at = NOW - timedelta(seconds=1)
                project.retention_state = state.model_dump_json()
                session.add(project)
                session.commit()
            assert (
                retention_store.get_retention_status(ids.project).outcome
                == RetentionOutcome.EXPIRED
            )
            winner = retention_store.archive_project(ids.project)
            assert winner.outcome == RetentionOutcome.SUCCEEDED
        finally:
            release.set()
        stale.result(timeout=20)

    with Session(retention_store.engine) as session:
        bundles = session.scalars(
            select(ArchiveBundleSchema).where(
                ArchiveBundleSchema.run_id == ids.run
            )
        ).all()
    state = saved_state(retention_store, ids.project)
    assert state.last_outcome == RetentionOutcome.SUCCEEDED
    assert state.archived == 1
    assert len(bundles) == 1
    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        == bundles[0].id
    )
    assert stored_objects(storage) == [f"{bundles[0].id}.json.gz"]


@pytest.mark.parametrize("failure", ["upload", "retirement", "commit_ack"])
def test_interrupted_retirement(
    retention_store, run_factory, storage, monkeypatch, failure
):
    """A failed commit changes nothing; a lost acknowledgement keeps the object."""
    ids = run_factory(retention_store)
    before = (
        rows(retention_store),
        retention_store.get_run(ids.run).model_dump(),
    )
    inserted = False
    original_commit = retention_store.engine.dialect.do_commit
    original_write = storage.write

    def write(uri, data):
        if failure == "upload" and uri.endswith(".json.gz"):
            data += b"x"
        original_write(uri, data)

    def observe(conn, cursor, statement, parameters, context, many):
        nonlocal inserted
        if failure == "retirement" and statement.startswith(
            "DELETE FROM step_configuration"
        ):
            raise OSError("retirement interrupted")
        if statement.startswith("INSERT INTO archive_bundle"):
            inserted = True

    def commit(connection):
        nonlocal inserted
        original_commit(connection)
        if inserted and failure == "commit_ack":
            inserted = False
            raise OSError("acknowledgement lost")

    event.listen(retention_store.engine, "before_cursor_execute", observe)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(retention_store.engine.dialect, "do_commit", commit)
            patch.setattr(storage, "write", write)
            outcome = retention_store.archive_project(ids.project)
    finally:
        event.remove(retention_store.engine, "before_cursor_execute", observe)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    state = saved_state(retention_store, ids.project)
    if failure != "commit_ack":
        assert state.failed == 1
        assert rows(retention_store) == before[0]
        assert stored_objects(storage) == []
    else:
        assert state.archived == 1
        restored = retention_store.restore_pipeline_run(ids.run)
        assert restored.outcome == RestoreOutcome.RESTORED
        assert retention_store.get_run(ids.run).model_dump() == before[1]


def test_pass_continues_from_its_saved_position(
    retention_store, run_factory, storage
):
    """Each pass examines the next runs, including excluded ones."""
    runs = [
        run_factory(retention_store, age_days=100 - index)
        for index in range(3)
    ]
    project = runs[0].project
    with Session(retention_store.engine) as session:
        # A run still marked running stays in SQL but is examined.
        oldest = session.get(PipelineRunSchema, runs[0].run)
        oldest.status = ExecutionStatus.RUNNING.value
        session.add(oldest)
        session.commit()
    retention_store.update_project(
        project,
        ProjectUpdate(
            retention=RetentionSettings(
                archive_after_days=7, max_runs_per_pass=1
            )
        ),
    )

    first = retention_store.archive_project(project)
    assert first.outcome == RetentionOutcome.PAUSED
    assert saved_state(retention_store, project).skipped == 1
    second = retention_store.archive_project(project)
    assert second.outcome == RetentionOutcome.PAUSED
    third = retention_store.archive_project(project)
    assert third.outcome == RetentionOutcome.SUCCEEDED

    archived = [
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        for ids in runs
    ]
    assert archived[0] is None and all(archived[1:])
    assert saved_state(retention_store, project).cursor is None


def test_archived_snapshot_is_deleted_only_after_its_run(
    retention_store, run_factory, archive_run, storage
):
    """Deleting a run keeps its object; its snapshot is then deletable."""
    ids = run_factory(retention_store)
    bundle_id = archive_run(retention_store, ids)
    with pytest.raises(ExecutionArchivedError, match=str(ids.run)):
        retention_store.delete_snapshot(ids.snapshot)

    retention_store.delete_run(ids.run)

    with Session(retention_store.engine) as session:
        bundle = session.get(ArchiveBundleSchema, bundle_id)
        assert bundle.run_id is None
    assert storage.read(bundle.uri, bundle.size_bytes)
    assert retention_store.get_snapshot(
        ids.snapshot, hydrate=False
    ).archive_bundle_id
    retention_store.delete_snapshot(ids.snapshot)


@pytest.mark.parametrize("writer_kind", ["step", "update", "snapshot"])
def test_writer_racing_archive_preserves_committed_detail(
    retention_store, run_factory, storage, monkeypatch, NOW, writer_kind
):
    """Retirement waits for writers, then detects changed payload or ownership."""
    ids = run_factory(retention_store, "dynamic")
    entered, release = Event(), Event()
    hook = {
        "step": "protect_run",
        "update": "update_hot",
        "snapshot": "protect_snapshot_owners",
    }[writer_kind]
    original = getattr(fences, hook)
    calls = 0

    def pause_after_lock(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        if current_thread().name.startswith("writer"):
            calls += 1
            # Snapshot creation commits its index allocation before locking again.
            if calls == (2 if writer_kind == "snapshot" else 1):
                entered.set()
                assert release.wait(20)
        return result

    monkeypatch.setattr(fences, hook, pause_after_lock)
    writers = {
        "step": lambda: retention_store.create_run_step(
            dynamic_step(ids, "late", NOW)
        ),
        "update": lambda: retention_store.update_run(
            ids.run,
            PipelineRunUpdate(
                exception_info=ExceptionInfo(
                    traceback="late failure", message="late"
                )
            ),
        ),
        "snapshot": lambda: retention_store.get_or_create_run(
            PipelineRunRequest(
                project=ids.project,
                name="late",
                snapshot=ids.snapshot,
                status=ExecutionStatus.RUNNING,
            )
        ),
    }
    with (
        ThreadPoolExecutor(1, thread_name_prefix="writer") as pool,
        ThreadPoolExecutor(1) as archives,
    ):
        writer = pool.submit(writers[writer_kind])
        try:
            assert entered.wait(10)
            archive = archives.submit(
                retention_store.archive_project, ids.project
            )
            with pytest.raises(FutureTimeout):
                archive.result(timeout=0.5)
        finally:
            release.set()
        written = writer.result(timeout=20)
        archive.result(timeout=20)
    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        is None
    )
    retention_store.archive_project(ids.project)
    assert retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
    if writer_kind == "snapshot":
        assert (
            retention_store.get_snapshot(ids.snapshot).archive_bundle_id
            is None
        )
    retention_store.restore_pipeline_run(ids.run)
    if writer_kind == "step":
        assert retention_store.get_run_step(written.id).config.name == "late"
    elif writer_kind == "update":
        assert (
            retention_store.get_run(ids.run).exception_info.message == "late"
        )


@pytest.mark.parametrize("failure", ["occupied", "insert"])
def test_restore_conflict_rolls_back_all_detail(
    retention_store, run_factory, archive_run, monkeypatch, failure
):
    """Ownership conflicts and failures after payload updates leave SQL unchanged."""
    ids = run_factory(retention_store, "dynamic")
    original = rows(retention_store)["step_configuration"][0]
    archive_run(retention_store, ids)
    if failure == "occupied":
        insert_rows(retention_store, {"step_configuration": [original]})
    before = rows(retention_store)

    def fail_insert(conn, cursor, statement, parameters, context, many):
        if failure == "insert" and statement.startswith(
            "INSERT INTO step_configuration"
        ):
            raise IntegrityError(
                statement, None, RuntimeError("late insert failure")
            )

    event.listen(retention_store.engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(ExecutionRetentionConflictError):
            retention_store.restore_pipeline_run(ids.run)
    finally:
        event.remove(
            retention_store.engine, "before_cursor_execute", fail_insert
        )
    assert rows(retention_store) == before
