# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Public retention selection, ownership, budgets and settings scenarios."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from zenml.models import ProjectFilter, ProjectUpdate, StackFilter
from zenml.models.v2.misc.retention import (
    RetentionDryRunRequest,
    RetentionLimits,
    RetentionSettings,
)
from zenml.zen_stores.retention import eligibility
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    DeploymentSchema,
    ModelSchema,
    ModelVersionPipelineRunSchema,
    ModelVersionSchema,
    PipelineBuildSchema,
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    RunTemplateSchema,
    RunWaitConditionSchema,
    ScheduleSchema,
    StepConfigurationSchema,
    StepRunSchema,
    TriggerSchema,
    TriggerSnapshotSchema,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)

NOW = datetime(2026, 9, 8)


@pytest.fixture
def sql_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SqlZenStore:
    """Create isolated SQLite data and a fixed policy evaluation time.

    Args:
        tmp_path: Temporary test directory.
        monkeypatch: Isolated environment and dependency overrides.

    Returns:
        A SQLite store with default identities.
    """
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(tmp_path / "cfg"))
    monkeypatch.setattr(eligibility, "utc_now", lambda: NOW)
    return SqlZenStore(
        config=SqlZenStoreConfiguration(url=f"sqlite:///{tmp_path / 'db'}"),
        skip_default_registrations=False,
    )


def make_tree(
    store: SqlZenStore, parent: UUID | None = None, age: int = 100
) -> dict[str, UUID]:
    """Create valid identities with detail deliberately not decodable as models.

    Args:
        store: Isolated SQL store.
        parent: Root identity for a nested run.
        age: Execution age in days.

    Returns:
        Identities of the tree and its associated records.
    """
    project = store.list_projects(ProjectFilter()).items[0].id
    pipeline = PipelineSchema(
        project_id=project, name=str(uuid4()), run_count=0
    )
    snapshot = PipelineSnapshotSchema(
        project_id=project,
        pipeline_id=pipeline.id,
        pipeline_configuration='{"description":"é😀"}',
        client_environment="{}",
        run_name_template="t",
        step_count=1,
    )
    run = PipelineRunSchema(
        project_id=project,
        pipeline_id=pipeline.id,
        snapshot_id=snapshot.id,
        name=str(uuid4()),
        index=1,
        status="completed",
        in_progress=False,
        enable_heartbeat=False,
        end_time=NOW - timedelta(days=age),
        parent_run_id=parent,
        root_run_id=parent,
        orchestrator_environment="abc",
    )
    step = StepRunSchema(
        project_id=project,
        pipeline_run_id=run.id,
        snapshot_id=snapshot.id,
        name="step",
        version=1,
        is_retriable=False,
        status="completed",
        end_time=run.end_time,
        source_code="kept source",
        docstring="kept docs",
        exception_info="error",
    )
    config = StepConfigurationSchema(
        name="step", index=0, snapshot_id=snapshot.id, config="configuration"
    )
    with Session(store.engine, expire_on_commit=False) as session:
        session.add_all([pipeline, snapshot, run, step, config])
        session.commit()
    return dict(
        project=project,
        pipeline=pipeline.id,
        snapshot=snapshot.id,
        run=run.id,
        step=step.id,
    )


def selection(
    store: SqlZenStore, tree: dict[str, UUID], **limits: int
) -> eligibility.RetentionSelection:
    """Select with the agreed 90-day policy.

    Args:
        store: Isolated SQL store.
        tree: Identities of the candidate tree.
        **limits: Per-invocation budget overrides.

    Returns:
        The bounded selection and exclusion counts.
    """
    return store.select_archivable_trees(
        tree["project"],
        RetentionSettings(archive_after_days=90),
        RetentionLimits(**limits),
    )


def test_positive_tree_and_utf8_lengths(sql_store: SqlZenStore) -> None:
    """Header identities survive and lengths count bytes without decoding JSON.

    Args:
        sql_store: Isolated SQL store.
    """
    root = make_tree(sql_store)
    child = make_tree(sql_store, root["run"])
    result = selection(sql_store, root)
    assert not result.exclusions and not result.truncated
    tree = result.candidates[0]
    assert set(tree.tree_run_ids) == {root["run"], child["run"]}
    assert set(tree.snapshot_ids) == {root["snapshot"], child["snapshot"]}
    assert tree.tables["pipeline_snapshot"].estimated_bytes == 2 * (
        len('{"description":"é😀"}'.encode()) + 2
    )
    assert tree.tables["step_configuration"].rows_deleted == 2
    assert tree.tables["step_run"].estimated_bytes == 10
    assert tree.tables["pipeline_run"].rows_deleted == 0


@pytest.mark.parametrize(
    "status,end_time",
    [
        ("cached", None),
        ("skipped", None),
        ("completed", None),
        ("failed", None),
        ("completed", NOW - timedelta(days=90)),
        ("skipped", NOW),
    ],
)
def test_terminal_step_timestamps_do_not_set_retention_age(
    sql_store: SqlZenStore, status: str, end_time: datetime | None
) -> None:
    """Old trees remain eligible when terminal steps lack old end timestamps.

    Args:
        sql_store: Isolated SQL store.
        status: Terminal child-step status.
        end_time: Missing or recent step timestamp that must not block retention.
    """
    root = make_tree(sql_store)
    child = make_tree(sql_store, root["run"])
    with Session(sql_store.engine) as session:
        step = session.get(StepRunSchema, child["step"])
        assert step
        step.status = status
        step.end_time = end_time
        session.add(step)
        session.commit()
    result = selection(sql_store, root)
    assert not result.exclusions
    assert len(result.candidates) == 1
    assert not result.candidates[0].exclusions
    assert set(result.candidates[0].tree_run_ids) == {
        root["run"],
        child["run"],
    }


@pytest.mark.parametrize(
    "rule",
    [
        "not_terminal",
        "not_old",
        "missing_end",
        "step_not_terminal",
        "pinned",
        "unresolved_wait",
        "model_link",
        "in_progress_dependent",
        "resumable_failed_root",
        "restored_grace",
    ],
)
def test_each_exclusion_and_its_release(
    sql_store: SqlZenStore, rule: str
) -> None:
    """Each protection excludes a whole tree and explains why; removing it admits it.

    Args:
        sql_store: Isolated SQL store.
        rule: Exclusion to protect and then release.
    """
    root = make_tree(sql_store)
    child = make_tree(sql_store, root["run"])
    with Session(sql_store.engine, expire_on_commit=False) as session:
        run = session.get(PipelineRunSchema, child["run"])
        root_run = session.get(PipelineRunSchema, root["run"])
        assert run and root_run
        removable = None
        if rule == "not_terminal":
            run.in_progress = True
        elif rule == "not_old":
            run.end_time = NOW - timedelta(days=90)
        elif rule == "missing_end":
            run.end_time = None
        elif rule == "pinned":
            run.retain = True
        elif rule == "step_not_terminal":
            step = session.get(StepRunSchema, child["step"])
            assert step
            step.status = "running"
            session.add(step)
        elif rule == "unresolved_wait":
            removable = RunWaitConditionSchema(
                run_id=run.id,
                project_id=root["project"],
                name="wait",
                type="external_input",
                status="pending",
            )
        elif rule == "model_link":
            model = ModelSchema(
                project_id=root["project"],
                name=str(uuid4()),
                save_models_to_registry=False,
            )
            version = ModelVersionSchema(
                project_id=root["project"],
                model_id=model.id,
                name="v",
                number=1,
                stage="archived",
                producer_run_id_if_numeric=run.id,
            )
            session.add_all([model, version])
            session.flush()
            removable = ModelVersionPipelineRunSchema(
                model_version_id=version.id, pipeline_run_id=run.id
            )
        elif rule == "in_progress_dependent":
            removable = PipelineRunSchema(
                project_id=root["project"],
                name=str(uuid4()),
                index=2,
                status="running",
                in_progress=True,
                enable_heartbeat=False,
                original_run_id=run.id,
            )
        elif rule == "resumable_failed_root":
            stack = sql_store.list_stacks(StackFilter()).items[0].id
            build = PipelineBuildSchema(
                project_id=root["project"],
                stack_id=stack,
                images="{}",
                is_local=False,
                contains_code=True,
            )
            session.add(build)
            session.flush()
            snapshot = session.get(PipelineSnapshotSchema, root["snapshot"])
            assert snapshot
            snapshot.is_dynamic = True
            snapshot.build_id = build.id
            session.add(snapshot)
            root_run.status = "failed"
        elif rule == "restored_grace":
            removable = ArchiveBundleSchema(
                project_id=root["project"],
                root_run_id=root_run.id,
                uri="unused",
                size_bytes=0,
                row_counts="{}",
                manifest_hash="x",
                format_version=1,
                schema_revision="test",
                status="restored",
                restored_at=NOW - timedelta(days=1),
            )
        session.add_all([run, root_run])
        if removable is not None:
            session.add(removable)
        session.commit()
    expected = "not_old" if rule == "missing_end" else rule
    result = selection(sql_store, root)
    assert result.exclusions[expected] == 1
    if rule == "model_link":
        allowed = sql_store.select_archivable_trees(
            root["project"],
            RetentionSettings(
                archive_after_days=90, archive_model_linked_runs=True
            ),
            RetentionLimits(),
        )
        assert not allowed.exclusions
    assert (
        expected
        in next(
            t for t in result.candidates if t.root_run_id == root["run"]
        ).exclusions
    )
    with Session(sql_store.engine, expire_on_commit=False) as session:
        if removable is not None:
            session.delete(session.merge(removable))
        run = session.get(PipelineRunSchema, child["run"])
        assert run
        run.in_progress = False
        run.retain = False
        run.end_time = NOW - timedelta(days=100)
        step = session.get(StepRunSchema, child["step"])
        assert step
        step.status = "completed"
        root_run = session.get(PipelineRunSchema, root["run"])
        assert root_run
        root_run.status = "completed"
        session.add_all([run, step, root_run])
        session.commit()
    assert not selection(sql_store, root).candidates[0].exclusions


@pytest.mark.parametrize(
    "owner",
    [
        "shared",
        "deployment",
        "template",
        "name",
        "child_snapshot",
        "schedule",
        "trigger",
    ],
)
def test_snapshot_ownership_keeps_tree_eligible(
    sql_store: SqlZenStore, owner: str
) -> None:
    """Operational/shared snapshots stay hot without blocking unrelated detail.

    Args:
        sql_store: Isolated SQL store.
        owner: Reference that keeps snapshot detail in SQL.
    """
    root = make_tree(sql_store)
    other = make_tree(sql_store, age=1)
    with Session(sql_store.engine, expire_on_commit=False) as session:
        snapshot = session.get(PipelineSnapshotSchema, root["snapshot"])
        assert snapshot
        if owner == "shared":
            run = session.get(PipelineRunSchema, other["run"])
            assert run
            run.snapshot_id = snapshot.id
            session.add(run)
        elif owner == "deployment":
            session.add(
                DeploymentSchema(
                    project_id=root["project"],
                    name="d",
                    status="running",
                    snapshot_id=snapshot.id,
                )
            )
        elif owner == "template":
            session.add(
                RunTemplateSchema(
                    project_id=root["project"],
                    name="t",
                    source_snapshot_id=snapshot.id,
                )
            )
        elif owner == "name":
            snapshot.name = "named"
        elif owner == "schedule":
            schedule = ScheduleSchema(
                project_id=root["project"],
                name="s",
                active=True,
                catchup=False,
            )
            session.add(schedule)
            session.flush()
            snapshot.schedule_id = schedule.id
        elif owner == "trigger":
            trigger = TriggerSchema(
                project_id=root["project"],
                name="t",
                active=True,
                type="schedule",
                flavor="native",
                configuration="{}",
                concurrency="skip",
            )
            session.add(trigger)
            session.flush()
            session.add(
                TriggerSnapshotSchema(
                    trigger_id=trigger.id, snapshot_id=snapshot.id
                )
            )
        else:
            child = session.get(PipelineSnapshotSchema, other["snapshot"])
            assert child
            child.source_snapshot_id = snapshot.id
            session.add(child)
        session.add(snapshot)
        session.commit()
    tree = selection(sql_store, root).candidates[0]
    assert not tree.exclusions and not tree.snapshot_ids
    assert tree.tables["step_configuration"].rows == 0
    assert tree.retained_details["snapshot_ownership"] == 1


def test_metadata_all_links_and_policy_override(
    sql_store: SqlZenStore,
) -> None:
    """Adding a step link keeps both the metadata value and every link hot.

    Args:
        sql_store: Isolated SQL store.
    """
    root = make_tree(sql_store)
    with Session(sql_store.engine, expire_on_commit=False) as session:
        value = RunMetadataSchema(
            project_id=root["project"], key="metric", type="str", value="123"
        )
        session.add(value)
        session.flush()
        session.add(
            RunMetadataResourceSchema(
                resource_id=root["run"],
                resource_type="pipeline_run",
                run_metadata_id=value.id,
            )
        )
        session.commit()
        value_id = value.id
    assert selection(sql_store, root).candidates[0].metadata_ids == [value_id]
    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(
            RunMetadataResourceSchema(
                resource_id=root["step"],
                resource_type="step_run",
                run_metadata_id=value_id,
            )
        )
        session.commit()
    retained = selection(sql_store, root)
    assert not retained.candidates[0].metadata_ids
    assert retained.retained_details["metadata_ownership"] == 1


@pytest.mark.parametrize(
    "limits,reason",
    [
        ({"max_trees": 1}, None),
        ({"max_rows": 1}, "row_limit"),
        ({"max_bytes": 1}, "byte_limit"),
    ],
)
def test_limits_never_admit_partial_trees(
    sql_store: SqlZenStore, limits: dict[str, int], reason: str | None
) -> None:
    """Bounds truncate discovery or reject a whole tree with an explicit reason.

    Args:
        sql_store: Isolated SQL store.
        limits: Per-invocation budget overrides.
        reason: Expected rejection reason.
    """
    root = make_tree(sql_store, age=110)
    make_tree(sql_store)
    result = selection(sql_store, root, **limits)
    assert result.truncated and len(result.candidates) == 1
    assert result.candidates[0].root_run_id == root["run"]
    if reason:
        assert (
            result.exclusions[reason] == 1 and not result.candidates[0].tables
        )


def test_settings_round_trip_and_dry_run_does_not_enable(
    sql_store: SqlZenStore,
) -> None:
    """What-if defaults and settings writes never start or alter executions.

    Args:
        sql_store: Isolated SQL store.
    """
    root = make_tree(sql_store)
    assert (
        sql_store.get_project(root["project"]).retention.archive_after_days
        is None
    )
    report = sql_store.retention_dry_run(
        root["project"], RetentionDryRunRequest()
    )
    assert (
        report.effective_policy.archive_after_days == 90
        and report.eligible_tree_count == 1
    )
    assert (
        sql_store.get_project(root["project"]).retention.archive_after_days
        is None
    )
    policy = RetentionSettings(archive_after_days=180, max_trees=20)
    sql_store.update_project(root["project"], ProjectUpdate(retention=policy))
    assert sql_store.get_project(root["project"]).retention == policy
    assert not sql_store.select_archivable_trees(
        root["project"], RetentionSettings(), RetentionLimits()
    ).candidates


@pytest.mark.parametrize(
    "values",
    [
        {"archive_after_days": 6},
        {"max_trees": 0},
        {"max_rows": -1},
        {"max_bytes": 0},
        {"restored_grace_days": -1},
    ],
)
def test_invalid_policy(values: dict[str, int]) -> None:
    """Invalid settings are rejected before any store access.

    Args:
        values: Invalid policy values.
    """
    with pytest.raises(ValidationError):
        RetentionSettings(**values)


def test_latest_bundle_and_exact_grace_boundary(
    sql_store: SqlZenStore,
) -> None:
    """Old restore history does not override the newest bundle's grace state.

    Args:
        sql_store: Isolated SQL store.
    """
    root = make_tree(sql_store)
    with Session(sql_store.engine, expire_on_commit=False) as session:
        old = ArchiveBundleSchema(
            project_id=root["project"],
            root_run_id=root["run"],
            uri="unused",
            size_bytes=0,
            row_counts="{}",
            manifest_hash="x",
            format_version=1,
            schema_revision="test",
            status="restored",
            created=NOW - timedelta(days=60),
            restored_at=NOW - timedelta(days=1),
        )
        latest = ArchiveBundleSchema(
            project_id=root["project"],
            root_run_id=root["run"],
            uri="unused",
            size_bytes=0,
            row_counts="{}",
            manifest_hash="x",
            format_version=1,
            schema_revision="test",
            status="restored",
            created=NOW - timedelta(days=40),
            restored_at=NOW - timedelta(days=30),
        )
        session.add_all([old, latest])
        session.commit()
    assert not selection(sql_store, root).exclusions


@pytest.mark.parametrize("defect", ["incomplete_tree", "archived_step"])
def test_malformed_or_partially_archived_tree_stays_hot(
    sql_store: SqlZenStore, defect: str
) -> None:
    """Broken membership and archived members cannot become fresh candidates.

    Args:
        sql_store: Isolated SQL store.
        defect: Malformed ownership or archive state.
    """
    root = make_tree(sql_store)
    child = make_tree(sql_store, root["run"])
    with Session(sql_store.engine) as session:
        if defect == "incomplete_tree":
            run = session.get(PipelineRunSchema, child["run"])
            assert run
            run.root_run_id = None
            session.add(run)
        else:
            step = session.get(StepRunSchema, child["step"])
            assert step
            step.archived_at = NOW
            session.add(step)
        session.commit()
    assert selection(sql_store, root).exclusions[defect] == 1


@pytest.mark.parametrize(
    "is_local,has_stack", [(False, True), (True, True), (False, False)]
)
def test_runnable_sql_predicate_matches_reader(
    sql_store: SqlZenStore, is_local: bool, has_stack: bool
) -> None:
    """Resume eligibility and the existing reader use the same runnable contract.

    Args:
        sql_store: Isolated SQL store.
        is_local: Whether the build runs locally.
        has_stack: Whether a build has an execution stack.
    """
    from sqlalchemy import select
    from sqlmodel import col

    root = make_tree(sql_store)
    stack = (
        sql_store.list_stacks(StackFilter()).items[0].id if has_stack else None
    )
    with Session(sql_store.engine) as session:
        build = PipelineBuildSchema(
            project_id=root["project"],
            stack_id=stack,
            images="{}",
            is_local=is_local,
            contains_code=True,
        )
        session.add(build)
        session.flush()
        snapshot = session.get(PipelineSnapshotSchema, root["snapshot"])
        assert snapshot
        snapshot.build_id = build.id
        session.add(snapshot)
        session.commit()
        matching = (
            session.execute(
                select(col(PipelineSnapshotSchema.id)).where(
                    PipelineSnapshotSchema.runnable_filter()
                )
            )
            .scalars()
            .all()
        )
        assert (
            (snapshot.id in matching)
            == snapshot.is_runnable
            == (not is_local and has_stack)
        )


def test_settings_migration_preserves_disabled_project(
    sql_store: SqlZenStore,
) -> None:
    """The SQLite upgrade adds nullable settings to a pre-R3 project unchanged.

    Args:
        sql_store: Isolated SQL store.
    """
    from sqlalchemy import inspect

    from zenml.zen_stores.migrations.alembic import Alembic

    tree = make_tree(sql_store)
    project = sql_store.list_projects(ProjectFilter()).items[0]
    before = sql_store.get_project(project.id)
    migration = Alembic(sql_store.engine)
    migration.downgrade("7a1c3d9e2b4f")
    assert "retention_settings" not in {
        c["name"] for c in inspect(sql_store.engine).get_columns("project")
    }
    migration.upgrade("8b2d4e6f901a")
    after = sql_store.get_project(project.id)
    assert after.updated == before.updated
    assert after.retention == RetentionSettings()
    column = next(
        c
        for c in inspect(sql_store.engine).get_columns("project")
        if c["name"] == "retention_settings"
    )
    assert column["nullable"]
    with Session(sql_store.engine) as session:
        assert session.get(PipelineRunSchema, tree["run"]) is not None
        assert session.get(StepRunSchema, tree["step"]) is not None
        assert (
            session.get(PipelineSnapshotSchema, tree["snapshot"]) is not None
        )


def test_project_boundary_is_fail_closed(sql_store: SqlZenStore) -> None:
    """Foreign project members cannot contribute their identities or bytes.

    Args:
        sql_store: Isolated SQL store.
    """
    from zenml.models import ProjectRequest

    root = make_tree(sql_store)
    child = make_tree(sql_store, root["run"])
    other = sql_store.create_project(ProjectRequest(name="other-project"))
    assert not sql_store.select_archivable_trees(
        other.id, RetentionSettings(archive_after_days=90), RetentionLimits()
    ).candidates
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, child["run"])
        assert run
        run.project_id = other.id
        session.add(run)
        session.commit()
    result = selection(sql_store, root)
    assert result.exclusions["project_mismatch"] == 1
    assert not result.candidates[0].tables


@pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="SQLite connection limit API requires Python 3.11",
)
def test_large_tree_with_sqlite_parameter_limit(
    sql_store: SqlZenStore,
) -> None:
    """A valid bounded tree works with SQLite's historical 999-variable limit.

    Args:
        sql_store: Isolated SQL store.
    """
    import sqlite3

    root = make_tree(sql_store)
    with Session(sql_store.engine) as session:
        session.add_all(
            [
                PipelineRunSchema(
                    project_id=root["project"],
                    name=str(uuid4()),
                    index=i,
                    status="completed",
                    in_progress=False,
                    enable_heartbeat=False,
                    parent_run_id=root["run"],
                    root_run_id=root["run"],
                    end_time=NOW - timedelta(days=100),
                )
                for i in range(80)
            ]
        )
        session.commit()
    with sql_store.engine.connect() as connection:
        raw = connection.connection.driver_connection
        previous = raw.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 999)
    try:
        result = selection(sql_store, root)
        assert not result.exclusions
        assert len(result.candidates[0].tree_run_ids) == 81
    finally:
        raw.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, previous)
