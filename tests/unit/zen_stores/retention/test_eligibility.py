# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Table-driven retention policy, marker, and per-run eligibility rules."""

from datetime import timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from sqlmodel import Session, SQLModel

from zenml.config.server_config import ArchiveSettings
from zenml.models import (
    StackFilter,
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
    PipelineSnapshotSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

SETTINGS = ArchiveSettings(backend="local", uri="/tmp", after_days=90)


def update_record(
    store: SqlZenStore, schema: type[SQLModel], identity: UUID, **values: Any
) -> None:
    """Apply one direct eligibility mutation."""
    with store.engine.begin() as connection:
        connection.execute(
            update(schema).where(schema.id == identity).values(**values)
        )


def inspect(
    store: SqlZenStore, run, now, settings=SETTINGS, force=False
) -> eligibility.ArchivableRun:
    """Inspect one run with the fixed test settings and clock."""
    with Session(store.engine) as session:
        return eligibility.inspect_run(
            session, run.run, settings, now, force=force
        )


def make_resumable(store: SqlZenStore, run) -> None:
    """Fail a dynamic run whose snapshot has a runnable build."""
    with Session(store.engine) as session:
        build = PipelineBuildSchema(
            project_id=run.project,
            stack_id=store.list_stacks(StackFilter()).items[0].id,
            images="{}",
            is_local=False,
            contains_code=True,
        )
        session.add(build)
        session.flush()
        snapshot = session.get(PipelineSnapshotSchema, run.snapshot)
        snapshot.is_dynamic, snapshot.build_id = True, build.id
        session.get(PipelineRunSchema, run.run).status = "failed"
        session.commit()


@pytest.mark.parametrize(
    "rule,expected",
    [
        ("eligible", None),
        ("in_progress", "not_eligible"),
        ("running_step", "not_eligible"),
        ("running_child", "not_eligible"),
        ("not_old", "not_old"),
        ("model_link", "model_link"),
        ("resumable_failed", "resumable_failed"),
        ("restored_grace", "restored_grace"),
    ],
)
def test_each_exclusion(
    retention_store, run_factory, NOW, rule: str, expected: Optional[str]
) -> None:
    """Each safety rule excludes a run with one stable reason."""
    run = run_factory(retention_store)
    simple = {
        "in_progress": (PipelineRunSchema, run.run, {"in_progress": True}),
        "running_step": (StepRunSchema, run.producer, {"status": "running"}),
        "not_old": (
            PipelineRunSchema,
            run.run,
            {"end_time": NOW - timedelta(days=90)},
        ),
    }
    if mutation := simple.get(rule):
        update_record(retention_store, mutation[0], mutation[1], **mutation[2])
    if rule == "running_child":
        child = run_factory(retention_store, parent=run.run)
        update_record(
            retention_store, PipelineRunSchema, child.run, status="running"
        )
    if rule == "resumable_failed":
        make_resumable(retention_store, run)
    with Session(retention_store.engine) as session:
        if rule == "model_link":
            model = ModelSchema(
                project_id=run.project,
                name=str(uuid4()),
                save_models_to_registry=False,
            )
            version = ModelVersionSchema(
                project_id=run.project,
                model_id=model.id,
                name="v",
                number=1,
                stage="archived",
                producer_run_id_if_numeric=run.run,
            )
            session.add_all([model, version])
            session.flush()
            session.add(
                ModelVersionPipelineRunSchema(
                    model_version_id=version.id, pipeline_run_id=run.run
                )
            )
        elif rule == "restored_grace":
            session.add(
                ArchiveBundleSchema(
                    project_id=run.project,
                    run_id=run.run,
                    uri="unused",
                    size_bytes=1,
                    content_hash="0" * 64,
                    format_version=1,
                    restored_at=NOW - timedelta(days=1),
                )
            )
        session.commit()

    inspected = inspect(retention_store, run, NOW)

    assert inspected.exclusion == expected
    if expected is None:
        assert inspected.snapshot_ids == [run.snapshot]
        # The run, two steps, one snapshot, and its two configurations.
        assert inspected.row_count == 6


@pytest.mark.parametrize("root_state", ["finished", "running", "resumable"])
def test_child_run_waits_for_its_root(
    retention_store, run_factory, NOW, root_state
) -> None:
    """A child is archived on its own once its root cannot resume it."""
    root = run_factory(retention_store)
    child = run_factory(retention_store, parent=root.run)
    if root_state == "running":
        update_record(
            retention_store, PipelineRunSchema, root.run, in_progress=True
        )
    elif root_state == "resumable":
        make_resumable(retention_store, root)

    expected = None if root_state == "finished" else "root_active"
    assert inspect(retention_store, child, NOW).exclusion == expected


@pytest.mark.parametrize("owner", ["shared", "deployment", "name"])
def test_snapshot_in_other_use_stays_hot(
    retention_store, run_factory, NOW, owner: str
) -> None:
    """A snapshot something else uses stays in SQL without blocking the run."""
    run, other = run_factory(retention_store), run_factory(retention_store)
    with Session(retention_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, run.snapshot)
        if owner == "shared":
            session.get(PipelineRunSchema, other.run).snapshot_id = snapshot.id
        elif owner == "deployment":
            session.add(
                DeploymentSchema(
                    project_id=run.project,
                    name="d",
                    status="running",
                    snapshot_id=snapshot.id,
                )
            )
        else:
            snapshot.name = "named"
        session.commit()

    inspected = inspect(retention_store, run, NOW)

    assert inspected.exclusion is None
    assert inspected.snapshot_ids == []
    # The run and its two steps; the snapshot's configurations stay too.
    assert inspected.row_count == 3


def test_run_over_the_record_cap_is_oversized(
    retention_store, run_factory, NOW, monkeypatch
) -> None:
    """A run with more rows than one bundle holds is excluded before capture."""
    run = run_factory(retention_store)
    monkeypatch.setattr(eligibility, "MAX_RECORDS", 5)
    assert inspect(retention_store, run, NOW).exclusion == "oversized"
