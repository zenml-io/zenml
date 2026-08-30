#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests of manual export, verification and maintenance passes.

SQL stays authoritative throughout: an export ends `VERIFIED` and nothing
clears payload from the database.
"""

from datetime import timedelta
from typing import Optional

import pytest
from sqlmodel import Session, select

from tests.unit.zen_stores.execution_archive.service import (
    FaultyStores,
    archiver,
)
from tests.unit.zen_stores.execution_archive.utils import (
    OLD,
    OLDER_THAN,
    Family,
    archive_row,
    count_statements,
    populate_family,
)
from zenml.enums import ExecutionArchiveState
from zenml.models import (
    ExecutionArchiveMaintenanceRequest,
    ExecutionArchiveResponse,
)
from zenml.zen_stores.execution_archive import (
    maintenance as maintenance_module,
)
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.exceptions import (
    ExecutionArchiveError,
    ExecutionArchiveParityError,
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.maintenance import (
    ExecutionArchiveMaintainer,
)
from zenml.zen_stores.schemas import (
    ExecutionArchiveSchema,
    PipelineSnapshotSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _export(
    store: SqlZenStore,
    family: Family,
    stores: Optional[FaultyStores] = None,
    **kwargs: object,
) -> ExecutionArchiveResponse:
    return archiver(store, stores, **kwargs).export(
        project_id=family.project_id,
        root_run_id=family.run_id,
        older_than=OLDER_THAN,
    )


def _request(
    family: Family, **kwargs: object
) -> ExecutionArchiveMaintenanceRequest:
    return ExecutionArchiveMaintenanceRequest(
        project=family.project_id, root_run_ids=[family.run_id], **kwargs
    )


def test_export_verifies_objects_and_never_touches_sql(
    sql_store: SqlZenStore,
) -> None:
    """Exports end verified and idempotent; SQL keeps its payload."""
    family = populate_family(sql_store, steps=2)

    first = _export(sql_store, family)
    second = _export(sql_store, family)
    assert first.id == second.id
    assert second.state == ExecutionArchiveState.VERIFIED
    assert second.manifest is not None
    assert second.execution_payload is not None
    assert second.snapshot_payload is not None
    assert second.stored_bytes and second.stored_bytes > 0
    assert archive_row(sql_store).compacted_at is None
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None
        assert snapshot.source_code == 'print("pipeline")'
        assert snapshot.execution_archive_id is None

    # An oversized family is refused before anything is read or written.
    oversized = populate_family(sql_store, suffix="-oversized")
    with pytest.raises(ExecutionArchiveError, match="too large"):
        _export(sql_store, oversized, max_stored_bytes=16)
    with Session(sql_store.engine) as session:
        assert len(session.exec(select(ExecutionArchiveSchema)).all()) == 1


def test_payload_change_during_export_fails_closed(
    sql_store: SqlZenStore,
) -> None:
    """SQL edited between export and verification keeps its value."""
    family = populate_family(sql_store)

    def mutate() -> None:
        with Session(sql_store.engine) as session:
            snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
            assert snapshot is not None
            snapshot.source_code = 'print("changed")'
            snapshot.updated = OLD + timedelta(hours=1)
            session.add(snapshot)
            session.commit()

    with pytest.raises(ExecutionArchiveParityError):
        _export(
            sql_store, family, FaultyStores(sql_store, before_manifest=mutate)
        )

    failed = archive_row(sql_store)
    assert failed.state == ExecutionArchiveState.FAILED.value
    assert failed.last_error
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None
        assert snapshot.source_code == 'print("changed")'

    # The changed family is archived again as a new generation.
    retried = _export(sql_store, family)
    assert retried.state == ExecutionArchiveState.VERIFIED
    assert retried.generation == 2


def test_maintenance_previews_applies_and_lists(
    sql_store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dry run reads no payload; an apply ends verified, SQL untouched."""
    family = populate_family(sql_store)
    maintenance = ExecutionArchiveMaintainer(sql_store)

    with count_statements(sql_store, "step_configuration") as statements:
        [preview] = maintenance.preview(_request(family))
    assert preview.eligible
    assert preview.stored_bytes and preview.stored_bytes > 0
    assert all(
        "length(" in statement.lower()
        for statement in statements
        if "step_configuration.config" in statement
    )
    assert maintenance.list_archives(project_id=family.project_id) == []

    [applied] = maintenance.apply(_request(family))
    assert applied.archive_state == ExecutionArchiveState.VERIFIED
    assert applied.archive_id is not None
    with Session(sql_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None and snapshot.source_code is not None
        assert snapshot.execution_archive_id is None

    [again] = maintenance.apply(_request(family))
    assert again.archive_id == applied.archive_id
    listed = maintenance.list_archives(
        project_id=family.project_id, state=ExecutionArchiveState.VERIFIED
    )
    assert [archive.id for archive in listed] == [applied.archive_id]
    assert (
        maintenance.get_archive(
            applied.archive_id, project_id=family.project_id
        )
        == listed[0]
    )
    assert (
        maintenance.get_archive(applied.archive_id, project_id=family.run_id)
        is None
    )
    discovered = maintenance.preview(
        ExecutionArchiveMaintenanceRequest(project=family.project_id)
    )
    assert [candidate.root_run_id for candidate in discovered] == [
        family.run_id
    ]

    # A family too large to archive is reported, not attempted.
    monkeypatch.setattr(
        maintenance_module,
        "DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES",
        16,
    )
    big = populate_family(sql_store, suffix="-big")
    [blocked] = maintenance.preview(_request(big))
    assert not blocked.eligible
    assert "too large" in " ".join(blocked.blockers)


def test_a_claimed_generation_refuses_a_second_worker(
    sql_store: SqlZenStore,
) -> None:
    """Workers claim a generation before touching it."""
    family = populate_family(sql_store)
    verified = _export(sql_store, family)
    catalog = ExecutionArchiveCatalog(sql_store.engine)
    catalog.claim(verified.id, owner="another-worker", seconds=600)

    with pytest.raises(ExecutionArchiveStateError, match="processed"):
        _export(sql_store, family)

    catalog.release(verified.id, owner="another-worker")
    assert _export(sql_store, family).state == ExecutionArchiveState.VERIFIED
