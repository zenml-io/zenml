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
"""Contract tests for the inert execution archive foundation."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlmodel import Session

from tests.unit.zen_stores.execution_archive.utils import (
    NOW,
    populate_family,
    substitutions_of,
)
from zenml.config.server_config import ServerConfiguration
from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES,
)
from zenml.enums import ExecutionStatus
from zenml.exceptions import (
    ArchiveUnavailableError,
    ExecutionArchiveRestoreRequiredError,
)
from zenml.models import StepRunFilter, StepRunRequest
from zenml.zen_stores.execution_archive import codec
from zenml.zen_stores.execution_archive.codec import (
    canonical_json,
    compress,
    decompress,
    sha256_digest,
)
from zenml.zen_stores.execution_archive.exceptions import (
    ExecutionArchiveStateError,
)
from zenml.zen_stores.execution_archive.payload import (
    ExecutionArchivePayload,
    parse_execution_archive_payload,
)
from zenml.zen_stores.execution_archive.storage import (
    build_execution_archive_storage,
)
from zenml.zen_stores.execution_archive_utils import (
    archived_payload_id,
    archived_payload_placeholder,
    require_active_payload,
)
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

FIXTURE = Path(__file__).parent / "fixtures" / "archive_payload_v1.json"
FIXTURE_SHA256 = (
    "c169b4ca27e49e9deebfdad1bec3f0e8d362ebecec3b36972ebb1110c9c24094"
)


def test_archive_format_v1_is_stable_and_size_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Version-one objects stay readable and reject oversized decoding."""
    stored = FIXTURE.read_bytes().rstrip(b"\n")
    payload = parse_execution_archive_payload(stored)

    assert canonical_json(payload) == stored
    assert sha256_digest(stored) == FIXTURE_SHA256
    assert decompress(compress(stored)) == stored

    unsupported = stored.replace(
        b'"schema_version":1', b'"schema_version":2', 1
    )
    with pytest.raises(ArchiveUnavailableError, match="schema version"):
        parse_execution_archive_payload(unsupported)

    changed_v1 = stored.replace(
        b'"generation":1', b'"future_field":null,"generation":1', 1
    )
    with pytest.raises(ArchiveUnavailableError, match="versioned schema"):
        parse_execution_archive_payload(changed_v1)

    monkeypatch.setattr(
        codec,
        "DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES",
        8,
    )
    with pytest.raises(ValueError, match="decompression limit"):
        compress(b"123456789")
    with pytest.raises(ValueError, match="decompression limit"):
        decompress(codec.gzip.compress(b"123456789"))


def test_archive_storage_isolates_fenced_write_attempts(
    tmp_path: Path,
) -> None:
    """Distinct claim tokens can never overwrite each other's bytes."""
    workspace_id = uuid4()
    project_id = uuid4()
    archive_id = uuid4()
    config = ServerConfiguration(
        execution_archive_flavor="local",
        execution_archive_configuration={"path": str(tmp_path)},
        execution_archive_path_prefix="history",
    )
    storage = build_execution_archive_storage(
        config, workspace_id=workspace_id
    )
    key = storage.object_key(
        project_id=project_id, archive_id=archive_id, claim_token=1
    )
    newer_key = storage.object_key(
        project_id=project_id, archive_id=archive_id, claim_token=2
    )
    encoded = canonical_json({"archive": str(archive_id)})
    compressed = compress(encoded)

    object_ = storage.write_verified(
        key, compressed, decoded_bytes=len(encoded)
    )
    assert storage.read_verified(key, object_) == compressed
    assert f"/workspaces/{workspace_id}/projects/{project_id}/" in key
    assert key.endswith(f"/{archive_id}/1.json.gz")
    assert newer_key != key

    Path(key).write_bytes(b"corrupt")
    with pytest.raises(ArchiveUnavailableError):
        storage.read_verified(key, object_)

    oversized = object_.model_copy(
        update={
            "stored_bytes": (
                DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES
                + 1024 * 1024
                + 1
            )
        }
    )
    with pytest.raises(
        ArchiveUnavailableError, match="compressed object limit"
    ):
        storage.read_verified(key, oversized)

    storage.write_verified(key, compressed, decoded_bytes=len(encoded))
    storage.write_verified(newer_key, compressed, decoded_bytes=len(encoded))
    unrelated_key = (
        Path(
            storage.generation_prefix(
                project_id=project_id, archive_id=archive_id
            )
        )
        / "manifest.json"
    )
    unrelated_key.write_bytes(b"unrelated")
    storage.delete_other_attempts(newer_key)

    assert not Path(key).exists()
    assert Path(newer_key).exists()
    assert unrelated_key.exists()

    storage.delete(newer_key)
    storage.delete(newer_key)


def test_archive_target_is_explicit_stable_and_optional(
    tmp_path: Path,
) -> None:
    """Storage identity follows immutable config and an absent target is inert."""
    workspace_id = uuid4()
    config = ServerConfiguration(
        execution_archive_flavor="local",
        execution_archive_configuration={"path": str(tmp_path)},
        execution_archive_path_prefix="history",
    )

    first = build_execution_archive_storage(config, workspace_id=workspace_id)
    second = build_execution_archive_storage(config, workspace_id=workspace_id)
    assert first.target_digest == second.target_digest
    assert first.target_digest == sha256_digest(
        canonical_json(
            {
                "flavor": "local",
                "configuration": {"path": str(tmp_path)},
                "path_prefix": "history",
                "workspace_id": str(workspace_id),
            }
        )
    )

    changed = config.model_copy(
        update={"execution_archive_path_prefix": "other-history"}
    )
    assert (
        build_execution_archive_storage(
            changed, workspace_id=workspace_id
        ).target_digest
        != first.target_digest
    )

    with pytest.raises(ExecutionArchiveStateError, match="configured"):
        build_execution_archive_storage(
            ServerConfiguration(), workspace_id=workspace_id
        )


def test_compacted_payload_marker_requires_an_explicit_restore() -> None:
    """A compacted value carries the generation needed by client tooling."""
    archive_id = uuid4()
    marker = archived_payload_placeholder(archive_id)

    assert archived_payload_id(marker) == archive_id
    assert archived_payload_id("ordinary JSON") is None
    with pytest.raises(ExecutionArchiveRestoreRequiredError) as error:
        require_active_payload("ordinary JSON", marker)
    assert error.value.archive_id == archive_id


def test_hot_list_views_survive_while_full_payload_requires_restore(
    sql_store: SqlZenStore,
) -> None:
    """Compaction does not break summaries or pretend full payload is hot."""
    family = populate_family(sql_store)
    archive_id = uuid4()
    marker = archived_payload_placeholder(archive_id)

    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, family.run_id)
        snapshot = session.get(PipelineSnapshotSchema, family.snapshot_id)
        step = session.get(StepRunSchema, family.step_id)
        assert run is not None
        assert snapshot is not None
        assert step is not None
        run.orchestrator_environment = marker
        snapshot.pipeline_configuration = marker
        step.docstring = marker
        session.add_all([run, snapshot, step])
        session.commit()

        assert run.to_model(include_metadata=False).metadata is None
        assert snapshot.to_model(include_metadata=False).metadata is None
        assert step.to_model(include_metadata=False).metadata is None
        for schema in (run, snapshot, step):
            with pytest.raises(ExecutionArchiveRestoreRequiredError) as error:
                schema.to_model(include_metadata=True)
            assert error.value.archive_id == archive_id


def test_foundation_migration_keeps_archive_identity_after_project_deletion(
    sql_store: SqlZenStore,
) -> None:
    """Catalog ownership is logical and adds no mutable target table."""
    inspector = inspect(sql_store.engine)

    assert "execution_archive" in inspector.get_table_names()
    assert (
        "execution_archive_storage_target" not in inspector.get_table_names()
    )
    assert not inspector.get_foreign_keys("execution_archive")
    assert "claim_token" in {
        column["name"] for column in inspector.get_columns("execution_archive")
    }
    assert "source_updated_at" in {
        column["name"] for column in inspector.get_columns("execution_archive")
    }
    assert "execution_archive_id" in {
        column["name"] for column in inspector.get_columns("pipeline_run")
    }
    assert "execution_archive_target_digest" in {
        column["name"] for column in inspector.get_columns("server_settings")
    }
    assert "ix_execution_archive_state_updated_id" in {
        index["name"] for index in inspector.get_indexes("execution_archive")
    }
    assert "execution_archive_id" in {
        column["name"] for column in inspector.get_columns("pipeline_snapshot")
    }


def test_step_list_projection_matches_hydrated_configuration(
    sql_store: SqlZenStore,
) -> None:
    """Compaction-safe list fields preserve existing step-list behavior."""
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
    assert created.substitutions == listed[("step-1", False)].substitutions
    assert set(substitutions_of(NOW)) <= set(created.substitutions)
