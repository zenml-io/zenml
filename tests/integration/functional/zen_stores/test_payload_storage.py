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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""End-to-end checks of execution payload storage.

The clean client's SQLite store offloads every payload to the database. The
tests run real pipelines and store calls against it, and remove or alter the
stored bytes of blobs to cover what offloading can break: responses that differ
from inline ones, execution paths that stop working when payloads cannot be
read, half-created runs and corrupted blobs.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, delete, select

from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.exceptions import PayloadIntegrityError
from zenml.models import (
    PipelineRequest,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.payload_storage import PayloadStorageConfiguration
from zenml.zen_stores.schemas import (
    BlobContentSchema,
    BlobSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

PAYLOAD_SCHEMAS = [
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
    PipelineRunSchema,
]


@step
def load(value: int = 3) -> int:
    """Load a value."""
    return value


@step
def train(value: int) -> int:
    """Double a value."""
    return value * 2


@pipeline(enable_cache=False)
def static_pipeline() -> None:
    """A static pipeline."""
    train(load())


@pipeline(dynamic=True, enable_cache=False)
def child_pipeline(value: int) -> int:
    """A child pipeline."""
    return train(value)


@pipeline(dynamic=True, enable_cache=False)
def dynamic_pipeline() -> None:
    """A dynamic pipeline with dynamic steps and a child run."""
    value = load()
    for _ in range(2):
        train(value)
    child_pipeline(value.load())


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """The store of a clean client, which offloads payloads to its database."""
    zen_store = clean_client.zen_store
    assert isinstance(zen_store, SqlZenStore)
    assert zen_store.payload_store.offload_enabled
    return zen_store


def _open_store(store: SqlZenStore, **payload_storage: Any) -> SqlZenStore:
    """Open another store on the same database, with its own cache."""
    settings = {**store.config.payload_storage.model_dump(), **payload_storage}
    config = store.config.model_copy(
        update={"payload_storage": PayloadStorageConfiguration(**settings)},
        deep=True,
    )
    return SqlZenStore(config=config, skip_default_registrations=True)


def _hydrated_responses(store: SqlZenStore) -> Dict[str, Any]:
    """Every hydrated run, step, snapshot and run DAG of the project."""
    project = Client().active_project.id
    responses: Dict[str, Any] = {}
    for run in store.list_runs(
        PipelineRunFilter(project=project, size=1000)
    ).items:
        responses[f"run:{run.id}"] = store.get_run(run.id).model_dump(
            mode="json"
        )
        responses[f"dag:{run.id}"] = store.get_pipeline_run_dag(
            run.id
        ).model_dump(mode="json")
    for step_run in store.list_run_steps(
        StepRunFilter(project=project, size=1000)
    ).items:
        responses[f"step:{step_run.id}"] = store.get_run_step(
            step_run.id
        ).model_dump(mode="json")
    for snapshot in store.list_snapshots(
        PipelineSnapshotFilter(project=project, size=1000)
    ).items:
        responses[f"snapshot:{snapshot.id}"] = store.get_snapshot(
            snapshot.id
        ).model_dump(mode="json")
    return responses


def _count_payload_columns(store: SqlZenStore) -> Dict[str, int]:
    """Count the payload values held inline and offloaded."""
    counts = {"inline": 0, "offloaded": 0}
    with Session(store.engine) as session:
        for schema in PAYLOAD_SCHEMAS:
            for row in session.exec(select(schema)).all():
                for field in schema.PAYLOAD_FIELDS:
                    if field.get_blob_id(row) is not None:
                        counts["offloaded"] += 1
                    elif field.get_inline_text(row) is not None:
                        counts["inline"] += 1
    return counts


def _move_payloads_inline(store: SqlZenStore) -> None:
    """Move every offloaded payload back into its inline column."""
    for schema in PAYLOAD_SCHEMAS:
        with Session(store.engine) as session:
            rows = session.exec(select(schema)).all()
            values = store.payload_store.load(
                [
                    blob_id
                    for row in rows
                    for field in schema.PAYLOAD_FIELDS
                    if (blob_id := field.get_blob_id(row))
                ]
            )
            for row in rows:
                for field in schema.PAYLOAD_FIELDS:
                    if blob_id := field.get_blob_id(row):
                        setattr(row, field.name, values[blob_id])
                        setattr(row, field.blob_id_name, None)
            session.add_all(rows)
            session.commit()


def _create_snapshot(
    store: SqlZenStore, config_name: Optional[str] = None
) -> PipelineSnapshotResponse:
    """Create a snapshot of two steps, with payloads no other one has."""
    client = Client()
    pipeline_model = store.create_pipeline(
        PipelineRequest(
            project=client.active_project.id, name=f"p-{uuid4().hex[:8]}"
        )
    )
    steps = {
        name: Step(
            spec=StepSpec(
                source=Source(
                    module="payloads.steps", type=SourceType.INTERNAL
                ),
                upstream_steps=upstream,
                invocation_id=name,
            ),
            config=StepConfiguration(name=name),
        )
        for name, upstream in {"load": [], "train": ["load"]}.items()
    }
    return store.create_snapshot(
        PipelineSnapshotRequest(
            project=client.active_project.id,
            stack=client.active_stack.id,
            pipeline=pipeline_model.id,
            run_name_template="payloads",
            pipeline_configuration={"name": config_name or uuid4().hex},
            client_version="test",
            server_version="test",
            step_configurations=steps,
            pipeline_spec=PipelineSpec(steps=[s.spec for s in steps.values()]),
            source_code=f"def pipeline(): ...  # {uuid4().hex}",
        )
    )


def _run_request(
    snapshot_id: UUID, tags: Optional[List[str]] = None
) -> PipelineRunRequest:
    """A request for a new running run of a snapshot."""
    return PipelineRunRequest(
        project=Client().active_project.id,
        name=f"run-{uuid4().hex[:8]}",
        snapshot=snapshot_id,
        status=ExecutionStatus.RUNNING,
        start_time=utc_now(),
        orchestrator_run_id=uuid4().hex,
        orchestrator_environment={"pod": uuid4().hex},
        tags=tags,
    )


def _start_run(store: SqlZenStore) -> PipelineRunResponse:
    """Start a run of a new snapshot."""
    run, _ = store.get_or_create_run(_run_request(_create_snapshot(store).id))
    return run


def _start_step(store: SqlZenStore, run_id: UUID) -> StepRunResponse:
    """Start the first step of a run."""
    return store.create_run_step(
        StepRunRequest(
            project=Client().active_project.id,
            name="load",
            status=ExecutionStatus.RUNNING,
            start_time=utc_now(),
            pipeline_run_id=run_id,
            source_code=f"def load(): ...  # {uuid4().hex}",
            docstring="Load a value.",
        )
    )


def _get_config_blob_content(
    session: Session, snapshot_id: UUID
) -> BlobContentSchema:
    """The stored bytes of the pipeline configuration of a snapshot."""
    snapshot = session.get(PipelineSnapshotSchema, snapshot_id)
    assert snapshot and snapshot.pipeline_configuration_blob_id
    blob = session.get(BlobSchema, snapshot.pipeline_configuration_blob_id)
    assert blob
    content = session.get(BlobContentSchema, blob.sha256)
    assert content
    return content


def test_offloaded_and_inline_payloads_read_the_same(
    store: SqlZenStore,
) -> None:
    """Runs read the same whether their payloads are offloaded or inline."""
    static_pipeline()
    dynamic_pipeline()
    columns = _count_payload_columns(store)
    assert columns["offloaded"] > 0
    assert columns["inline"] == 0

    offloaded = _hydrated_responses(_open_store(store, cache_size=0))
    _move_payloads_inline(store)
    assert _count_payload_columns(store)["offloaded"] == 0
    inline = _hydrated_responses(store)

    assert offloaded == inline


def test_paths_without_metadata_work_while_payloads_are_unreadable(
    store: SqlZenStore,
) -> None:
    """Execution updates and responses without metadata never read payloads."""
    cold = _open_store(store, cache_size=0)
    run = _start_run(cold)
    step_run = _start_step(cold, run.id)
    with Session(cold.engine) as session:
        session.execute(delete(BlobContentSchema))
        session.commit()

    with pytest.raises(RuntimeError, match="missing"):
        cold.get_run(run.id, hydrate=True)

    project = Client().active_project.id
    cold.get_run(run.id, hydrate=False)
    cold.list_runs(PipelineRunFilter(project=project))
    cold.get_snapshot(run.snapshot.id, hydrate=False)
    cold.list_snapshots(PipelineSnapshotFilter(project=project))
    cold.get_run_step(step_run.id, hydrate=False)
    cold.list_run_steps(StepRunFilter(project=project))
    cold.update_step_heartbeat(step_run.id)
    cold.update_run_step(
        step_run.id,
        StepRunUpdate(
            status=ExecutionStatus.FAILED,
            end_time=utc_now(),
            exception_info={"traceback": "Traceback", "step_code_line": None},
        ),
    )
    updated = cold.update_run(
        run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED)
    )
    assert updated.status == ExecutionStatus.FAILED


def test_run_creation_writes_nothing_when_payloads_are_unreadable(
    store: SqlZenStore,
) -> None:
    """A payload read failure while creating a run leaves no half-created run."""
    cold = _open_store(store, cache_size=0)
    snapshot = _create_snapshot(cold)
    request = _run_request(snapshot.id, tags=["payloads"])
    with Session(cold.engine) as session:
        content = _get_config_blob_content(session, snapshot.id)
        sha256, data = content.sha256, content.data
        session.delete(content)
        session.commit()

    with pytest.raises(RuntimeError, match="missing"):
        cold.get_or_create_run(request)

    with Session(cold.engine) as session:
        assert not session.exec(
            select(PipelineRunSchema.id).where(
                PipelineRunSchema.snapshot_id == snapshot.id
            )
        ).all()
        session.add(BlobContentSchema(sha256=sha256, data=data))
        session.commit()

    run, created = cold.get_or_create_run(request)
    assert created
    assert [tag.name for tag in run.tags] == ["payloads"]


def test_corrupted_blob_is_rejected_and_not_cached(store: SqlZenStore) -> None:
    """Bytes that are not the registered ones never reach a response."""
    snapshot = _create_snapshot(store, config_name="original-configuration")
    cached = _open_store(store, cache_size=64 * 1024 * 1024)

    def replace_config_bytes(old: bytes, new: bytes) -> None:
        with Session(store.engine) as session:
            content = _get_config_blob_content(session, snapshot.id)
            content.data = content.data.replace(old, new)
            session.add(content)
            session.commit()

    # Same size, so that only the SHA-256 tells the bytes apart.
    replace_config_bytes(b"original", b"tampered")
    with pytest.raises(PayloadIntegrityError):
        cached.get_snapshot(snapshot.id, hydrate=True)

    replace_config_bytes(b"tampered", b"original")
    restored = cached.get_snapshot(snapshot.id, hydrate=True)
    assert restored.pipeline_configuration.name == "original-configuration"
