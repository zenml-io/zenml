# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Table-driven retention policy, marker, and eligibility guarantees."""

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlmodel import Session, SQLModel

from tests.unit.zen_stores.retention.fixture_graph import FROZEN_NOW as NOW
from tests.unit.zen_stores.retention.fixture_graph import seed_tree
from zenml.enums import ArchiveBundleStatus
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
from zenml.models.v2.misc.retention import RetentionLimits, RetentionSettings
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
    RunMetadataResourceSchema,
    RunMetadataSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


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


def select_trees(
    store: SqlZenStore, project: UUID, **limits: int
) -> eligibility.RetentionSelection:
    """Select with the fixed 90-day test policy."""
    with Session(store.engine) as session:
        return eligibility.select_archivable_trees(
            session,
            project,
            RetentionSettings(archive_after_days=90),
            RetentionLimits(**limits),
            now=NOW,
        )


def restored_bundle(
    tree: dict[str, UUID], *, status: str = "restored", age: int = 1
) -> ArchiveBundleSchema:
    """Build authoritative restore history relative to the fixed clock."""
    return ArchiveBundleSchema(
        project_id=tree["project"],
        root_run_id=tree["run"],
        uri="unused",
        size_bytes=0,
        manifest_hash="x",
        format_version=1,
        status=status,
        created=NOW - timedelta(days=age),
        restored_at=(
            NOW - timedelta(days=age) if status == "restored" else None
        ),
    )


def test_policy_round_trip_validation_and_required_preview(sql_store) -> None:
    """Policies stay disabled by default and invalid bounds fail early."""
    root = seed_tree(sql_store, NOW)
    project = sql_store.get_project(root["project"])
    assert project.retention.archive_after_days is None
    assert sql_store.retention_dry_run(project).eligible_tree_count == 0
    policy = RetentionSettings(archive_after_days=180, max_trees=20)
    sql_store.update_project(project.id, ProjectUpdate(retention=policy))
    project = sql_store.get_project(project.id)
    assert project.retention == policy
    assert sql_store.retention_dry_run(project).eligible_tree_count == 0

    for values in (
        {"archive_after_days": 6},
        {"max_trees": 0},
        {"max_rows": -1},
        {"max_bytes": 0},
        {"restored_grace_days": -1},
    ):
        with pytest.raises(ValidationError):
            RetentionSettings(**values)

    from zenml.zen_stores.zen_store_interface import ZenStoreInterface

    assert "retention_dry_run" in ZenStoreInterface.__abstractmethods__


def test_archive_markers_filter_headers_and_preserve_run_pins(
    sql_store,
) -> None:
    """Public markers split header lists while run pins update explicitly."""
    project = sql_store.list_projects(ProjectFilter()).items[0].id
    bundle = ArchiveBundleSchema(
        project_id=project,
        uri="s3://archive/bundle",
        size_bytes=1,
        manifest_hash="sha256:0",
        format_version=1,
        status=ArchiveBundleStatus.COMPLETE,
    )
    with Session(sql_store.engine) as session:
        session.add(bundle)
        session.commit()
        session.refresh(bundle)
    live = seed_tree(sql_store, NOW)
    archived = seed_tree(sql_store, NOW, bundle_id=bundle.id)
    listings = {
        "run": lambda value: sql_store.list_runs(
            PipelineRunFilter(project=project, archive_bundle_id=value)
        ),
        "step": lambda value: sql_store.list_run_steps(
            StepRunFilter(project=project, archive_bundle_id=value)
        ),
        "snapshot": lambda value: sql_store.list_snapshots(
            PipelineSnapshotFilter(project=project, archive_bundle_id=value)
        ),
    }
    for name, read in listings.items():
        live_ids = (
            {live["step"], live["consumer"]}
            if name == "step"
            else {live[name]}
        )
        cold_ids = (
            {archived["step"], archived["consumer"]}
            if name == "step"
            else {archived[name]}
        )
        assert {item.id for item in read("isnull:").items} == live_ids
        assert {item.id for item in read("isnotnull:").items} == cold_ids
        assert {item.id for item in read(bundle.id).items} == cold_ids

    assert sql_store.get_run(live["run"]).retain is False
    sql_store.update_run(live["run"], PipelineRunUpdate(retain=True))
    untouched = sql_store.update_run(
        live["run"], PipelineRunUpdate(add_tags=["x"])
    )
    assert untouched.retain is True


def test_pending_bundle_allows_an_incomplete_descriptor(sql_store) -> None:
    """A pending claim exists before its storage descriptor is known."""
    pending = ArchiveBundleSchema(
        project_id=sql_store.list_projects(ProjectFilter()).items[0].id,
        format_version=1,
        status=ArchiveBundleStatus.PENDING,
    )
    with Session(sql_store.engine) as session:
        session.add(pending)
        session.commit()
        session.refresh(pending)
        assert (pending.uri, pending.size_bytes, pending.manifest_hash) == (
            None,
            None,
            None,
        )


@pytest.mark.parametrize(
    "rule,expected",
    [
        ("not_terminal", "not_eligible"),
        ("not_old", "not_old"),
        ("pinned", "pinned"),
        ("model_link", "model_link"),
        ("in_progress_dependent", "in_progress_dependent"),
        ("resumable_failed_root", "resumable_failed_root"),
        ("restored_grace", "restored_grace"),
    ],
)
def test_each_exclusion_family(sql_store, rule: str, expected: str) -> None:
    """Each safety rule excludes the whole tree with one stable reason."""
    root = seed_tree(sql_store, NOW)
    child = seed_tree(sql_store, NOW, root["run"])
    simple = {
        "not_terminal": (
            PipelineRunSchema,
            child["run"],
            {"in_progress": True},
        ),
        "not_old": (
            PipelineRunSchema,
            child["run"],
            {"end_time": NOW - timedelta(days=90)},
        ),
        "pinned": (
            PipelineRunSchema,
            child["run"],
            {"retain": True},
        ),
        "resumable_failed_root": (
            PipelineRunSchema,
            root["run"],
            {"status": "failed"},
        ),
    }
    if mutation := simple.get(rule):
        update_record(sql_store, mutation[0], mutation[1], **mutation[2])

    with Session(sql_store.engine) as session:
        if rule == "model_link":
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
                producer_run_id_if_numeric=child["run"],
            )
            session.add_all([model, version])
            session.flush()
            session.add(
                ModelVersionPipelineRunSchema(
                    model_version_id=version.id,
                    pipeline_run_id=child["run"],
                )
            )
        elif rule == "in_progress_dependent":
            session.add(
                PipelineRunSchema(
                    project_id=root["project"],
                    name=str(uuid4()),
                    index=2,
                    status="running",
                    in_progress=True,
                    enable_heartbeat=False,
                    original_run_id=child["run"],
                )
            )
        elif rule == "resumable_failed_root":
            build = PipelineBuildSchema(
                project_id=root["project"],
                stack_id=sql_store.list_stacks(StackFilter()).items[0].id,
                images="{}",
                is_local=False,
                contains_code=True,
            )
            session.add(build)
            session.flush()
            snapshot = session.get(PipelineSnapshotSchema, root["snapshot"])
            assert snapshot is not None
            snapshot.is_dynamic, snapshot.build_id = True, build.id
        elif rule == "restored_grace":
            session.add(restored_bundle(root))
        session.commit()

    candidate = select_trees(sql_store, root["project"]).candidates[0]
    assert candidate.exclusion == expected
    assert set(candidate.tree_run_ids) == {root["run"], child["run"]}


def test_overlapping_exclusions_report_one_reason(sql_store) -> None:
    """Reason precedence stays stable when multiple protections apply."""
    root = seed_tree(sql_store, NOW)
    update_record(
        sql_store,
        PipelineRunSchema,
        root["run"],
        retain=True,
        in_progress=True,
    )
    assert (
        select_trees(sql_store, root["project"]).candidates[0].exclusion
        == "pinned"
    )


@pytest.mark.parametrize(
    "owner",
    ["shared", "deployment", "name"],
)
def test_snapshot_ownership_stays_hot(sql_store, owner: str) -> None:
    """Shared and operational snapshots remain in SQL without blocking the tree."""
    root, other = seed_tree(sql_store, NOW), seed_tree(sql_store, NOW, age=1)
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, root["snapshot"])
        assert snapshot is not None
        if owner == "shared":
            run = session.get(PipelineRunSchema, other["run"])
            assert run is not None
            run.snapshot_id = snapshot.id
        elif owner == "deployment":
            session.add(
                DeploymentSchema(
                    project_id=root["project"],
                    name="d",
                    status="running",
                    snapshot_id=snapshot.id,
                )
            )
        else:
            snapshot.name = "named"
        session.commit()
    candidate = select_trees(sql_store, root["project"]).candidates[0]
    assert candidate.exclusion is None
    assert not candidate.snapshot_ids
    assert candidate.retained_details["snapshot_ownership"] == 1


def test_grace_uses_latest_authoritative_restore(sql_store) -> None:
    """New attempts cannot hide grace, while its exact boundary expires."""
    root = seed_tree(sql_store, NOW)
    with Session(sql_store.engine) as session:
        old = restored_bundle(root, age=30)
        old.created = NOW - timedelta(days=40)
        session.add_all([old, restored_bundle(root, status="pending")])
        session.commit()
    assert (
        select_trees(sql_store, root["project"]).candidates[0].exclusion
        is None
    )


@pytest.mark.parametrize(
    "defect", ["incomplete_tree", "archived_step", "foreign_project"]
)
def test_malformed_membership_fails_closed(sql_store, defect: str) -> None:
    """Partial archive state and cross-project tree membership stay hot."""
    root = seed_tree(sql_store, NOW)
    child = seed_tree(sql_store, NOW, root["run"])
    if defect == "incomplete_tree":
        update_record(
            sql_store, PipelineRunSchema, child["run"], root_run_id=None
        )
    elif defect == "archived_step":
        update_record(
            sql_store,
            StepRunSchema,
            child["step"],
            archive_bundle_id=uuid4(),
        )
    else:
        project = sql_store.create_project(
            ProjectRequest(name="other-project")
        )
        update_record(
            sql_store, PipelineRunSchema, child["run"], project_id=project.id
        )
    assert (
        select_trees(sql_store, root["project"]).candidates[0].exclusion
        == "not_eligible"
    )


def test_fixed_estimate_excludes_hot_metadata(sql_store) -> None:
    """Only archived detail rows consume the fixed-weight budget."""
    root = seed_tree(sql_store, NOW)
    baseline = select_trees(sql_store, root["project"]).candidates[0]
    with Session(sql_store.engine) as session:
        value = RunMetadataSchema(
            project_id=root["project"],
            key="metric",
            type="str",
            value="123",
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
    actual = select_trees(sql_store, root["project"]).candidates[0]
    assert (actual.row_count, actual.estimated_bytes) == (
        baseline.row_count,
        baseline.estimated_bytes,
    )
    assert "metadata_ownership" not in actual.retained_details


@pytest.mark.parametrize(
    "limits,reason,count,truncated",
    [
        ({"max_trees": 1}, None, 1, True),
        ({"max_rows": 1}, "row_limit", 1, True),
        ({"max_bytes": 1}, "byte_limit", 2, False),
    ],
)
def test_invocation_limits_never_split_trees(
    sql_store,
    limits: dict[str, int],
    reason: str | None,
    count: int,
    truncated: bool,
) -> None:
    """Discovery and size bounds return whole trees with explicit reasons."""
    first = seed_tree(sql_store, NOW, age=110)
    seed_tree(sql_store, NOW)
    result = select_trees(sql_store, first["project"], **limits)
    assert len(result.candidates) == count and result.truncated is truncated
    assert result.candidates[0].exclusion == reason


@pytest.mark.parametrize(
    "ceiling,extra", [("row_limit", 9_995), ("byte_limit", 2_043)]
)
def test_bundle_format_ceiling(sql_store, ceiling: str, extra: int) -> None:
    """Invocation capacity never admits an indivisible format-oversized tree."""
    root = seed_tree(sql_store, NOW)
    with Session(sql_store.engine) as session:
        session.add_all(
            StepConfigurationSchema(
                name=f"extra-{index}",
                index=index + 2,
                snapshot_id=root["snapshot"],
                config="{}",
            )
            for index in range(extra)
        )
        session.commit()
    assert (
        select_trees(sql_store, root["project"]).candidates[0].exclusion
        == ceiling
    )


def test_preview_continues_after_oversize_then_stops_at_pass_budget(
    sql_store,
) -> None:
    """Per-tree oversize continues scanning; aggregate exhaustion pauses it."""
    oldest = seed_tree(sql_store, NOW, age=120)
    middle = seed_tree(sql_store, NOW, age=110)
    latest = seed_tree(sql_store, NOW, age=100)
    with Session(sql_store.engine) as session:
        session.add_all(
            StepConfigurationSchema(
                name=f"extra-{index}",
                index=index + 2,
                snapshot_id=oldest["snapshot"],
                config="{}",
            )
            for index in range(3)
        )
        session.commit()
    result = select_trees(sql_store, oldest["project"], max_bytes=64 * 1024)
    assert [tree.root_run_id for tree in result.candidates] == [
        oldest["run"],
        middle["run"],
        latest["run"],
    ]
    assert [tree.exclusion for tree in result.candidates] == [
        "byte_limit",
        None,
        "pass_budget",
    ]
    assert result.truncated


def test_self_referencing_root_is_canonical(sql_store) -> None:
    """Both persisted root encodings identify the same eligible tree."""
    root = seed_tree(sql_store, NOW)
    update_record(
        sql_store,
        PipelineRunSchema,
        root["run"],
        root_run_id=root["run"],
    )
    candidate = select_trees(sql_store, root["project"]).candidates[0]
    assert candidate.root_run_id == root["run"] and candidate.exclusion is None
