# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive and restore round trips, races, atomicity, and pass progress."""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import timedelta
from pathlib import Path
from threading import Event, current_thread
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select
from sqlmodel import Session

from tests.unit.zen_stores.retention.fixture_graph import (
    dynamic_step,
    graph_rows,
    insert_rows,
)
from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    RestoreOutcome,
    RetentionFailure,
    RetentionOutcome,
)
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunUpdate,
    ProjectFilter,
    ProjectUpdate,
    RunMetadataRequest,
    RunMetadataResource,
    StepRunFilter,
    StepRunResponseMetadata,
)
from zenml.models.v2.misc.exception_info import ExceptionInfo
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.retention import archiver, capture, fences
from zenml.zen_stores.retention.state import RetentionState
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineRunSchema,
    ProjectSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

RESPONSE_MARKERS = {
    "body": {"archive_bundle_id"},
    "resources": {
        "snapshot": {"body": {"archive_bundle_id"}},
        "run": {"body": {"archive_bundle_id"}},
    },
}


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


def set_policy(store: SqlZenStore, project_id: UUID, **values) -> None:
    """Save a retention policy with a 7-day age and the given overrides.

    Args:
        store: Metadata store.
        project_id: Project.
        **values: Policy fields to override.
    """
    store.update_project(
        project_id,
        ProjectUpdate(
            retention=RetentionSettings(archive_after_days=7, **values)
        ),
    )


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_archive_restore_round_trip(
    retention_store, kind, run_factory, archive_run, storage
):
    """Every read looks the same while archived and after restore."""
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
    exclude = {**RESPONSE_MARKERS, "items": {"__all__": RESPONSE_MARKERS}}
    before = [call().model_dump() for call in calls]
    hot = [call().model_dump(exclude=exclude) for call in calls]
    bundle_id = archive_run(retention_store, ids)
    with Session(retention_store.engine) as session:
        run = session.get(PipelineRunSchema, ids.run)
        step = session.get(StepRunSchema, ids.consumer)
        assert run.orchestrator_environment is None
        assert step.step_configuration is None
        assert step.archive_bundle_id == bundle_id
        assert not session.scalars(
            select(StepConfigurationSchema).where(
                (StepConfigurationSchema.snapshot_id == ids.snapshot)
                | StepConfigurationSchema.step_run_id.in_(
                    [ids.producer, ids.consumer]
                )
            )
        ).all()
        bundle = session.get(ArchiveBundleSchema, bundle_id)
        assert bundle.run_id == ids.run and bundle.restored_at is None
    assert storage.read(bundle.uri, bundle.size_bytes)
    assert [call().model_dump(exclude=exclude) for call in calls] == hot

    restored = retention_store.restore_pipeline_run(ids.run)

    assert restored.outcome == RestoreOutcome.RESTORED
    assert restored.restored_at is not None
    assert [call().model_dump() for call in calls] == before
    with Session(retention_store.engine) as session:
        assert session.get(ArchiveBundleSchema, bundle_id).restored_at


@pytest.mark.parametrize(
    "kind,conflict", [("dynamic", False), ("dynamic", True)]
)
def test_restore_writes_back_many_configurations(
    retention_store, storage, NOW, kind, conflict
):
    """Restore 1,500 definitions, or roll everything back on a late conflict."""
    project = retention_store.list_projects(ProjectFilter()).items[0].id
    source = graph_rows(project, NOW - timedelta(days=100))
    configuration_template = source["step_configuration"][0]
    step_template = source["step_run"][0]
    for index in range(1_498):
        name = f"extra-{index}"
        configuration = dict(configuration_template)
        configuration.update(id=uuid4(), index=index + 2, name=name)
        source["step_configuration"].append(configuration)
        if kind == "dynamic":
            step = dict(step_template)
            step.update(id=uuid4(), name=name)
            source["step_run"].append(step)
    source["pipeline_snapshot"][0]["step_count"] = 1_500
    if kind == "dynamic":
        source["pipeline_snapshot"][0]["is_dynamic"] = True
        steps = {row["name"]: row["id"] for row in source["step_run"]}
        for configuration in source["step_configuration"]:
            configuration.update(
                snapshot_id=None, step_run_id=steps[configuration["name"]]
            )
    insert_rows(retention_store, source)
    set_policy(retention_store, project)
    run_id = source["pipeline_run"][0]["id"]
    configuration_ids = {row["id"] for row in source["step_configuration"]}

    assert (
        retention_store.archive_project(project).outcome
        == RetentionOutcome.SUCCEEDED
    )
    if conflict:
        occupied = source["step_configuration"][1_200]
        with retention_store.engine.begin() as connection:
            connection.execute(
                StepConfigurationSchema.__table__.insert().values(**occupied)
            )
        with pytest.raises(ExecutionRetentionConflictError):
            retention_store.restore_pipeline_run(run_id)
        with Session(retention_store.engine) as session:
            run = session.get(PipelineRunSchema, run_id)
            assert run.orchestrator_environment is None
            assert run.archive_bundle_id is not None
            assert session.scalars(
                select(StepConfigurationSchema.id).where(
                    StepConfigurationSchema.id.in_(configuration_ids)
                )
            ).all() == [occupied["id"]]
    else:
        restored = retention_store.restore_pipeline_run(run_id)
        assert restored.outcome == RestoreOutcome.RESTORED
        with Session(retention_store.engine) as session:
            assert (
                set(
                    session.scalars(
                        select(StepConfigurationSchema.id).where(
                            StepConfigurationSchema.id.in_(configuration_ids)
                        )
                    )
                )
                == configuration_ids
            )


def test_step_added_while_archiving_is_never_lost(
    retention_store, run_factory, storage, monkeypatch, NOW
):
    """A step committed before retirement's lock makes that run wait a pass."""
    ids = run_factory(retention_store, "dynamic")
    name = f"late-{uuid4().hex[:8]}"
    guarded, release = Event(), Event()
    original = fences.protect_inserts

    def pause_after_guard(*args, **kwargs):
        original(*args, **kwargs)
        if current_thread().name.startswith("writer"):
            guarded.set()
            assert release.wait(20)

    monkeypatch.setattr(fences, "protect_inserts", pause_after_guard)
    with (
        ThreadPoolExecutor(1, thread_name_prefix="writer") as writers,
        ThreadPoolExecutor(1, thread_name_prefix="archive") as archivers,
    ):
        writer = writers.submit(
            retention_store.create_run_step, dynamic_step(ids, name, NOW)
        )
        assert guarded.wait(10)
        archive = archivers.submit(
            retention_store.archive_project, ids.project
        )
        try:
            with pytest.raises(FutureTimeout):
                archive.result(timeout=1)
        finally:
            release.set()
        created = writer.result(timeout=20)
        outcome = archive.result(timeout=20)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    assert saved_state(retention_store, ids.project).skipped == 1
    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        is None
    )
    second = retention_store.archive_project(ids.project)
    assert second.outcome == RetentionOutcome.SUCCEEDED
    assert retention_store.get_run_step(created.id).name == name
    retention_store.restore_pipeline_run(ids.run)
    assert retention_store.get_run_step(created.id).config.name == name


def test_detail_update_racing_retirement_is_kept(
    retention_store, run_factory, storage, monkeypatch
):
    """An update committed while retirement waits changes what is archived."""
    ids = run_factory(retention_store)
    updated, release = Event(), Event()
    original = fences.update_hot

    def pause_after_update(*args, **kwargs):
        original(*args, **kwargs)
        if current_thread().name.startswith("writer"):
            updated.set()
            assert release.wait(20)

    monkeypatch.setattr(fences, "update_hot", pause_after_update)
    failure = ExceptionInfo(traceback="late failure", message="late")
    with (
        ThreadPoolExecutor(1, thread_name_prefix="writer") as writers,
        ThreadPoolExecutor(1, thread_name_prefix="archive") as archivers,
    ):
        writer = writers.submit(
            retention_store.update_run,
            ids.run,
            PipelineRunUpdate(exception_info=failure),
        )
        assert updated.wait(10)
        archive = archivers.submit(
            retention_store.archive_project, ids.project
        )
        try:
            with pytest.raises(FutureTimeout):
                archive.result(timeout=1)
        finally:
            release.set()
        writer.result(timeout=20)
        archive.result(timeout=20)

    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        is None
    )
    retention_store.archive_project(ids.project)
    assert retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
    assert retention_store.get_run(ids.run).exception_info.message == "late"


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


def test_new_run_using_the_snapshot_while_archiving_keeps_it_hot(
    retention_store, run_factory, storage, monkeypatch
):
    """Retirement re-checks ownership only after locking the snapshot."""
    ids = run_factory(retention_store)
    guarded, release = Event(), Event()
    original = fences.protect_snapshot_owners
    calls = []

    def pause_after_guard(*args, **kwargs):
        original(*args, **kwargs)
        if current_thread().name.startswith("writer"):
            calls.append(1)
            # Run creation guards twice; the second guard protects the insert
            # after the run index allocation committed.
            if len(calls) == 2:
                guarded.set()
                assert release.wait(20)

    monkeypatch.setattr(fences, "protect_snapshot_owners", pause_after_guard)
    request = PipelineRunRequest(
        project=ids.project,
        name=f"new-{uuid4().hex[:8]}",
        snapshot=ids.snapshot,
        status=ExecutionStatus.RUNNING,
    )
    with (
        ThreadPoolExecutor(1, thread_name_prefix="writer") as writers,
        ThreadPoolExecutor(1, thread_name_prefix="archive") as archivers,
    ):
        writer = writers.submit(retention_store.get_or_create_run, request)
        assert guarded.wait(10)
        archive = archivers.submit(
            retention_store.archive_project, ids.project
        )
        try:
            with pytest.raises(FutureTimeout):
                archive.result(timeout=1)
        finally:
            release.set()
        writer.result(timeout=20)
        archive.result(timeout=20)

    assert (
        retention_store.get_snapshot(
            ids.snapshot, hydrate=False
        ).archive_bundle_id
        is None
    )
    retention_store.archive_project(ids.project)
    assert retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
    assert (
        retention_store.get_snapshot(
            ids.snapshot, hydrate=False
        ).archive_bundle_id
        is None
    )


def test_run_creation_rechecks_the_snapshot_after_index_allocation(
    retention_store, run_factory, storage, monkeypatch
):
    """Archival between index allocation and insert cannot orphan a new run."""
    ids = run_factory(retention_store)
    allocate = SqlZenStore._get_next_run_index

    def allocate_then_archive(store, pipeline_id, session):
        index = allocate(store, pipeline_id=pipeline_id, session=session)
        outcome = store.archive_project(ids.project)
        assert outcome.outcome == RetentionOutcome.SUCCEEDED
        return index

    monkeypatch.setattr(
        SqlZenStore, "_get_next_run_index", allocate_then_archive
    )
    runs = PipelineRunFilter(project=ids.project)
    before = retention_store.list_runs(runs).total

    with pytest.raises(ExecutionArchivedError):
        retention_store.get_or_create_run(
            PipelineRunRequest(
                project=ids.project,
                name=f"late-{uuid4().hex[:8]}",
                snapshot=ids.snapshot,
                status=ExecutionStatus.RUNNING,
            )
        )

    assert retention_store.list_runs(runs).total == before


def test_losing_pass_removes_its_object(
    retention_store, run_factory, storage, monkeypatch, NOW
):
    """Two passes racing on one run leave one bundle and one object."""
    ids = run_factory(retention_store)
    uploaded, release = Event(), Event()
    original = storage.write

    def pause_after_upload(uri, data):
        original(uri, data)
        if current_thread().name.startswith("stale"):
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
    assert len(bundles) == 1
    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        == bundles[0].id
    )
    assert stored_objects(storage) == [f"{bundles[0].id}.json.gz"]


def test_second_pass_is_rejected_while_the_first_holds_its_lease(
    retention_store, run_factory, storage
):
    """Only one pass per project runs at a time."""
    ids = run_factory(retention_store)
    retention_store.prepare_retention_pass(ids.project)
    with pytest.raises(ExecutionRetentionConflictError) as error:
        retention_store.prepare_retention_pass(ids.project)
    assert error.value.error_code == RetentionFailure.BUSY


def test_abandoned_pass_is_replaced_after_its_lease(
    retention_store, run_factory, storage, NOW
):
    """A pass that stopped updating is reported expired and can be replaced."""
    ids = run_factory(retention_store)
    abandoned = retention_store.prepare_retention_pass(ids.project)
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

    replacement = retention_store.prepare_retention_pass(ids.project)

    assert replacement.operation_id != abandoned.operation_id
    result = retention_store.execute_retention_pass(replacement)
    assert result.outcome == RetentionOutcome.SUCCEEDED
    # A late run of the abandoned pass finds its state taken and writes nothing.
    assert abandoned.run().operation_id == replacement.operation_id
    status = retention_store.get_retention_status(ids.project)
    assert status.outcome == RetentionOutcome.SUCCEEDED
    assert status.archived == 1


@pytest.mark.parametrize("failure", ["retirement", "commit_ack"])
def test_interrupted_retirement(
    retention_store, run_factory, storage, rows, monkeypatch, failure
):
    """A failed commit changes nothing; a lost acknowledgement keeps the object."""
    ids = run_factory(retention_store)
    before = (
        rows(retention_store),
        retention_store.get_run(ids.run).model_dump(),
    )
    inserted = False
    original_commit = retention_store.engine.dialect.do_commit

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
            outcome = retention_store.archive_project(ids.project)
    finally:
        event.remove(retention_store.engine, "before_cursor_execute", observe)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    state = saved_state(retention_store, ids.project)
    if failure == "retirement":
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
    set_policy(retention_store, project, max_runs_per_pass=1)

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


def test_oversized_run_is_counted_and_not_read_again(
    retention_store, run_factory, storage, rows, monkeypatch
):
    """A run over the byte budget stops capture early and is remembered."""
    ids = run_factory(retention_store)
    exception_info = ExceptionInfo(traceback="x" * 20 * 1024).model_dump_json()
    with Session(retention_store.engine) as session:
        for step in session.scalars(
            select(StepRunSchema).where(
                StepRunSchema.pipeline_run_id == ids.run
            )
        ):
            step.exception_info = exception_info
            session.add(step)
        session.commit()
    charged = []
    measure = capture.source_row_bytes

    def counted(row):
        charged.append(row["id"])
        return measure(row)

    monkeypatch.setattr(capture, "source_row_bytes", counted)
    monkeypatch.setattr(capture, "MAX_SOURCE_BYTES", 16 * 1024)
    before = rows(retention_store)

    outcome = retention_store.archive_project(ids.project)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    state = saved_state(retention_store, ids.project)
    assert state.oversized == 1 and state.oversized_run_ids == [ids.run]
    assert rows(retention_store) == before
    charged.clear()
    retention_store.archive_project(ids.project)
    assert charged == []
    assert saved_state(retention_store, ids.project).oversized == 0


def test_policy_change_pauses_the_pass(
    retention_store, run_factory, storage, monkeypatch
):
    """A pass stops instead of archiving under a policy that changed."""
    ids = run_factory(retention_store)
    original = capture.capture_run

    def change_policy_then_capture(session, run):
        set_policy(retention_store, ids.project, max_runs_per_pass=5)
        return original(session, run)

    monkeypatch.setattr(archiver, "capture_run", change_policy_then_capture)

    outcome = retention_store.archive_project(ids.project)

    assert outcome.outcome == RetentionOutcome.PAUSED
    assert (
        retention_store.get_run(ids.run, hydrate=False).archive_bundle_id
        is None
    )
    assert stored_objects(storage) == []


def test_concurrent_restores_restore_once(
    retention_store, run_factory, archive_run, storage, monkeypatch
):
    """The slower of two restores finds the run restored and reports a no-op."""
    ids = run_factory(retention_store)
    bundle_id = archive_run(retention_store, ids)
    downloaded, release = Event(), Event()
    original = storage.read

    def pause_after_download(uri, max_bytes):
        data = original(uri, max_bytes)
        if current_thread().name.startswith("slow"):
            downloaded.set()
            assert release.wait(20)
        return data

    monkeypatch.setattr(storage, "read", pause_after_download)
    with ThreadPoolExecutor(1, thread_name_prefix="slow") as pool:
        slow = pool.submit(retention_store.restore_pipeline_run, ids.run)
        try:
            assert downloaded.wait(20)
            fast = retention_store.restore_pipeline_run(ids.run)
        finally:
            release.set()
        late = slow.result(timeout=20)

    assert fast.outcome == RestoreOutcome.RESTORED
    assert late.outcome == RestoreOutcome.NOOP
    with Session(retention_store.engine) as session:
        assert session.get(ArchiveBundleSchema, bundle_id).restored_at


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
    assert retention_store.get_snapshot(ids.snapshot).pipeline_spec
    retention_store.delete_snapshot(ids.snapshot)


def test_metadata_still_attaches_to_an_archived_run(
    retention_store, run_factory, archive_run
):
    """Metadata never left SQL, so publishing it needs no restore."""
    ids = run_factory(retention_store)
    archive_run(retention_store, ids)

    retention_store.create_run_metadata(
        RunMetadataRequest(
            project=ids.project,
            resources=[
                RunMetadataResource(
                    id=ids.run, type=MetadataResourceTypes.PIPELINE_RUN
                )
            ],
            values={"late": "kept"},
            types={"late": MetadataTypeEnum.STRING},
        )
    )

    assert retention_store.get_run(ids.run).run_metadata["late"] == "kept"


class ReleasedStepRunResponseMetadata(StepRunResponseMetadata):
    """Step metadata as released clients declare it, with a required snapshot."""

    snapshot_id: UUID


def test_archived_step_metadata_keeps_the_released_client_contract(
    retention_store, run_factory, archive_run
):
    """Archived steps keep snapshot_id, so older clients still parse them."""
    ids = run_factory(retention_store, "dynamic")
    archive_run(retention_store, ids)

    step = retention_store.get_run_step(ids.consumer)

    assert step.archive_bundle_id is not None
    metadata = ReleasedStepRunResponseMetadata.model_validate_json(
        step.get_metadata().model_dump_json()
    )
    assert metadata.snapshot_id == ids.snapshot
