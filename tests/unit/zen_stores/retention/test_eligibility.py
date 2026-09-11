# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Table-driven retention policy, marker, and per-run eligibility rules."""

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlmodel import Session, SQLModel

from tests.unit.zen_stores.retention.fixture_graph import FROZEN_NOW as NOW
from tests.unit.zen_stores.retention.fixture_graph import seed_run
from zenml.models import (
    PipelineRunFilter,
    PipelineRunUpdate,
    PipelineSnapshotFilter,
    ProjectFilter,
    ProjectRequest,
    ProjectUpdate,
    StackFilter,
    StepRunFilter,
)
from zenml.models.v2.misc.retention import (
    RetentionRunEstimate,
    RetentionSettings,
)
from zenml.zen_stores.retention import eligibility
from zenml.zen_stores.retention.state import Cursor
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    DeploymentSchema,
    ModelSchema,
    ModelVersionPipelineRunSchema,
    ModelVersionSchema,
    PipelineBuildSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

POLICY = RetentionSettings(archive_after_days=90)


def update_record(
    store: SqlZenStore, schema: type[SQLModel], identity: UUID, **values: Any
) -> None:
    """Apply one direct eligibility mutation."""
    with Session(store.engine) as session:
        record = session.get(schema, identity)
        assert record is not None
        for name, value in values.items():
            setattr(record, name, value)
        session.add(record)
        session.commit()


def inspect(
    store: SqlZenStore, run: dict[str, UUID], policy=POLICY
) -> eligibility.ArchivableRun:
    """Inspect one run with the fixed test policy and clock."""
    with Session(store.engine) as session:
        return eligibility.inspect_run(
            session, run["project"], run["run"], policy, NOW
        )


def discover(store: SqlZenStore, project: UUID, **kwargs) -> list[UUID]:
    """Discover candidate runs with the fixed test policy and clock."""
    with Session(store.engine) as session:
        return [
            cursor.run_id
            for cursor in eligibility.discover_runs(
                session,
                project,
                kwargs.pop("policy", POLICY),
                NOW,
                kwargs.pop("after", None),
                kwargs.pop("limit", 10),
                **kwargs,
            )
        ]


def bundle_row(run: dict[str, UUID], **values: Any) -> ArchiveBundleSchema:
    """Build a bundle row for a run."""
    return ArchiveBundleSchema(
        project_id=run["project"],
        run_id=run["run"],
        uri="unused",
        size_bytes=1,
        content_hash="0" * 64,
        format_version=1,
        **values,
    )


def make_resumable(store: SqlZenStore, run: dict[str, UUID]) -> None:
    """Fail a dynamic run whose snapshot has a runnable build."""
    with Session(store.engine) as session:
        build = PipelineBuildSchema(
            project_id=run["project"],
            stack_id=store.list_stacks(StackFilter()).items[0].id,
            images="{}",
            is_local=False,
            contains_code=True,
        )
        session.add(build)
        session.flush()
        snapshot = session.get(PipelineSnapshotSchema, run["snapshot"])
        snapshot.is_dynamic, snapshot.build_id = True, build.id
        session.get(PipelineRunSchema, run["run"]).status = "failed"
        session.commit()


def test_policy_round_trip_and_validation(retention_store) -> None:
    """Policies stay disabled by default and invalid values fail early."""
    run = seed_run(retention_store, NOW)
    project = retention_store.get_project(run["project"])
    assert project.retention.archive_after_days is None
    assert retention_store.retention_dry_run(project).examined_run_count == 0
    policy = RetentionSettings(archive_after_days=180, max_runs_per_pass=20)
    retention_store.update_project(project.id, ProjectUpdate(retention=policy))
    assert retention_store.get_project(project.id).retention == policy

    for values in (
        {"archive_after_days": 6},
        {"max_runs_per_pass": 0},
        {"restored_grace_days": -1},
        {"max_bytes": 1},
    ):
        with pytest.raises(ValidationError):
            RetentionSettings(**values)


def test_archive_markers_filter_headers_and_preserve_run_pins(
    retention_store,
) -> None:
    """Public markers split header lists while run pins update explicitly."""
    project = retention_store.list_projects(ProjectFilter()).items[0].id
    live = seed_run(retention_store, NOW)
    bundle_id = uuid4()
    archived = seed_run(retention_store, NOW, bundle_id=bundle_id)
    with Session(retention_store.engine) as session:
        session.add(bundle_row(archived, id=bundle_id))
        session.commit()
    listings = {
        "run": lambda value: retention_store.list_runs(
            PipelineRunFilter(project=project, archive_bundle_id=value)
        ),
        "step": lambda value: retention_store.list_run_steps(
            StepRunFilter(project=project, archive_bundle_id=value)
        ),
        "snapshot": lambda value: retention_store.list_snapshots(
            PipelineSnapshotFilter(project=project, archive_bundle_id=value)
        ),
    }
    for name, read in listings.items():
        ids = (
            (lambda run: {run["step"], run["consumer"]})
            if name == "step"
            else (lambda run: {run[name]})
        )
        assert {item.id for item in read("isnull:").items} == ids(live)
        assert {item.id for item in read("isnotnull:").items} == ids(archived)
        assert {item.id for item in read(bundle_id).items} == ids(archived)

    assert retention_store.get_run(live["run"]).retain is False
    retention_store.update_run(live["run"], PipelineRunUpdate(retain=True))
    untouched = retention_store.update_run(
        live["run"], PipelineRunUpdate(add_tags=["x"])
    )
    assert untouched.retain is True


def test_old_finished_run_is_eligible(retention_store) -> None:
    """A finished run older than the policy age has no exclusion."""
    run = seed_run(retention_store, NOW)
    inspected = inspect(retention_store, run)
    assert inspected.exclusion is None
    assert inspected.snapshot_ids == [run["snapshot"]]
    # The run, two steps, one snapshot, and its two configurations.
    assert inspected.row_count == 6


@pytest.mark.parametrize(
    "rule,expected",
    [
        ("in_progress", "not_eligible"),
        ("running_step", "not_eligible"),
        ("running_child", "not_eligible"),
        ("not_old", "not_old"),
        ("pinned", "pinned"),
        ("model_link", "model_link"),
        ("resumable_failed", "resumable_failed"),
        ("restored_grace", "restored_grace"),
    ],
)
def test_each_exclusion(retention_store, rule: str, expected: str) -> None:
    """Each safety rule excludes a run with one stable reason."""
    run = seed_run(retention_store, NOW)
    simple = {
        "in_progress": (PipelineRunSchema, run["run"], {"in_progress": True}),
        "running_step": (StepRunSchema, run["step"], {"status": "running"}),
        "not_old": (
            PipelineRunSchema,
            run["run"],
            {"end_time": NOW - timedelta(days=90)},
        ),
        "pinned": (PipelineRunSchema, run["run"], {"retain": True}),
    }
    if mutation := simple.get(rule):
        update_record(retention_store, mutation[0], mutation[1], **mutation[2])
    if rule == "running_child":
        child = seed_run(retention_store, NOW, parent=run["run"])
        update_record(
            retention_store, PipelineRunSchema, child["run"], status="running"
        )
    if rule == "resumable_failed":
        make_resumable(retention_store, run)
    with Session(retention_store.engine) as session:
        if rule == "model_link":
            model = ModelSchema(
                project_id=run["project"],
                name=str(uuid4()),
                save_models_to_registry=False,
            )
            version = ModelVersionSchema(
                project_id=run["project"],
                model_id=model.id,
                name="v",
                number=1,
                stage="archived",
                producer_run_id_if_numeric=run["run"],
            )
            session.add_all([model, version])
            session.flush()
            session.add(
                ModelVersionPipelineRunSchema(
                    model_version_id=version.id, pipeline_run_id=run["run"]
                )
            )
        elif rule == "restored_grace":
            session.add(bundle_row(run, restored_at=NOW - timedelta(days=1)))
        session.commit()

    assert inspect(retention_store, run).exclusion == expected
    assert expected in RetentionRunEstimate.EXCLUSION_DESCRIPTIONS


@pytest.mark.parametrize("root_state", ["finished", "running", "resumable"])
def test_child_run_waits_for_its_root(retention_store, root_state) -> None:
    """A child is archived on its own once its root cannot resume it."""
    root = seed_run(retention_store, NOW)
    child = seed_run(retention_store, NOW, parent=root["run"])
    if root_state == "running":
        update_record(
            retention_store, PipelineRunSchema, root["run"], in_progress=True
        )
    elif root_state == "resumable":
        make_resumable(retention_store, root)

    expected = None if root_state == "finished" else "root_active"
    assert inspect(retention_store, child).exclusion == expected


@pytest.mark.parametrize("owner", ["shared", "deployment", "name"])
def test_snapshot_in_other_use_stays_hot(retention_store, owner: str) -> None:
    """A snapshot something else uses stays in SQL without blocking the run."""
    run, other = seed_run(retention_store, NOW), seed_run(retention_store, NOW)
    with Session(retention_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, run["snapshot"])
        if owner == "shared":
            session.get(
                PipelineRunSchema, other["run"]
            ).snapshot_id = snapshot.id
        elif owner == "deployment":
            session.add(
                DeploymentSchema(
                    project_id=run["project"],
                    name="d",
                    status="running",
                    snapshot_id=snapshot.id,
                )
            )
        else:
            snapshot.name = "named"
        session.commit()

    inspected = inspect(retention_store, run)

    assert inspected.exclusion is None
    assert inspected.snapshot_ids == []
    # The run and its two steps; the snapshot's configurations stay too.
    assert inspected.row_count == 3


@pytest.mark.parametrize("defect", ["archived_step", "foreign_project"])
def test_inconsistent_run_fails_closed(retention_store, defect: str) -> None:
    """Partial archive state and cross-project steps keep a run hot."""
    run = seed_run(retention_store, NOW)
    if defect == "archived_step":
        update_record(
            retention_store,
            StepRunSchema,
            run["step"],
            archive_bundle_id=uuid4(),
        )
    else:
        project = retention_store.create_project(
            ProjectRequest(name="other-project")
        )
        update_record(
            retention_store, StepRunSchema, run["step"], project_id=project.id
        )
    assert inspect(retention_store, run).exclusion == "not_eligible"


def test_run_over_the_record_cap_is_oversized(
    retention_store, monkeypatch
) -> None:
    """A run with more rows than one bundle holds is excluded before capture."""
    run = seed_run(retention_store, NOW)
    with Session(retention_store.engine) as session:
        session.add_all(
            StepConfigurationSchema(
                name=f"extra-{index}",
                index=index + 2,
                snapshot_id=run["snapshot"],
                config="{}",
            )
            for index in range(5)
        )
        session.commit()
    monkeypatch.setattr(eligibility, "MAX_RECORDS", 10)
    inspected = inspect(retention_store, run)
    assert inspected.row_count == 11
    assert inspected.exclusion == "oversized"


def test_discovery_skips_runs_that_need_no_inspection(retention_store) -> None:
    """Pinned, recent, model-linked, archived, and skipped runs never appear."""
    runs = {
        name: seed_run(retention_store, NOW, age=age)
        for name, age in (
            ("oldest", 130),
            ("pinned", 120),
            ("recent", 10),
            ("archived", 110),
            ("skipped", 105),
            ("newest", 100),
        )
    }
    update_record(
        retention_store, PipelineRunSchema, runs["pinned"]["run"], retain=True
    )
    update_record(
        retention_store,
        PipelineRunSchema,
        runs["archived"]["run"],
        archive_bundle_id=uuid4(),
    )
    project = runs["oldest"]["project"]

    found = discover(retention_store, project, skip=[runs["skipped"]["run"]])

    assert found == [runs["oldest"]["run"], runs["newest"]["run"]]


def test_discovery_continues_after_the_saved_position(retention_store) -> None:
    """The saved position is exclusive and ordered by end time, then ID."""
    runs = [seed_run(retention_store, NOW, age=age) for age in (120, 110, 100)]
    with Session(retention_store.engine) as session:
        first = session.get(PipelineRunSchema, runs[0]["run"])
        after = Cursor(end_time=first.end_time, run_id=first.id)
    project = runs[0]["project"]

    assert discover(retention_store, project, after=after) == [
        runs[1]["run"],
        runs[2]["run"],
    ]
    assert discover(retention_store, project, limit=1) == [runs[0]["run"]]


def test_selection_reports_whether_more_runs_follow(retention_store) -> None:
    """The dry run inspects one pass worth of runs and flags the rest."""
    runs = [seed_run(retention_store, NOW, age=age) for age in (120, 110)]
    with Session(retention_store.engine) as session:
        selection = eligibility.select_archivable_runs(
            session, runs[0]["project"], POLICY, NOW, None, 1
        )
    assert [run.run_id for run in selection.runs] == [runs[0]["run"]]
    assert selection.truncated
