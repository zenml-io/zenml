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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Product-policy, coordination, and purge tests for execution archiving."""

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect
from sqlmodel import Session, select

from tests.unit.zen_stores.execution_archive.service import (
    CallbackStorage,
    authority,
    exporter,
    local_storage,
)
from tests.unit.zen_stores.execution_archive.utils import (
    NOW,
    OLD,
    populate_family,
)
from zenml.config.server_config import ServerConfiguration
from zenml.enums import ExecutionArchiveMode, ExecutionArchiveState
from zenml.exceptions import (
    ExecutionArchiveNotEligibleError,
    ExecutionArchiveStateError,
)
from zenml.models import (
    ExecutionArchiveExportRequest,
    ExecutionArchivePolicy,
    ProjectRequest,
)
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.coordination import (
    ExecutionArchiveCoordination,
)
from zenml.zen_stores.execution_archive.coordinator import (
    ExecutionArchiveCoordinator,
)
from zenml.zen_stores.execution_archive.purger import ExecutionArchivePurger
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    ServerSettingsSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _config(
    tmp_path: Path, *, compaction: bool = False
) -> ServerConfiguration:
    return ServerConfiguration(
        execution_archive_flavor="local",
        execution_archive_configuration={"path": str(tmp_path)},
        execution_archive_path_prefix="execution-archive",
        execution_archive_compaction_enabled=compaction,
        execution_archive_scan_limit=100,
        execution_archive_work_limit=10,
        execution_archive_time_budget=60,
        execution_archive_lease_seconds=120,
    )


def _coordinator(
    store: SqlZenStore,
    tmp_path: Path,
    *,
    compaction: bool = False,
    scan_limit: int = 100,
) -> ExecutionArchiveCoordinator:
    return ExecutionArchiveCoordinator(
        store=store,
        config=_config(tmp_path, compaction=compaction),
        storage=local_storage(store, tmp_path),
        clock=lambda: NOW,
        owner="test-coordinator",
        scan_limit=scan_limit,
        work_limit=10,
        time_budget=60,
        lease_seconds=120,
        compaction_enabled=compaction,
    )


def test_product_policy_schema_is_installed(sql_store: SqlZenStore) -> None:
    """A fresh store has the policy, lease, cursor, and traversal index."""
    inspector = inspect(sql_store.engine)
    settings_columns = {
        column["name"] for column in inspector.get_columns("server_settings")
    }
    assert {
        "execution_archive_mode",
        "execution_archive_retention_days",
        "execution_archive_cursor_completed_at",
        "execution_archive_cursor_root_run_id",
        "execution_archive_coordinator_owner",
        "execution_archive_coordinator_token",
        "execution_archive_coordinator_expires_at",
        "execution_archive_last_pass",
    } <= settings_columns
    candidate_index = next(
        index
        for index in inspector.get_indexes("pipeline_run")
        if index["name"] == "ix_pipeline_run_archive_candidates"
    )
    assert candidate_index["column_names"] == [
        "execution_archive_id",
        "end_time",
        "id",
    ]


def test_policy_is_disabled_by_default_and_changes_fence_a_pass(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A policy update is atomic and invalidates an older coordinator."""
    coordination = ExecutionArchiveCoordination(
        sql_store.engine,
        workspace_id=sql_store.get_deployment_id(),
        config=_config(tmp_path),
        clock=lambda: NOW,
    )

    assert coordination.get_policy() == ExecutionArchivePolicy()
    claim = coordination.try_claim(owner="old-worker", lease_seconds=60)
    assert claim is not None

    policy = ExecutionArchivePolicy(
        mode=ExecutionArchiveMode.ARCHIVE, retention_days=90
    )
    assert coordination.update_policy(policy) == policy
    assert coordination.cursor() == (None, None)
    with pytest.raises(ExecutionArchiveStateError, match="newer"):
        coordination.renew(claim, lease_seconds=60)

    current = coordination.try_claim(owner="current-worker", lease_seconds=60)
    assert current is not None
    coordination.release(current)
    coordination.release(current)
    assert coordination.try_claim(owner="next-worker", lease_seconds=60)


def test_fenced_pass_result_is_discarded_without_failing_maintenance(
    sql_store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A policy change wins over a stale pass result at the final fence."""
    coordinator = _coordinator(sql_store, tmp_path)
    coordination = coordinator.coordination
    original_finish = coordination.finish

    def finish_after_policy_change(*args: Any, **kwargs: Any) -> None:
        coordination.update_policy(
            ExecutionArchivePolicy(mode=ExecutionArchiveMode.EXPORT)
        )
        original_finish(*args, **kwargs)

    monkeypatch.setattr(coordination, "finish", finish_after_policy_change)

    assert coordinator.run_once() is None
    assert coordination.status().last_pass is None


def test_finish_error_is_not_masked_by_release_failure(
    sql_store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Best-effort lease cleanup preserves the original database error."""
    coordinator = _coordinator(sql_store, tmp_path)
    coordination = coordinator.coordination

    def fail_finish(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("could not save pass result")

    def fail_release(*args: Any, **kwargs: Any) -> None:
        raise ValueError("could not release lease")

    monkeypatch.setattr(coordination, "finish", fail_finish)
    monkeypatch.setattr(coordination, "release", fail_release)

    with pytest.raises(RuntimeError, match="could not save pass result"):
        coordinator.run_once()


def test_status_tolerates_a_stale_cached_result(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Monitoring remains available when cached pass JSON is unreadable."""
    with Session(sql_store.engine) as session:
        settings = session.exec(select(ServerSettingsSchema)).one()
        settings.execution_archive_last_pass = '{"started_at":"invalid"}'
        session.add(settings)
        session.commit()

    status = _coordinator(sql_store, tmp_path).coordination.status()

    assert status.storage_configured
    assert status.last_pass is None


def test_status_validates_storage_without_touching_objects(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Status validates the target locally without creating its path."""
    archive_root = tmp_path / "not-created"
    coordination = ExecutionArchiveCoordination(
        sql_store.engine,
        workspace_id=sql_store.get_deployment_id(),
        config=_config(archive_root),
        clock=lambda: NOW,
    )

    status = coordination.status()

    assert status.storage_configured
    assert status.workspace_prefix is not None
    assert str(archive_root) in status.workspace_prefix
    assert not archive_root.exists()


def test_status_rejects_target_change_while_archives_exist(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Status exposes a target change that existing archives would reject."""
    tree = populate_family(sql_store)
    exporter(sql_store, tmp_path).export(
        project_id=tree.project_id, root_run_id=tree.run_id
    )
    changed_target = ExecutionArchiveCoordination(
        sql_store.engine,
        workspace_id=sql_store.get_deployment_id(),
        config=_config(tmp_path / "different-target"),
        clock=lambda: NOW,
    )

    status = changed_target.status()

    assert not status.storage_configured
    assert status.workspace_prefix is None


def test_archive_policy_respects_the_deployment_compaction_gate(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Archive mode exports first and compacts only behind the safety gate."""
    family = populate_family(sql_store)
    export_only = _coordinator(sql_store, tmp_path)
    export_only.coordination.update_policy(
        ExecutionArchivePolicy(mode=ExecutionArchiveMode.ARCHIVE)
    )

    first = export_only.run_once()

    assert first is not None and first.exported_trees == 1
    archive = ExecutionArchiveCatalog(sql_store.engine).latest_for_root(
        family.run_id
    )
    assert archive is not None
    assert archive.state == ExecutionArchiveState.VERIFIED
    assert (
        export_only.coordination.status().effective_mode
        == ExecutionArchiveMode.EXPORT
    )

    second = _coordinator(sql_store, tmp_path, compaction=True).run_once()

    assert second is not None and second.compacted_trees == 1
    archive = ExecutionArchiveCatalog(sql_store.engine).require(archive.id)
    assert archive.state == ExecutionArchiveState.COLD
    assert archive.requires_restore

    third = _coordinator(sql_store, tmp_path, compaction=True).run_once()

    assert third is not None and third.scanned_trees == 0


def test_manual_export_is_safe_but_compaction_honors_workspace_policy(
    sql_store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manual export is a probe; first-time compaction remains policy-bound."""
    config = _config(tmp_path, compaction=True)
    monkeypatch.setattr(
        ServerConfiguration,
        "get_server_config",
        staticmethod(lambda: config),
    )
    family = populate_family(sql_store)

    archive = sql_store.export_execution_archive(
        ExecutionArchiveExportRequest(
            project_id=family.project_id, root_run_id=family.run_id
        )
    )

    assert archive.state == ExecutionArchiveState.VERIFIED
    with pytest.raises(ExecutionArchiveStateError, match="policy"):
        sql_store.compact_execution_archive(
            archive_id=archive.id, project_id=family.project_id
        )

    sql_store.update_execution_archive_policy(
        ExecutionArchivePolicy(
            mode=ExecutionArchiveMode.ARCHIVE, retention_days=365
        )
    )
    with pytest.raises(
        ExecutionArchiveNotEligibleError, match="retention period"
    ):
        sql_store.compact_execution_archive(
            archive_id=archive.id, project_id=family.project_id
        )

    sql_store.update_execution_archive_policy(
        ExecutionArchivePolicy(
            mode=ExecutionArchiveMode.ARCHIVE, retention_days=180
        )
    )
    compacted = sql_store.compact_execution_archive(
        archive_id=archive.id, project_id=family.project_id
    )

    assert compacted.state == ExecutionArchiveState.COLD


def test_shutdown_between_export_and_compaction_resumes_safely(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A shutdown after export leaves a verified generation to resume."""
    tree = populate_family(sql_store)
    stopping = False

    def request_stop() -> None:
        nonlocal stopping
        stopping = True

    coordinator = ExecutionArchiveCoordinator(
        store=sql_store,
        config=_config(tmp_path, compaction=True),
        storage=CallbackStorage(
            local_storage(sql_store, tmp_path), request_stop
        ),
        clock=lambda: NOW,
        owner="stopping-coordinator",
        scan_limit=100,
        work_limit=10,
        time_budget=60,
        lease_seconds=120,
        compaction_enabled=True,
    )
    coordinator.coordination.update_policy(
        ExecutionArchivePolicy(mode=ExecutionArchiveMode.ARCHIVE)
    )

    result = coordinator.run_once(stop_requested=lambda: stopping)

    archive = ExecutionArchiveCatalog(sql_store.engine).latest_for_root(
        tree.run_id
    )
    assert result is not None
    assert result.exported_trees == 1
    assert result.compacted_trees == 0
    assert result.candidate_scan_incomplete
    assert archive is not None
    assert archive.state == ExecutionArchiveState.VERIFIED

    resumed = _coordinator(sql_store, tmp_path, compaction=True).run_once()

    assert resumed is not None and resumed.compacted_trees == 1
    assert (
        ExecutionArchiveCatalog(sql_store.engine).require(archive.id).state
        == ExecutionArchiveState.COLD
    )


def test_catalog_activity_cannot_hide_a_source_change(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Fresh lease timestamps never substitute for the source watermark."""
    family = populate_family(sql_store)
    coordinator = _coordinator(sql_store, tmp_path)
    coordinator.coordination.update_policy(
        ExecutionArchivePolicy(mode=ExecutionArchiveMode.EXPORT)
    )
    assert coordinator.run_once() is not None
    catalog = ExecutionArchiveCatalog(sql_store.engine)
    first = catalog.latest_for_root(family.run_id)
    assert first is not None
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None
        snapshot.source_code = 'print("changed")'
        snapshot.updated = OLD + timedelta(days=1)
        session.add(snapshot)
        session.commit()
    claim = catalog.claim(first.id, owner="catalog-reader", lease_seconds=60)
    catalog.release(claim)

    result = coordinator.run_once()

    second = catalog.latest_for_root(family.run_id)
    assert result is not None and result.exported_trees == 1
    assert second is not None and second.generation == first.generation + 1
    assert second.source_updated_at == OLD + timedelta(days=1)


def test_export_policy_rechecks_a_verified_generation_after_storage_failure(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A transient verification error is retried even when SQL is unchanged."""
    family = populate_family(sql_store)
    coordinator = _coordinator(sql_store, tmp_path)
    coordinator.coordination.update_policy(
        ExecutionArchivePolicy(mode=ExecutionArchiveMode.EXPORT)
    )
    assert coordinator.run_once() is not None
    catalog = ExecutionArchiveCatalog(sql_store.engine)
    archive = catalog.latest_for_root(family.run_id)
    assert archive is not None
    with Session(sql_store.engine) as session:
        row = session.get(ExecutionArchiveSchema, archive.id)
        assert row is not None
        row.last_error = "temporary object-store outage"
        session.add(row)
        session.commit()

    result = coordinator.run_once()

    retried = catalog.require(archive.id)
    assert result is not None and result.exported_trees == 1
    assert retried.last_error is None


def test_fair_cursor_advances_past_a_blocked_family(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """One permanently blocked family cannot starve newer candidates."""
    blocked = populate_family(sql_store, suffix="-blocked")
    eligible = populate_family(sql_store, suffix="-eligible")
    with Session(sql_store.engine) as session:
        blocked_run = session.get(PipelineRunSchema, blocked.run_id)
        snapshot = session.get(PipelineSnapshotSchema, blocked.snapshot_id)
        assert blocked_run is not None and snapshot is not None
        blocked_run.end_time = OLD - timedelta(days=1)
        snapshot.name = "still-operational"
        session.add_all([blocked_run, snapshot])
        session.commit()
    coordinator = _coordinator(sql_store, tmp_path, scan_limit=1)
    coordinator.coordination.update_policy(
        ExecutionArchivePolicy(mode=ExecutionArchiveMode.EXPORT)
    )

    first = coordinator.run_once()
    second = coordinator.run_once()

    assert first is not None and first.blocked_trees == 1
    assert second is not None and second.exported_trees == 1
    assert (
        ExecutionArchiveCatalog(sql_store.engine).latest_for_root(
            eligible.run_id
        )
        is not None
    )


def test_project_deletion_queues_then_purges_its_archive(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Database deletion stays local while object deletion is retryable."""
    project = sql_store.create_project(ProjectRequest(name="archived-project"))
    family = populate_family(
        sql_store, project_id=project.id, suffix="-deleted-project"
    )
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    catalog = ExecutionArchiveCatalog(sql_store.engine)
    object_path = Path(catalog.object_key(archive.id))
    assert object_path.exists()
    abandoned_attempt = object_path.parent / "abandoned.json.gz"
    abandoned_attempt.write_bytes(b"incomplete")

    sql_store.delete_project(project.id)

    pending = catalog.require(archive.id)
    assert pending.purge_pending_at is not None
    assert object_path.exists()
    purger = ExecutionArchivePurger(
        sql_store.engine,
        storage=local_storage(sql_store, tmp_path),
        owner="test-purger",
    )
    purger.purge(archive.id)
    assert catalog.get(archive.id) is None
    assert not object_path.exists()
    assert not abandoned_attempt.exists()


def test_authoritative_archive_cannot_be_purged_from_a_live_project(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """Manual purge never deletes the only authoritative payload copy."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    authority(sql_store, tmp_path).compact(
        archive_id=archive.id, project_id=family.project_id
    )

    with pytest.raises(ExecutionArchiveStateError, match="Restore"):
        ExecutionArchivePurger(sql_store.engine).request(
            archive_id=archive.id, project_id=family.project_id
        )


def test_purge_pending_generation_cannot_become_authoritative(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A purge request wins its race with a later authority switch."""
    family = populate_family(sql_store)
    archive = exporter(sql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    ExecutionArchivePurger(sql_store.engine).request(
        archive_id=archive.id, project_id=family.project_id
    )

    with pytest.raises(ExecutionArchiveStateError, match="queued for purge"):
        authority(sql_store, tmp_path).compact(
            archive_id=archive.id, project_id=family.project_id
        )

    current = ExecutionArchiveCatalog(sql_store.engine).require(archive.id)
    assert current.state == ExecutionArchiveState.VERIFIED
    assert not current.requires_restore


def test_export_does_not_revive_a_purge_pending_generation(
    sql_store: SqlZenStore, tmp_path: Path
) -> None:
    """An explicit export creates a new generation beside a queued purge."""
    family = populate_family(sql_store)
    service = exporter(sql_store, tmp_path)
    archived = service.export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    ExecutionArchivePurger(sql_store.engine).request(
        archive_id=archived.id, project_id=family.project_id
    )

    replacement = service.export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    assert replacement.id != archived.id
    assert replacement.generation == archived.generation + 1
    assert replacement.purge_pending_at is None
    assert (
        ExecutionArchiveCatalog(sql_store.engine)
        .require(archived.id)
        .purge_pending_at
        is not None
    )
