# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Public retirement, restoration, fencing, atomicity, and scan progress."""

import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event, current_thread
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import event, select, update
from sqlmodel import Session

from tests.unit.zen_stores.retention.fixture_graph import (
    graph_rows,
    insert_rows,
)
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import (
    ArchiveBundleStatus,
    ExecutionStatus,
    RetentionFailure,
    RetentionOutcome,
    RunWaitConditionType,
)
from zenml.exceptions import (
    ExecutionArchivedError,
    ExecutionRetentionConflictError,
)
from zenml.models import (
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineSnapshotFilter,
    ProjectFilter,
    ProjectUpdate,
    RunWaitConditionRequest,
    StackFilter,
    StepRunFilter,
    StepRunRequest,
)
from zenml.models.v2.misc.retention import RetentionSettings
from zenml.zen_stores.retention import fences, transactions
from zenml.zen_stores.retention.archiver import ArchivePass
from zenml.zen_stores.retention.catalog import RetentionState
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    PipelineBuildSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    ProjectSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    StepConfigurationSchema,
    StepRunSchema,
)


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("sql_store", id="sqlite"),
        pytest.param(
            "mysql_store", marks=pytest.mark.retention_mysql, id="mysql"
        ),
    ],
)
@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_archive_restore_round_trip(
    request,
    backend,
    kind,
    tree_factory,
    archive_one_tree,
    storage,
    monkeypatch,
):
    """Restore all execution shapes after verified retirement."""
    sql_store = request.getfixturevalue(backend)
    ids = tree_factory(sql_store, kind)
    calls = [
        lambda: sql_store.get_run(ids.run),
        lambda: sql_store.get_run_step(ids.consumer),
        lambda: sql_store.get_snapshot(ids.snapshot),
        lambda: sql_store.get_pipeline_run_dag(ids.run),
        lambda: sql_store.list_run_steps(
            StepRunFilter(pipeline_run_id=ids.run), hydrate=True
        ),
    ]
    marker = {
        "body": {"archive_bundle_id"},
        "resources": {
            "snapshot": {"body": {"archive_bundle_id"}},
            "run": {"body": {"archive_bundle_id"}},
        },
    }
    exclude = {**marker, "items": {"__all__": marker}}
    before = [call().model_dump() for call in calls]
    hot = [call().model_dump(exclude=exclude) for call in calls]
    archive_one_tree(sql_store, ids)
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, ids.run)
        step = session.get(StepRunSchema, ids.consumer)
        assert run.orchestrator_environment is None
        assert step.step_configuration is None
        configurations = select(StepConfigurationSchema).where(
            (StepConfigurationSchema.snapshot_id == ids.snapshot)
            | StepConfigurationSchema.step_run_id.in_(
                [ids.producer, ids.consumer]
            )
        )
        assert not session.scalars(configurations).all()
    assert [call().model_dump(exclude=exclude) for call in calls] == hot
    restored = sql_store.restore_pipeline_run(ids.run)
    assert restored.outcome == RetentionOutcome.SUCCEEDED
    assert [call().model_dump() for call in calls] == before


def test_archive_aware_execution_filters(
    sql_store, tree_factory, archive_one_tree
):
    """Keep execution flags and their public filters aligned when offloaded."""
    ids = tree_factory(sql_store)
    stack_id = sql_store.list_stacks(StackFilter()).items[0].id
    with Session(sql_store.engine) as session:
        build = PipelineBuildSchema(
            project_id=ids.project,
            stack_id=stack_id,
            images="{}",
            is_local=False,
            contains_code=True,
        )
        session.add(build)
        session.flush()
        snapshot = session.get(PipelineSnapshotSchema, ids.snapshot)
        assert snapshot
        snapshot.build_id = build.id
        snapshot.stack_id = stack_id
        session.add(snapshot)
        session.commit()

    def assert_state(*, available: bool) -> None:
        snapshot = sql_store.get_snapshot(ids.snapshot)
        run = sql_store.get_run(ids.run)
        assert snapshot.runnable is available
        assert run.get_metadata().is_templatable is available

        runnable = sql_store.list_snapshots(
            PipelineSnapshotFilter(runnable=True)
        ).items
        deployable = sql_store.list_snapshots(
            PipelineSnapshotFilter(deployable=True)
        ).items
        templatable = sql_store.list_runs(
            PipelineRunFilter(templatable=True)
        ).items
        not_templatable = sql_store.list_runs(
            PipelineRunFilter(templatable=False)
        ).items
        assert (ids.snapshot in {item.id for item in runnable}) is available
        assert (ids.snapshot in {item.id for item in deployable}) is available
        assert (ids.run in {item.id for item in templatable}) is available
        assert (
            ids.run in {item.id for item in not_templatable}
        ) is not available

    assert_state(available=True)
    archive_one_tree(sql_store, ids)
    assert_state(available=False)
    sql_store.restore_pipeline_run(ids.run)
    assert_state(available=True)


def test_shared_snapshot_capture_uses_bounded_projection(
    sql_store, tree_factory, storage, NOW
):
    """Avoid loading unretired snapshot payloads while preserving run detail."""
    ids = tree_factory(sql_store)
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, ids.snapshot)
        run = session.get(PipelineRunSchema, ids.run)
        assert snapshot and run
        snapshot.source_code = "shared payload " + "x" * 1_000_000
        session.add(snapshot)
        session.add(
            PipelineRunSchema(
                project_id=ids.project,
                pipeline_id=run.pipeline_id,
                snapshot_id=ids.snapshot,
                name=str(uuid4()),
                index=2,
                status=ExecutionStatus.COMPLETED,
                in_progress=False,
                enable_heartbeat=False,
                end_time=NOW,
            )
        )
        session.commit()

    marker = {"body": {"archive_bundle_id"}}
    before = sql_store.get_run(ids.run).model_dump(exclude=marker)
    statements = []

    def record_statement(
        connection, cursor, statement, parameters, context, executemany
    ):
        statements.append(" ".join(statement.split()))

    event.listen(sql_store.engine, "before_cursor_execute", record_statement)
    try:
        outcome = sql_store.archive_project(ids.project)
    finally:
        event.remove(
            sql_store.engine, "before_cursor_execute", record_statement
        )

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    projection = (
        "SELECT pipeline_snapshot.id, pipeline_snapshot.is_dynamic, "
        "pipeline_snapshot.archive_bundle_id, "
        "pipeline_snapshot.pipeline_configuration FROM pipeline_snapshot"
    )
    assert any(statement.startswith(projection) for statement in statements)
    assert sql_store.get_run(ids.run).model_dump(exclude=marker) == before


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="SQLite variable limits require Connection.setlimit",
)
@pytest.mark.parametrize(
    "kind,conflict", [("static", False), ("dynamic", False), ("dynamic", True)]
)
def test_restore_batches_large_configuration_sets(
    sql_store, storage, NOW, kind, conflict
):
    """Restore 500 definitions under 999 binds and roll back late conflicts."""
    project = sql_store.list_projects(ProjectFilter()).items[0].id
    source = graph_rows(project, NOW - timedelta(days=100))
    configuration_template = source["step_configuration"][0]
    step_template = source["step_run"][0]
    for index in range(498):
        name = f"extra-{index}"
        configuration = dict(configuration_template)
        configuration.update(id=uuid4(), index=index + 2, name=name)
        source["step_configuration"].append(configuration)
        if kind == "dynamic":
            step = dict(step_template)
            step.update(id=uuid4(), name=name)
            source["step_run"].append(step)
    source["pipeline_snapshot"][0]["step_count"] = 500
    if kind == "dynamic":
        source["pipeline_snapshot"][0]["is_dynamic"] = True
        steps = {row["name"]: row["id"] for row in source["step_run"]}
        for configuration in source["step_configuration"]:
            configuration.update(
                snapshot_id=None,
                step_run_id=steps[configuration["name"]],
            )
    insert_rows(sql_store, source)
    sql_store.update_project(
        project,
        ProjectUpdate(retention=RetentionSettings(archive_after_days=7)),
    )
    configuration_rows = sorted(
        source["step_configuration"], key=lambda row: str(row["id"])
    )
    configuration_ids = [row["id"] for row in configuration_rows]

    def limit_bind_parameters(connection, record):
        if isinstance(connection, sqlite3.Connection):
            connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 999)

    event.listen(sql_store.engine, "connect", limit_bind_parameters)
    sql_store.engine.dispose()
    try:
        outcome = sql_store.archive_project(project)
        assert outcome.outcome == RetentionOutcome.SUCCEEDED
        run_id = source["pipeline_run"][0]["id"]
        if conflict:
            occupied = configuration_rows[450]
            with sql_store.engine.begin() as connection:
                connection.execute(
                    StepConfigurationSchema.__table__.insert().values(
                        **occupied
                    )
                )
            with pytest.raises(ExecutionRetentionConflictError):
                sql_store.restore_pipeline_run(run_id)
            with Session(sql_store.engine) as session:
                assert (
                    session.get(
                        PipelineRunSchema, run_id
                    ).orchestrator_environment
                    is None
                )
                assert session.scalars(
                    select(StepConfigurationSchema.id).where(
                        StepConfigurationSchema.id.in_(configuration_ids)
                    )
                ).all() == [occupied["id"]]
        else:
            restored = sql_store.restore_pipeline_run(run_id)
            assert restored.outcome == RetentionOutcome.SUCCEEDED
            with Session(sql_store.engine) as session:
                assert set(
                    session.scalars(
                        select(StepConfigurationSchema.id).where(
                            StepConfigurationSchema.id.in_(configuration_ids)
                        )
                    )
                ) == set(configuration_ids)
    finally:
        event.remove(sql_store.engine, "connect", limit_bind_parameters)


def test_sqlite_insert_guard_holds_lock_until_step_commit(
    sql_store, tree_factory, storage, monkeypatch, NOW
):
    """Retirement captures a step inserted after its guard acquires SQLite."""
    ids = tree_factory(sql_store, "dynamic")
    step_name = f"late-{uuid4().hex[:8]}"
    request = StepRunRequest(
        project=ids.project,
        name=step_name,
        pipeline_run_id=ids.run,
        start_time=NOW,
        end_time=NOW,
        status=ExecutionStatus.COMPLETED,
        dynamic_config=Step(
            spec=StepSpec(
                source=Source(module="tests", type=SourceType.INTERNAL),
                upstream_steps=[],
            ),
            config=StepConfiguration(name=step_name),
        ),
    )
    guarded, release, archive_opened = Event(), Event(), Event()
    original_guard = fences.protect_inserts
    original_open = storage.open

    def pause_after_guard(*args, **kwargs):
        result = original_guard(*args, **kwargs)
        if current_thread().name.startswith("guarded-writer"):
            guarded.set()
            assert release.wait(10)
        return result

    def observe_archive(path, mode="r"):
        if mode == "wb" and str(path).endswith("rows.tar.gz"):
            archive_opened.set()
        return original_open(path, mode)

    monkeypatch.setattr(fences, "protect_inserts", pause_after_guard)
    monkeypatch.setattr(storage, "open", observe_archive)
    with (
        ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="guarded-writer"
        ) as writer_pool,
        ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="retirement"
        ) as archive_pool,
    ):
        writer = writer_pool.submit(sql_store.create_run_step, request)
        assert guarded.wait(10)
        archive = archive_pool.submit(sql_store.archive_project, ids.project)
        try:
            assert not archive_opened.wait(0.5)
        finally:
            release.set()
        created = writer.result(timeout=10)
        outcome = archive.result(timeout=10)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    assert sql_store.get_run_step(created.id).name == step_name


def test_membership_writer_loses_when_archive_reaches_guard_first(
    sql_store, tree_factory, storage, monkeypatch
):
    """A child writer arriving after retirement fails without corrupting reads."""
    ids = tree_factory(sql_store)
    reached, release = Event(), Event()
    original_guard = fences.protect_membership

    def pause_before_guard(*args, **kwargs):
        if current_thread().name.startswith("late-child"):
            reached.set()
            assert release.wait(10)
        return original_guard(*args, **kwargs)

    monkeypatch.setattr(fences, "protect_membership", pause_before_guard)
    request = PipelineRunRequest(
        project=ids.project,
        name=f"late-child-{uuid4().hex[:8]}",
        snapshot=ids.snapshot,
        status=ExecutionStatus.RUNNING,
        parent_run_id=ids.run,
        child_key="late-child",
    )
    with ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="late-child"
    ) as pool:
        writer = pool.submit(sql_store.get_or_create_run, request)
        assert reached.wait(10)
        try:
            outcome = sql_store.archive_project(ids.project)
        finally:
            release.set()
        with pytest.raises(
            (ExecutionArchivedError, ExecutionRetentionConflictError)
        ):
            writer.result(timeout=10)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    assert sql_store.get_run(ids.run).id == ids.run


def test_archive_renews_claim_after_readback(
    sql_store, tree_factory, storage, monkeypatch, NOW
):
    """Renew a shortened live claim after slow archive verification."""
    ids = tree_factory(sql_store)
    clock = {"now": NOW}
    connection = sql_store.engine.raw_connection()
    try:
        connection.driver_connection.create_function(
            "current_timestamp",
            0,
            lambda: clock["now"].isoformat(" "),
        )
    finally:
        connection.close()

    original_open = storage.open
    shortened = False

    def shorten_claim(path, mode="r"):
        nonlocal shortened
        if (
            mode == "rb"
            and str(path).endswith("rows.tar.gz")
            and not shortened
        ):
            shortened = True
            with transactions.transaction(sql_store.engine) as session:
                session.execute(
                    update(ArchiveBundleSchema)
                    .where(
                        ArchiveBundleSchema.active_root_id == ids.run,
                        ArchiveBundleSchema.status
                        == ArchiveBundleStatus.PENDING,
                    )
                    .values(claim_expires_at=NOW + timedelta(minutes=1))
                )
        return original_open(path, mode)

    original_retire = ArchivePass._retire

    def retire_after_time_passes(archive_pass, prepared):
        assert shortened
        clock["now"] = NOW + timedelta(minutes=2)
        result = original_retire(archive_pass, prepared)
        with Session(sql_store.engine) as session:
            project = session.get(ProjectSchema, ids.project)
            assert project and project.retention_state
            state = RetentionState.model_validate_json(project.retention_state)
            assert state.last_outcome == RetentionOutcome.RUNNING
            assert state.operation_expires_at
            assert state.operation_expires_at > clock["now"]
        return result

    monkeypatch.setattr(storage, "open", shorten_claim)
    monkeypatch.setattr(ArchivePass, "_retire", retire_after_time_passes)

    outcome = sql_store.archive_project(ids.project)

    assert outcome.outcome == RetentionOutcome.SUCCEEDED
    assert sql_store.get_run(ids.run, hydrate=False).archive_bundle_id


def test_deleted_root_blocks_restore_but_keeps_archive_evidence(
    sql_store, tree_factory, archive_one_tree, storage, monkeypatch, rows
):
    """Reject queued restore while preserving the catalog and object."""
    ids = tree_factory(sql_store)
    bundle_id = archive_one_tree(sql_store, ids)
    prepared = sql_store.prepare_pipeline_run_restore(ids.run)
    assert prepared is not None
    sql_store.delete_run(ids.run)
    before = rows(sql_store)
    opened = Mock(
        side_effect=AssertionError("deleted-root restore opened storage")
    )
    with monkeypatch.context() as patch:
        patch.setattr(storage, "open", opened)
        with pytest.raises(ExecutionRetentionConflictError) as error:
            sql_store.execute_pipeline_run_restore(prepared)
    assert error.value.error_code == RetentionFailure.BUSY
    assert rows(sql_store) == before
    opened.assert_not_called()

    evidence = tree_factory(sql_store)
    evidence_bundle_id = archive_one_tree(sql_store, evidence)
    with Session(sql_store.engine) as session:
        bundle = session.get(ArchiveBundleSchema, bundle_id)
        assert bundle is not None
        assert bundle.root_run_id is None
        evidence_bundle = session.get(ArchiveBundleSchema, evidence_bundle_id)
        assert evidence_bundle is not None and evidence_bundle.uri is not None
        paths = (
            f"{evidence_bundle.uri}/manifest.json",
            f"{evidence_bundle.uri}/rows.tar.gz",
        )
    sql_store.delete_run(evidence.run)
    with Session(sql_store.engine) as session:
        evidence_bundle = session.get(ArchiveBundleSchema, evidence_bundle_id)
        assert evidence_bundle is not None
        assert evidence_bundle.root_run_id is None
        assert evidence_bundle.status == ArchiveBundleStatus.COMPLETE
    assert all(storage.exists(path) for path in paths)


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param("sql_store", id="sqlite"),
        pytest.param(
            "mysql_store", marks=pytest.mark.retention_mysql, id="mysql"
        ),
    ],
)
@pytest.mark.parametrize("expired", [False, True])
def test_claim_fencing(
    request, backend, tree_factory, storage, monkeypatch, rows, expired
):
    """A replacement generation fences an interrupted public archive pass."""
    store = request.getfixturevalue(backend)
    ids = tree_factory(store)
    bundles = select(ArchiveBundleSchema).where(
        ArchiveBundleSchema.root_run_id == ids.run
    )
    started, release = Event(), Event()
    original = storage.open

    def blocked(path, mode="r"):
        if (
            current_thread().name.startswith("stale-archive")
            and str(ids.run) in str(path)
            and str(path).endswith("rows.tar.gz")
            and mode == "wb"
        ):
            started.set()
            assert release.wait(20)
        return original(path, mode)

    monkeypatch.setattr(storage, "open", blocked)
    with ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="stale-archive"
    ) as pool:
        stale = pool.submit(store.archive_project, ids.project)
        try:
            assert started.wait(10)
            with Session(store.engine) as session:
                old = session.scalars(bundles).one()
                old_id = old.id
                if expired:
                    old.claim_expires_at = datetime(2000, 1, 1)
                    session.commit()
            replacement = store.archive_project(ids.project)
            if expired:
                assert replacement.outcome == RetentionOutcome.SUCCEEDED
                expected = rows(store)
            else:
                assert store.get_run(ids.run).archive_bundle_id is None
        finally:
            release.set()
        stale.result(timeout=10)
    if expired:
        assert rows(store) == expected
    else:
        # Competing checkpoints may fence both passes; a public retry converges.
        assert (
            store.archive_project(ids.project).outcome
            == RetentionOutcome.SUCCEEDED
        )
    with Session(store.engine) as session:
        complete = [
            b
            for b in session.scalars(bundles)
            if b.status == ArchiveBundleStatus.COMPLETE
        ]
        assert len(complete) == 1
        assert (
            session.get(PipelineRunSchema, ids.run).archive_bundle_id
            == complete[0].id
        )
        if expired:
            assert complete[0].id != old_id
            assert (
                session.get(ArchiveBundleSchema, old_id).status
                == ArchiveBundleStatus.FAILED
            )


@pytest.mark.parametrize(
    "outcome",
    [RetentionOutcome.ACCEPTED, RetentionOutcome.RUNNING],
)
@pytest.mark.parametrize("legacy", [False, True])
def test_abandoned_pass_can_be_replaced(
    sql_store, tree_factory, storage, NOW, outcome, legacy
):
    """Replace active-looking state after its operation freshness expires."""
    ids = tree_factory(sql_store)
    abandoned = sql_store.prepare_retention_pass(ids.project)
    assert abandoned.state.operation_expires_at
    assert abandoned.state.operation_expires_at > NOW
    contender = sql_store.prepare_retention_pass(ids.project)
    assert contender.state.operation_id == abandoned.operation_id
    assert contender.state.operation_id != contender.operation_id
    with Session(sql_store.engine) as session:
        project = session.get(ProjectSchema, ids.project)
        assert project and project.retention_state
        state = RetentionState.model_validate_json(project.retention_state)
        state.last_outcome = outcome
        state.operation_expires_at = (
            None if legacy else NOW - timedelta(seconds=1)
        )
        project.retention_state = state.model_dump_json()
        session.add(project)
        session.commit()

    replacement = sql_store.prepare_retention_pass(ids.project)
    assert replacement.state.operation_id == replacement.operation_id
    assert replacement.operation_id != abandoned.operation_id
    result = sql_store.execute_retention_pass(replacement)
    assert result.outcome == RetentionOutcome.SUCCEEDED
    assert sql_store.get_run(ids.run, hydrate=False).archive_bundle_id
    with Session(sql_store.engine) as session:
        project = session.get(ProjectSchema, ids.project)
        assert project and project.retention_state
        state = RetentionState.model_validate_json(project.retention_state)
        assert state.operation_expires_at is None


@pytest.mark.parametrize("failure", ["retirement", "commit_ack"])
def test_interrupted_archive(
    sql_store, tree_factory, storage, rows, monkeypatch, failure
):
    """Pre-commit failure rolls back; a lost acknowledgement remains restorable."""
    ids = tree_factory(sql_store)
    before = rows(sql_store), sql_store.get_run(ids.run).model_dump()
    complete = False
    original_commit = sql_store.engine.dialect.do_commit

    def observe(conn, cursor, statement, parameters, context, executemany):
        nonlocal complete
        if failure == "retirement" and statement.startswith(
            "DELETE FROM step_configuration"
        ):
            raise OSError("retirement interrupted")
        if (
            statement.startswith("UPDATE archive_bundle")
            and ArchiveBundleStatus.COMPLETE in parameters
        ):
            complete = True

    def commit(connection):
        nonlocal complete
        original_commit(connection)
        if complete and failure == "commit_ack":
            complete = False
            raise OSError("acknowledgement lost")

    event.listen(sql_store.engine, "before_cursor_execute", observe)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(sql_store.engine.dialect, "do_commit", commit)
            outcome = sql_store.archive_project(ids.project)
    finally:
        event.remove(sql_store.engine, "before_cursor_execute", observe)
    if failure == "retirement":
        assert outcome.outcome == RetentionOutcome.FAILED
        assert rows(sql_store) == before[0]
    else:
        assert sql_store.get_run(ids.run, hydrate=False).archive_bundle_id
        restored = sql_store.restore_pipeline_run(ids.run)
        assert restored.outcome == RetentionOutcome.SUCCEEDED
        assert sql_store.get_run(ids.run).model_dump() == before[1]


def test_cursor_advances_past_excluded_root(sql_store, tree_factory, storage):
    """Resume after an excluded root without rescanning it forever."""
    first, second = tree_factory(sql_store), tree_factory(sql_store)
    with Session(sql_store.engine) as session:
        session.add(
            PipelineRunSchema(
                project_id=first.project,
                name="pinned-child",
                root_run_id=first.run,
                parent_run_id=first.run,
                retain=True,
                status="completed",
                index=1,
                in_progress=False,
                enable_heartbeat=False,
                end_time=datetime(2025, 1, 1),
            )
        )
        session.get(PipelineRunSchema, first.run).end_time = datetime(
            2025, 1, 1
        )
        session.commit()
    sql_store.update_project(
        first.project,
        ProjectUpdate(
            retention=RetentionSettings(archive_after_days=7, max_trees=1)
        ),
    )
    first_pass = sql_store.archive_project(first.project)
    assert first_pass.outcome == RetentionOutcome.PAUSED
    assert (
        sql_store.get_run(second.run, hydrate=False).archive_bundle_id is None
    )
    second_pass = sql_store.archive_project(first.project)
    assert second_pass.outcome == RetentionOutcome.SUCCEEDED
    assert sql_store.get_run(first.run).archive_bundle_id is None
    assert (
        sql_store.get_run(second.run, hydrate=False).archive_bundle_id
        is not None
    )


def test_wait_condition_metadata_publishes_after_guarded_insert(
    sql_store, tree_factory
):
    """The guarded outer insert releases SQLite before publishing metadata."""
    ids = tree_factory(sql_store, kind="dynamic")

    condition = sql_store.create_run_wait_condition(
        RunWaitConditionRequest(
            project=ids.project,
            run=ids.run,
            name="guarded-wait",
            type=RunWaitConditionType.EXTERNAL_INPUT,
            metadata={"guarded": "value"},
        )
    )

    with Session(sql_store.engine) as session:
        metadata = session.execute(
            select(RunMetadataSchema).where(RunMetadataSchema.key == "guarded")
        ).scalar_one()
        assert metadata.value == '"value"'
        assert (
            session.execute(
                select(RunMetadataResourceSchema.resource_id).where(
                    RunMetadataResourceSchema.run_metadata_id == metadata.id
                )
            ).scalar_one()
            == condition.id
        )
