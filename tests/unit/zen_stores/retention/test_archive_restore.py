# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive and restore round trips, races, atomicity, and pass progress."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import contextmanager
from pathlib import Path
from threading import Event, current_thread
from uuid import uuid4

import pymysql
import pytest
from pydantic import ValidationError
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    delete,
    event,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from tests.unit.zen_stores.retention.fixture_graph import (
    dynamic_step,
    insert_rows,
)
from tests.unit.zen_stores.retention.fixture_graph import (
    read_tables as rows,
)
from zenml.client import Client
from zenml.config.server_config import ServerConfiguration
from zenml.enums import (
    ExecutionStatus,
    RestoreOutcome,
    RetentionExclusion,
)
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
    ExecutionRetentionOversizedError,
)
from zenml.models import (
    ArchiveRefusal,
    ArchiveRequest,
    PipelineRunRequest,
    PipelineRunUpdate,
    PipelineSnapshotUpdate,
    StepRunFilter,
    StepRunUpdate,
)
from zenml.models.v2.misc.exception_info import ExceptionInfo
from zenml.orchestrators import cache_utils
from zenml.zen_stores.retention import (
    archiver,
    capture,
    eligibility,
    fences,
)
from zenml.zen_stores.retention.eligibility import ArchivableRun
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    StepRunSchema,
)


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_archive_restore_round_trip(
    retention_store,
    kind,
    run_factory,
    archive_run,
    storage,
    monkeypatch,
    retention,
):
    """Restore recovers SQL payloads and all supported response forms."""
    ids = run_factory(retention_store, kind)
    project = retention_store.get_project(ids.project)
    monkeypatch.setattr(Client, "active_project", property(lambda _: project))
    monkeypatch.setattr(
        Client, "zen_store", property(lambda _: retention_store)
    )
    calls = [
        lambda: retention_store.get_run(ids.run),
        lambda: retention_store.get_run_step(
            ids.consumer, hydrate=kind != "legacy"
        ),
        lambda: retention_store.get_snapshot(ids.snapshot),
        lambda: retention_store.get_pipeline_run_dag(ids.run),
        lambda: retention_store.list_run_steps(
            StepRunFilter(pipeline_run_id=ids.run), hydrate=kind != "legacy"
        ),
    ]
    if kind != "legacy":
        calls.append(
            lambda: cache_utils.get_cached_step_run(str(ids.consumer))
        )
    else:
        with pytest.raises(ValidationError, match="snapshot_id"):
            retention_store.get_run_step(ids.consumer)
    before = [call().model_dump() for call in calls]
    sql_before = rows(retention_store)
    bundle_id = archive_run(retention_store, ids)
    assert cache_utils.get_cached_step_run(str(ids.consumer)) is None
    with Session(retention_store.engine) as session:
        run = session.get(PipelineRunSchema, ids.run)
        step = session.get(StepRunSchema, ids.consumer)
        assert run.orchestrator_environment is None
        assert step.step_configuration is None and step.exception_info is None
        assert step.source_code is None and step.docstring is None
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
    restored = retention.restore_pipeline_run(
        retention_store.get_run_header(ids.run)
    )

    assert restored.outcome == RestoreOutcome.RESTORED
    assert restored.restored_at is not None
    assert [call().model_dump() for call in calls] == before
    if kind == "legacy":
        with pytest.raises(ValidationError, match="snapshot_id"):
            retention_store.get_run_step(ids.consumer)
    sql_after = rows(retention_store)
    # These new columns are derived header projections, not archived payload.
    for source in (sql_before, sql_after):
        for step in source["step_run"]:
            step.pop("step_type")
            step.pop("substitutions")
    assert sql_after == sql_before
    with Session(retention_store.engine) as session:
        assert session.get(ArchiveBundleSchema, bundle_id).restored_at


def test_shared_configuration_change_invalidates_projections(
    retention_store,
    run_factory,
    storage,
    monkeypatch,
    retention,
):
    """A projection input outside the document still fails the recapture."""
    ids = run_factory(retention_store)
    other = run_factory(retention_store)
    snapshots = SQLModel.metadata.tables["pipeline_snapshot"]
    with retention_store.engine.begin() as connection:
        # Sharing the snapshot keeps its configuration out of the document.
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == other.run)
            .values(snapshot_id=ids.snapshot)
        )
    original = storage.write

    def change_after_upload(uri, data):
        original(uri, data)
        if uri.endswith(".json.gz"):
            with retention_store.engine.begin() as connection:
                connection.execute(
                    update(snapshots)
                    .where(snapshots.c.id == ids.snapshot)
                    .values(
                        pipeline_configuration=(
                            '{"name":"example",'
                            '"substitutions":{"team":"late"}}'
                        )
                    )
                )

    monkeypatch.setattr(storage, "write", change_after_upload)

    result = archiver.archive_runs(
        retention_store.engine,
        storage,
        retention.archive_settings(),
        [ids.run],
    )

    assert result.skipped == 1
    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        is None
    )


@pytest.mark.parametrize(
    "writer_kind", ["update", "step_update", "status", "replay", "delete"]
)
def test_write_after_retirement_fails_with_the_restore_command(
    archive_project,
    retention_store,
    run_factory,
    monkeypatch,
    retention,
    writer_kind,
    NOW,
):
    """A write waiting on retirement's lock sees the marker and fails."""
    ids = run_factory(retention_store)
    target = run_factory(retention_store, age_days=0)
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
        archive = archivers.submit(archive_project)
        assert locked.wait(20)
        operations = {
            "update": lambda: retention_store.update_run(
                ids.run,
                PipelineRunUpdate(
                    exception_info=ExceptionInfo(traceback="late")
                ),
            ),
            "step_update": lambda: retention_store.update_run_step(
                ids.consumer,
                StepRunUpdate(exception_info=ExceptionInfo(traceback="late")),
            ),
            "status": lambda: retention_store.update_run(
                ids.run,
                PipelineRunUpdate(
                    status=ExecutionStatus.COMPLETED, status_reason="late"
                ),
            ),
            "replay": lambda: retention_store.get_or_create_run(
                PipelineRunRequest(
                    project=ids.project,
                    name="replay",
                    snapshot=target.snapshot,
                    original_run_id=ids.run,
                    status=ExecutionStatus.RUNNING,
                )
            ),
            "delete": lambda: retention_store.delete_run(ids.run),
        }
        writer = writers.submit(operations[writer_kind])
        try:
            with pytest.raises(FutureTimeout):
                writer.result(timeout=1)
        finally:
            release.set()
        assert archive.result(timeout=20).archived == 1
        with pytest.raises(
            ExecutionArchivedError, match="pipeline runs unarchive"
        ):
            writer.result(timeout=20)

    if writer_kind == "step_update":
        step = retention_store.get_run_step(ids.consumer, hydrate=False)
        updated = retention_store.update_run_step(
            ids.consumer,
            StepRunUpdate(
                cache_expires_at=NOW,
                end_time=step.end_time,
            ),
        )
        with Session(retention_store.engine) as session:
            assert (
                session.get(StepRunSchema, ids.consumer).cache_expires_at
                == NOW
            )
        assert updated.archive_bundle_id is not None
        assert retention_store.update_run(ids.run, PipelineRunUpdate()).archive


@pytest.mark.parametrize("failure", ["upload", "retirement", "commit_ack"])
def test_interrupted_retirement(
    archive_project,
    retention_store,
    run_factory,
    storage,
    monkeypatch,
    failure,
    retention,
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
            outcome = archive_project()
    finally:
        event.remove(retention_store.engine, "before_cursor_execute", observe)

    state = outcome
    if failure != "commit_ack":
        assert state.failed == 1
        assert rows(retention_store) == before[0]
        assert not list(Path(storage.root).rglob("*.json.gz"))
    else:
        assert state.archived == 1
        restored = retention.restore_pipeline_run(
            retention_store.get_run_header(ids.run)
        )
        assert restored.outcome == RestoreOutcome.RESTORED
        assert retention_store.get_run(ids.run).model_dump() == before[1]


def test_unknown_retirement_outcome_keeps_uploaded_object(
    retention_store,
    run_factory,
    storage,
    monkeypatch,
    retention,
):
    """A missing catalog row cannot disprove a still-pending commit."""
    ids = run_factory(retention_store)
    pending = []

    @contextmanager
    def unresolved_commit(engine):
        connection = engine.connect().execution_options(
            isolation_level="READ COMMITTED"
        )
        transaction = connection.begin()
        session = Session(connection, expire_on_commit=False)
        pending.append((session, transaction, connection))
        yield session
        session.flush()
        raise ConnectionError("retirement commit outcome is unresolved")

    monkeypatch.setattr(
        archiver.transactions, "transaction", unresolved_commit
    )
    try:
        result = archiver.archive_runs(
            retention_store.engine,
            storage,
            retention.archive_settings(),
            [ids.run],
        )
        assert result.failed == 1
        session, transaction, _ = pending[0]
        transaction.commit()
        with Session(retention_store.engine) as verification:
            run = verification.get(PipelineRunSchema, ids.run)
            assert run is not None
            bundle = verification.get(
                ArchiveBundleSchema, run.archive_bundle_id
            )
            assert bundle is not None
            assert storage.artifact_store.exists(bundle.uri)
    finally:
        for session, transaction, connection in pending:
            if transaction.is_active:
                transaction.rollback()
            session.close()
            connection.close()


def test_capture_bounds_aggregate_multibyte_pages(
    retention_store, monkeypatch
) -> None:
    """A driver fetch stays bounded when small UTF-8 rows add up."""
    table = Table(
        "retention_capture_aggregate",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", Text),
    )
    table.create(retention_store.engine)
    payload = "😀" * 175
    payload_bytes = len(payload.encode("utf-8"))
    fetched_bytes = []
    original_fetchmany = pymysql.cursors.SSCursor.fetchmany

    def observe_fetchmany(cursor, size=None):
        fetched = original_fetchmany(cursor, size)
        fetched_bytes.append(
            sum(
                len(value.encode("utf-8"))
                for row in fetched
                for value in row
                if isinstance(value, str)
            )
        )
        return fetched

    try:
        with retention_store.engine.begin() as connection:
            connection.execute(
                table.insert(),
                [
                    {"id": identity, "payload": payload}
                    for identity in range(1, 5)
                ],
            )
        monkeypatch.setattr(capture, "MAX_SOURCE_BYTES", 4096)
        monkeypatch.setattr(capture, "SOURCE_BYTES_PER_PAGE", 1500)
        monkeypatch.setattr(
            pymysql.cursors.SSCursor, "fetchmany", observe_fetchmany
        )
        with Session(retention_store.engine) as session:
            capturer = capture.RunCapturer(
                session, ArchivableRun(run_id=uuid4())
            )
            captured = capturer._read_table(
                table,
                ["id", "payload"],
                (table.c.id, range(1, 5)),
            )

        assert [row["id"] for row in captured] == list(range(1, 5))
        assert capturer.source_bytes == 4 * payload_bytes
        assert fetched_bytes and max(fetched_bytes) <= 1500
    finally:
        table.drop(retention_store.engine)


def test_capture_guards_payload_before_driver_buffering(
    retention_store, monkeypatch
) -> None:
    """An oversized row reaches the driver without its guarded payload."""
    table = Table(
        "retention_capture_budget",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("payload", Text),
    )
    table.create(retention_store.engine)
    cap = 2048
    fetched_bytes = []
    original_fetchmany = pymysql.cursors.SSCursor.fetchmany

    def observe_fetchmany(cursor, size=None):
        rows = original_fetchmany(cursor, size)
        fetched_bytes.append(
            sum(
                len(value.encode("utf-8"))
                for row in rows
                for value in row
                if isinstance(value, str)
            )
        )
        return rows

    try:
        with retention_store.engine.begin() as connection:
            connection.execute(
                table.insert(),
                [
                    {"id": 1, "payload": ""},
                    {"id": 2, "payload": "x" * 3000},
                ],
            )
        monkeypatch.setattr(capture, "MAX_SOURCE_BYTES", cap)
        monkeypatch.setattr(
            pymysql.cursors.SSCursor, "fetchmany", observe_fetchmany
        )
        with Session(retention_store.engine) as session:
            capturer = capture.RunCapturer(
                session, ArchivableRun(run_id=uuid4())
            )
            with pytest.raises(ExecutionRetentionOversizedError):
                capturer._read_table(
                    table,
                    ["id", "payload"],
                    (table.c.id, [1, 2]),
                )

        assert fetched_bytes and max(fetched_bytes) <= cap
    finally:
        table.drop(retention_store.engine)


@pytest.mark.parametrize(
    "writer_kind", ["step", "update", "snapshot", "replay"]
)
def test_writer_racing_archive_preserves_committed_detail(
    archive_project,
    retention_store,
    run_factory,
    monkeypatch,
    NOW,
    writer_kind,
    retention,
):
    """Retirement waits for writers, then detects changed payload or ownership."""
    ids = run_factory(retention_store, "dynamic")
    entered, release = Event(), Event()
    hook = {
        "step": "protect_run",
        "update": "update",
        "snapshot": "lock_unarchived_snapshot",
        "replay": "protect_run",
    }[writer_kind]
    owner = PipelineRunSchema if writer_kind == "update" else fences
    original = getattr(owner, hook)
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

    monkeypatch.setattr(owner, hook, pause_after_lock)
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
        "replay": lambda: retention_store.get_or_create_run(
            PipelineRunRequest(
                project=ids.project,
                name="replay",
                snapshot=ids.snapshot,
                original_run_id=ids.run,
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
            archive = archives.submit(archive_project)
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
    archive_project()
    if writer_kind == "replay":
        assert retention_store.get_run(ids.run).archive_bundle_id is None
        replay, _ = written
        with retention_store.engine.begin() as connection:
            connection.execute(
                update(PipelineRunSchema)
                .where(PipelineRunSchema.id == replay.id)
                .values(status=ExecutionStatus.COMPLETED, in_progress=False)
            )
        archive_project()
    assert retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
    if writer_kind == "snapshot":
        assert (
            retention_store.get_snapshot(ids.snapshot).archive_bundle_id
            is None
        )
    retention.restore_pipeline_run(retention_store.get_run_header(ids.run))
    if writer_kind == "step":
        assert retention_store.get_run_step(written.id).config.name == "late"
    elif writer_kind == "update":
        assert (
            retention_store.get_run(ids.run).exception_info.message == "late"
        )


@pytest.mark.parametrize("failure", ["occupied", "insert"])
def test_restore_conflict_rolls_back_all_detail(
    retention_store,
    run_factory,
    archive_run,
    monkeypatch,
    failure,
    retention,
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
            retention.restore_pipeline_run(
                retention_store.get_run_header(ids.run)
            )
    finally:
        event.remove(
            retention_store.engine, "before_cursor_execute", fail_insert
        )
    assert rows(retention_store) == before


def test_restore_rejects_root_deleted_during_object_read(
    retention_store,
    run_factory,
    archive_run,
    storage,
    monkeypatch,
    retention,
) -> None:
    """A disappearing root is an expected conflict, not a generic error."""
    ids = run_factory(retention_store)
    archive_run(retention_store, ids)
    original_read = storage.read

    def delete_during_read(uri, max_bytes):
        data = original_read(uri, max_bytes)
        # Simulate a cascade from deleting the owning project or pipeline.
        with retention_store.engine.begin() as connection:
            connection.execute(
                delete(PipelineRunSchema).where(
                    PipelineRunSchema.id == ids.run
                )
            )
        return data

    monkeypatch.setattr(storage, "read", delete_during_read)

    with pytest.raises(ExecutionRetentionConflictError, match="disappeared"):
        retention.restore_pipeline_run(retention_store.get_run_header(ids.run))


def test_restore_rejects_changed_root_snapshot(
    retention_store,
    run_factory,
    archive_run,
    retention,
) -> None:
    """Restore validates the locked root ownership before writing detail."""
    ids = run_factory(retention_store)
    archive_run(retention_store, ids)
    with retention_store.engine.begin() as connection:
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == ids.run)
            .values(snapshot_id=None)
        )

    with pytest.raises(
        ExecutionRetentionConflictError, match="owner or snapshot"
    ):
        retention.restore_pipeline_run(retention_store.get_run_header(ids.run))


def test_targeted_archive_requires_explicit_policy_override(
    retention_store,
    run_factory,
    archive_request,
):
    """Manual archiving follows policy until force is explicit."""
    fresh = run_factory(retention_store, age_days=0)
    active = run_factory(retention_store, age_days=0)
    with retention_store.engine.begin() as connection:
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == active.run)
            .values(status=ExecutionStatus.RUNNING.value)
        )

    normal = archive_request(ArchiveRequest(run_ids=[fresh.run]))
    forced = archive_request(
        ArchiveRequest(run_ids=[fresh.run, active.run], force=True)
    )

    assert normal.archived == 0 and normal.skipped == 1
    assert normal.refusals == [
        ArchiveRefusal(run_id=fresh.run, reason=RetentionExclusion.NOT_OLD)
    ]
    assert forced.archived == 1 and forced.skipped == 1
    assert forced.refusals == [
        ArchiveRefusal(
            run_id=active.run, reason=RetentionExclusion.NOT_ELIGIBLE
        )
    ]
    assert retention_store.get_run(fresh.run, hydrate=False).archive_bundle_id
    assert (
        retention_store.get_run(active.run, hydrate=False).archive_bundle_id
        is None
    )


def test_targeted_archive_is_bounded_and_reports_more_work(
    retention_store,
    run_factory,
    monkeypatch,
    archive_request,
):
    """A project-wide archive does one batch and says more runs remain."""
    runs = [
        run_factory(retention_store, age_days=100 - index)
        for index in range(2)
    ]
    monkeypatch.setattr(eligibility, "MAX_ARCHIVE_BATCH_SIZE", 1)

    first = archive_request(ArchiveRequest(project_id=runs[0].project))
    second = archive_request(
        ArchiveRequest(
            project_id=runs[0].project,
            after_run_id=first.next_after_run_id,
        )
    )

    assert (first.archived, first.pending) == (1, True)
    assert first.next_after_run_id == runs[0].run
    assert (second.archived, second.pending) == (1, False)
    assert second.next_after_run_id is None
    assert all(
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        for ids in runs
    )


def test_archive_preview_is_bounded_and_side_effect_free(
    retention_store,
    run_factory,
    storage,
    monkeypatch,
    archive_request,
):
    """Dry-run uses eligibility without storage access or database writes."""
    eligible = run_factory(retention_store, age_days=100)
    active = run_factory(retention_store, age_days=99)
    with retention_store.engine.begin() as connection:
        connection.execute(
            update(PipelineRunSchema)
            .where(PipelineRunSchema.id == active.run)
            .values(status=ExecutionStatus.RUNNING.value)
        )
    before = rows(retention_store)

    def blocked(*_, **__):
        pytest.fail("dry-run accessed archive storage")

    monkeypatch.setattr(storage, "read", blocked)
    monkeypatch.setattr(storage, "write", blocked)

    result = archive_request(
        ArchiveRequest(project_id=eligible.project, dry_run=True)
    )

    assert result.dry_run
    assert (result.eligible, result.skipped, result.archived) == (1, 1, 0)
    assert result.refusals == [
        ArchiveRefusal(
            run_id=active.run, reason=RetentionExclusion.NOT_ELIGIBLE
        )
    ]
    assert rows(retention_store) == before


def test_pausing_new_archives_keeps_preview_and_restore_available(
    archive_project,
    retention_store,
    run_factory,
    archive_run,
    monkeypatch,
    retention,
    archive_request,
):
    """The write gate does not remove configured recovery access."""
    archived = run_factory(retention_store)
    archive_run(retention_store, archived)
    candidate = run_factory(retention_store)
    monkeypatch.setenv("ZENML_SERVER_ARCHIVE__ENABLED", "false")

    settings = ServerConfiguration.get_server_config().archive
    assert settings.configured
    assert not settings.new_archives_enabled
    with pytest.raises(ExecutionRetentionConflictError, match="paused"):
        archive_request(ArchiveRequest(run_ids=[candidate.run], force=True))
    with pytest.raises(ExecutionRetentionConflictError, match="paused"):
        archive_project()
    preview = archive_request(
        ArchiveRequest(run_ids=[candidate.run], dry_run=True)
    )
    assert preview.eligible == 1
    assert retention.restore_pipeline_run(
        retention_store.get_run_header(archived.run)
    ).outcome == (RestoreOutcome.RESTORED)


def test_archive_continuation_is_scoped_to_its_target(
    retention_store,
    run_factory,
    archive_request,
):
    """A cursor from another owner cannot move this target's scan."""
    target = run_factory(retention_store)
    other = run_factory(retention_store)

    with pytest.raises(KeyError, match="not available for this target"):
        archive_request(
            ArchiveRequest(
                pipeline_id=target.pipeline,
                after_run_id=other.run,
                dry_run=True,
            )
        )


def test_archived_snapshot_cannot_be_named_without_restore(
    retention_store,
    run_factory,
    archive_run,
    retention,
):
    """Naming is new use: a named snapshot must own its definition in SQL."""
    ids = run_factory(retention_store)
    archive_run(retention_store, ids)

    with pytest.raises(ExecutionArchivedError):
        retention_store.update_snapshot(
            ids.snapshot, PipelineSnapshotUpdate(name="promoted")
        )

    retention.restore_pipeline_run(retention_store.get_run_header(ids.run))
    named = retention_store.update_snapshot(
        ids.snapshot, PipelineSnapshotUpdate(name="promoted")
    )
    assert named.name == "promoted"
