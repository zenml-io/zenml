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
"""Tests of the archive foundation: capture, catalog, storage, format.

Every test drives real SQL rows and a real local archive destination and
covers one area end to end rather than one method at a time.
"""

import json
from datetime import timedelta
from pathlib import Path
from typing import Type
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlmodel import Session

from tests.unit.zen_stores.execution_archive.utils import (
    NOW,
    OLDER_THAN,
    count_statements,
    populate_family,
    substitutions_of,
)
from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES,
)
from zenml.enums import ExecutionArchiveState, ExecutionStatus
from zenml.exceptions import ArchiveUnavailableError
from zenml.models import (
    ExecutionArchiveObject,
    ProjectRequest,
    StepRunFilter,
    StepRunRequest,
)
from zenml.zen_stores.execution_archive.capture import (
    ExecutionArchiveCapturer,
)
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    compress,
    decompress,
    sha256_digest,
)
from zenml.zen_stores.execution_archive.eligibility import (
    evaluate_eligibility,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ChecksumMismatchError,
    ExecutionArchiveError,
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.models import (
    ArchiveObjectKind,
    ExecutionArchiveManifest,
)
from zenml.zen_stores.execution_archive.payload import (
    ExecutionPayload,
    SnapshotPayload,
)
from zenml.zen_stores.execution_archive.targets import ExecutionArchiveTargets
from zenml.zen_stores.schemas import (
    ExecutionArchiveStorageTargetSchema,
    PipelineRunSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

FIXTURES = Path(__file__).parent / "fixtures"


def test_capture_fingerprints_and_refuses_open_or_oversized_families(
    sql_store: SqlZenStore,
) -> None:
    """The fingerprint covers every table; open or huge families are refused.

    The preview path (`inspect`) and the size gate must never load a
    payload column: a family is judged on identities and column lengths.
    """
    family = populate_family(sql_store, steps=2)
    service = ExecutionArchiveCapturer(sql_store.engine)

    def capture():  # type: ignore[no-untyped-def]
        return service.capture(
            project_id=family.project_id, root_run_id=family.run_id
        )

    first = capture()
    assert first.family.table_counts == {
        "pipeline_run": 1,
        "step_run": 2,
        "pipeline_snapshot": 1,
        "step_configuration": 2,
    }
    assert first.family.snapshot_ids == [family.snapshot_id]
    assert first.family.stored_bytes > 0
    assert capture().source_fingerprint == first.source_fingerprint

    eligibility = evaluate_eligibility(
        first.family,
        now=NOW,
        older_than=OLDER_THAN,
        max_stored_bytes=(
            DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_FAMILY_STORED_BYTES
        ),
    )
    assert eligibility.eligible
    assert not evaluate_eligibility(
        first.family,
        now=NOW - timedelta(days=100),
        older_than=OLDER_THAN,
        max_stored_bytes=1024**3,
    ).eligible
    assert not evaluate_eligibility(
        first.family, now=NOW, older_than=OLDER_THAN, max_stored_bytes=64
    ).eligible

    with Session(sql_store.engine) as session:
        step = session.get(StepRunSchema, family.step_id)
        assert step is not None
        step.docstring = "Edited after capture."
        session.add(step)
        session.commit()
    assert capture().source_fingerprint != first.source_fingerprint

    # The size gate refuses before any payload column is read: inspection
    # touches payload columns only inside LENGTH aggregates.
    small = ExecutionArchiveCapturer(sql_store.engine, max_stored_bytes=64)
    with count_statements(sql_store, "step_configuration") as statements:
        with pytest.raises(ExecutionArchiveError, match="too large"):
            small.capture(
                project_id=family.project_id, root_run_id=family.run_id
            )
    assert statements
    assert all(
        "length(" in statement.lower()
        for statement in statements
        if "step_configuration.config" in statement
    )
    # A run outside the family that shares its snapshot keeps it in SQL.
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, family.run_id)
        assert run is not None
        session.add(
            PipelineRunSchema(
                project_id=run.project_id,
                user_id=run.user_id,
                pipeline_id=run.pipeline_id,
                snapshot_id=family.snapshot_id,
                name="archive-run-sibling",
                orchestrator_run_id=None,
                start_time=run.start_time,
                end_time=run.end_time,
                in_progress=False,
                status=ExecutionStatus.COMPLETED.value,
                orchestrator_environment=None,
                exception_info=None,
                index=2,
                enable_heartbeat=False,
                created=run.created,
                updated=run.updated,
            )
        )
        session.commit()
    with pytest.raises(ExecutionArchiveError, match="outside the family"):
        capture()


def test_catalog_owns_transitions_authority_claims_and_project_lifetime(
    sql_store: SqlZenStore,
) -> None:
    """Generations move along graph edges, one authoritative, one owner."""
    family = populate_family(sql_store)
    target_id = sql_store.execution_archive_targets.current()
    catalog = ExecutionArchiveCatalog(sql_store.engine)

    def begin(project_id, root_run_id, generation):  # type: ignore[no-untyped-def]
        return catalog.begin_export(
            project_id=project_id,
            root_run_id=root_run_id,
            generation=generation,
            source_fingerprint=str(generation) * 64,
            storage_target_id=target_id,
            stored_bytes=100,
        )

    entry = begin(family.project_id, family.run_id, 1)
    assert entry.state == ExecutionArchiveState.EXPORTING
    assert catalog.latest_for_root(family.run_id) == entry
    with Session(sql_store.engine) as session:
        assert (
            catalog.authoritative(session, root_run_ids=[family.run_id]) == []
        )

    manifest = ExecutionArchiveObject(sha256="b" * 64, stored_bytes=10)
    exported = catalog.record_objects(
        entry.id,
        manifest=manifest,
        execution=ExecutionArchiveObject(sha256="c" * 64, stored_bytes=20),
        snapshots=ExecutionArchiveObject(sha256="d" * 64, stored_bytes=30),
    )
    assert exported.manifest == manifest
    catalog.mark_verified(entry.id)
    verified = catalog.get(entry.id)
    assert verified is not None
    assert verified.state == ExecutionArchiveState.VERIFIED
    assert catalog.get(entry.id, project_id=uuid4()) is None
    with Session(sql_store.engine) as session:
        with pytest.raises(ExecutionArchiveStateError, match="cannot become"):
            catalog.transition(
                session, entry.id, ExecutionArchiveState.RESTORED
            )

    # A family has at most one authoritative generation.
    second = begin(family.project_id, family.run_id, 2)
    catalog.mark_verified(second.id)
    with Session(sql_store.engine) as session:
        catalog.transition(session, entry.id, ExecutionArchiveState.COMPACTING)
        session.commit()
    with Session(sql_store.engine) as session:
        [authoritative] = catalog.authoritative(
            session, root_run_ids=[family.run_id]
        )
        assert authoritative.id == entry.id
        with pytest.raises(ExecutionArchiveStateError, match="authoritative"):
            catalog.transition(
                session, second.id, ExecutionArchiveState.COMPACTING
            )

    # A generation has at most one live owner.
    catalog.claim(entry.id, owner="worker-a", seconds=60)
    with pytest.raises(ExecutionArchiveStateError, match="processed"):
        catalog.claim(entry.id, owner="worker-b", seconds=60)
    assert catalog.renew(entry.id, owner="worker-a", seconds=60)
    catalog.release(entry.id, owner="worker-a")
    catalog.claim(entry.id, owner="worker-b", seconds=60)
    assert not catalog.renew(entry.id, owner="worker-a", seconds=60)
    catalog.release(entry.id, owner="worker-b")

    # Catalog rows follow their project.
    project = sql_store.create_project(
        ProjectRequest(name="archive-scratch", display_name="Scratch")
    )
    root_run_id = uuid4()
    begin(project.id, root_run_id, 1)
    assert catalog.latest_for_root(root_run_id) is not None
    sql_store.delete_project(project.id)
    assert catalog.latest_for_root(root_run_id) is None


def test_configured_target_is_recorded_once_and_objects_are_verified(
    sql_store: SqlZenStore,
    bare_store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One immutable target per configuration; objects fail closed."""
    targets = sql_store.execution_archive_targets
    target_id = targets.current()
    assert targets.current() == target_id
    assert ExecutionArchiveTargets(sql_store).current() == target_id

    # A configuration change records another immutable target.
    monkeypatch.setenv(
        "ZENML_SERVER_EXECUTION_ARCHIVE_CONFIGURATION",
        json.dumps({"path": str(tmp_path / "archive-second")}),
    )
    second_id = ExecutionArchiveTargets(sql_store).current()
    assert second_id != target_id
    with Session(sql_store.engine) as session:
        rows = session.query(ExecutionArchiveStorageTargetSchema).count()
        assert rows == 2

    # Without configuration there is nothing to archive to.
    monkeypatch.delenv("ZENML_SERVER_EXECUTION_ARCHIVE_FLAVOR")
    with pytest.raises(ExecutionArchiveStateError, match="configured"):
        ExecutionArchiveTargets(sql_store).current()

    # Objects are content-addressed, deduplicated and verified on read.
    store = targets.object_store(target_id)
    scope = uuid4()
    payload = b'{"hello": "archive"}'
    first = store.put_if_absent(ArchiveObjectKind.MANIFEST, scope, payload)
    second = store.put_if_absent(ArchiveObjectKind.MANIFEST, scope, payload)
    assert first == second
    assert first.stored_bytes == len(payload)
    assert store.get_exact(ArchiveObjectKind.MANIFEST, scope, first) == payload

    [path] = (tmp_path / "archive-primary").rglob(f"{first.sha256}.json")
    path.write_bytes(b'{"hello": "corrupt"}')
    with pytest.raises(ChecksumMismatchError):
        store.get_exact(ArchiveObjectKind.MANIFEST, scope, first)
    with pytest.raises(ChecksumMismatchError):
        store.put_if_absent(ArchiveObjectKind.MANIFEST, scope, payload)
    with pytest.raises(ArchiveUnavailableError):
        store.get_exact(
            ArchiveObjectKind.MANIFEST,
            scope,
            ExecutionArchiveObject(sha256="0" * 64, stored_bytes=1),
        )


def test_step_projection_agrees_with_the_derived_configuration(
    sql_store: SqlZenStore,
) -> None:
    """Unhydrated and hydrated step listings return the same values.

    Rows created before the migration derive type and substitutions from
    the configuration; rows written by `create_run_step` carry them as
    columns. Both must agree, or the same row would answer differently
    depending on hydration.
    """
    family = populate_family(sql_store, steps=2, with_projection=False)
    with Session(sql_store.engine) as session:
        deleted = session.get(StepRunSchema, family.step_ids[1])
        assert deleted is not None
        session.delete(deleted)
        session.commit()
    created = sql_store.create_run_step(
        StepRunRequest(
            name="step-1",
            start_time=NOW,
            status=ExecutionStatus.RUNNING,
            pipeline_run_id=family.run_id,
            project=family.project_id,
        )
    )

    listed = {
        (step.name, hydrate): step
        for hydrate in (False, True)
        for step in sql_store.list_run_steps(
            StepRunFilter(pipeline_run_id=family.run_id), hydrate=hydrate
        ).items
    }
    for name in ("step-0", "step-1"):
        unhydrated, hydrated = listed[(name, False)], listed[(name, True)]
        assert unhydrated.type == hydrated.type
        assert unhydrated.substitutions == hydrated.substitutions
        assert {"date", "time"} <= set(unhydrated.substitutions)
    assert created.substitutions == listed[("step-1", False)].substitutions
    assert set(substitutions_of(NOW)) <= set(created.substitutions)


@pytest.mark.parametrize(
    "name, model_class",
    [
        ("execution_payload", ExecutionPayload),
        ("snapshot_payload", SnapshotPayload),
        ("manifest", ExecutionArchiveManifest),
    ],
)
def test_format_v1_golden_objects_stay_readable(
    name: str, model_class: Type[BaseModel]
) -> None:
    """Objects written by this version must decode and re-encode byte for byte.

    The fixtures are archives as this version writes them; a later version
    that cannot reproduce them exactly would change digests that are
    recorded in catalogs and manifests of existing archives. Compression
    is not pinned: its digest is computed at write time, so only the
    canonical bytes are an invariant.
    """
    stored = (FIXTURES / f"{name}_v1.json").read_bytes()
    digests = json.loads((FIXTURES / "digests_v1.json").read_text())

    decoded = model_class.model_validate_json(stored)
    assert canonical_json(decoded) == stored
    assert sha256_digest(stored) == digests[name]
    assert decompress(compress(stored)) == stored
