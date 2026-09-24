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
tests run real pipelines and store calls against it, and against a second
store on the same database that offloads to a local directory, to cover what
offloading can break: responses that differ from inline ones, paths that read
payloads they do not need, storage outages, half-created runs and corrupted
blobs.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlmodel import Session, select

from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.exceptions import (
    IllegalOperationError,
    PayloadIntegrityError,
    PayloadStorageUnavailableError,
)
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
    BlobSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)

PAYLOAD_SCHEMAS = [
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
    PipelineRunSchema,
]
REVISION_BEFORE_PAYLOAD_STORAGE = "8d638fcb4bd5"


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


def _open_local_store(store: SqlZenStore, root: Path) -> SqlZenStore:
    """Open a store that offloads to a local directory, without a cache."""
    return _open_store(
        store,
        write_backend="local",
        backends={"local": {"path": str(root)}},
        cache_size=0,
    )


@contextmanager
def _payload_reads(store: SqlZenStore) -> Iterator[List[str]]:
    """Record the queries that resolve offloaded payloads.

    Every resolution selects the bytes of database-held blobs along with the
    registry rows, whatever the backend; writes never select them.
    """
    statements: List[str] = []

    def record(conn: Any, cursor: Any, statement: str, *args: Any) -> None:
        if statement.startswith("SELECT") and "blob_content.data" in statement:
            statements.append(statement)

    event.listen(store.engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(store.engine, "before_cursor_execute", record)


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


def _get_blob_path(store: SqlZenStore, root: Path, blob_id: UUID) -> Path:
    """The file of a blob held by the local backend."""
    with Session(store.engine) as session:
        blob = session.get(BlobSchema, blob_id)
        assert blob
        return root / blob.sha256[:2] / blob.sha256[2:4] / blob.sha256


def _get_config_blob_path(
    store: SqlZenStore, root: Path, snapshot_id: UUID
) -> Path:
    """The file of the pipeline configuration of a snapshot."""
    with Session(store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, snapshot_id)
        assert snapshot and snapshot.pipeline_configuration_blob_id
        blob_id = snapshot.pipeline_configuration_blob_id
    return _get_blob_path(store, root, blob_id)


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


def test_sql_only_paths_read_no_payloads(store: SqlZenStore) -> None:
    """Responses without metadata and execution updates read no payloads."""
    cold = _open_store(store, cache_size=0)
    run = _start_run(cold)
    step_run = _start_step(cold, run.id)
    project = Client().active_project.id

    with _payload_reads(cold) as reads:
        cold.get_run(run.id, hydrate=False)
        cold.list_runs(PipelineRunFilter(project=project))
        cold.get_snapshot(run.snapshot.id, hydrate=False)
        cold.list_snapshots(PipelineSnapshotFilter(project=project))
        cold.get_run_step(step_run.id, hydrate=False)
        cold.list_run_steps(StepRunFilter(project=project))
        cold.update_step_heartbeat(step_run.id)
        cold.update_run_step(
            step_run.id, StepRunUpdate(status=ExecutionStatus.COMPLETED)
        )
        cold.update_run(
            run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED)
        )

    assert reads == []


def test_existing_run_is_authorized_before_its_payloads_are_read(
    store: SqlZenStore,
) -> None:
    """A caller who may not read an existing run causes no payload reads."""
    request = _run_request(_create_snapshot(store).id)
    store.get_or_create_run(request)

    def deny(run: PipelineRunResponse) -> None:
        raise IllegalOperationError("Denied.")

    cold = _open_store(store, cache_size=0)
    with _payload_reads(cold) as reads:
        with pytest.raises(IllegalOperationError):
            cold.get_or_create_run(request, pre_read_hook=deny)
    assert reads == []

    run, created = cold.get_or_create_run(request)
    assert not created
    assert run.orchestrator_environment == request.orchestrator_environment


def test_storage_outage_fails_only_what_needs_payloads(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """While storage is down, only creations and hydrated reads fail."""
    root = tmp_path / "payloads"
    root.mkdir()
    local = _open_local_store(store, root)
    run = _start_run(local)
    step_run = _start_step(local, run.id)

    root.rename(tmp_path / "unmounted")
    try:
        with pytest.raises(PayloadStorageUnavailableError):
            _create_snapshot(local)
        with pytest.raises(PayloadStorageUnavailableError):
            local.get_run(run.id, hydrate=True)

        local.get_run(run.id, hydrate=False)
        local.list_runs(PipelineRunFilter(project=Client().active_project.id))
        local.update_step_heartbeat(step_run.id)
        local.update_run_step(
            step_run.id,
            StepRunUpdate(
                status=ExecutionStatus.FAILED,
                end_time=utc_now(),
                exception_info={
                    "traceback": "Traceback: outage",
                    "step_code_line": None,
                },
            ),
        )
        local.update_run(
            run.id, PipelineRunUpdate(status=ExecutionStatus.FAILED)
        )
    finally:
        (tmp_path / "unmounted").rename(root)

    assert local.get_run(run.id, hydrate=True).status == ExecutionStatus.FAILED


def test_run_creation_writes_nothing_when_storage_fails(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """A storage failure while creating a run leaves no half-created run."""
    root = tmp_path / "payloads"
    root.mkdir()
    local = _open_local_store(store, root)
    snapshot = _create_snapshot(local)
    blob_path = _get_config_blob_path(local, root, snapshot.id)
    request = _run_request(snapshot.id, tags=["payloads"])

    blob_path.rename(tmp_path / "missing")
    try:
        with pytest.raises(PayloadStorageUnavailableError):
            local.get_or_create_run(request)
    finally:
        (tmp_path / "missing").rename(blob_path)

    with Session(local.engine) as session:
        assert not session.exec(
            select(PipelineRunSchema.id).where(
                PipelineRunSchema.snapshot_id == snapshot.id
            )
        ).all()

    run, created = local.get_or_create_run(request)
    assert created
    assert [tag.name for tag in run.tags] == ["payloads"]


def test_corrupted_blob_is_rejected_and_not_cached(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """Bytes that are not the registered ones never reach a response."""
    root = tmp_path / "payloads"
    root.mkdir()
    local = _open_local_store(store, root)
    snapshot = _create_snapshot(local, config_name="original-configuration")
    blob_path = _get_config_blob_path(local, root, snapshot.id)
    original = blob_path.read_bytes()
    # Same size, so that only the SHA-256 tells the bytes apart.
    blob_path.write_bytes(original.replace(b"original", b"tampered"))

    cached = _open_store(local, cache_size=64 * 1024 * 1024)
    try:
        with pytest.raises(PayloadIntegrityError):
            cached.get_snapshot(snapshot.id, hydrate=True)
    finally:
        blob_path.write_bytes(original)

    restored = cached.get_snapshot(snapshot.id, hydrate=True)
    assert restored.pipeline_configuration.name == "original-configuration"


@pytest.mark.usefixtures("clean_client")
def test_store_opens_to_migrate_a_database_without_payload_tables(
    tmp_path: Path,
) -> None:
    """A store opened only to migrate works before the payload tables exist."""
    config = SqlZenStoreConfiguration(url=f"sqlite:///{tmp_path / 'zenml.db'}")
    store = SqlZenStore(config=config, skip_default_registrations=True)
    head = store.alembic.current_revisions()
    store.alembic.downgrade(REVISION_BEFORE_PAYLOAD_STORAGE)

    migrating = SqlZenStore(
        config=config, skip_default_registrations=True, skip_migrations=True
    )
    migrating.migrate_database()

    assert migrating.alembic.current_revisions() == head
