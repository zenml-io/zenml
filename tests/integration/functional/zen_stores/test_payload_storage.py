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

Each test starts a local S3 server, and the clean client's SQLite store
offloads every payload to it. The tests run real pipelines and store calls,
and stop the server or remove or alter stored blobs to cover what offloading
can break: responses that differ from inline ones, execution paths that stop
working while storage is down, half-created runs and corrupted blobs.
"""

from typing import Any, Dict, Generator, List, Optional, Tuple
from uuid import UUID, uuid4

import pytest
from moto.server import ThreadedMotoServer
from sqlmodel import Session, delete, select, update

from tests.harness.utils import (
    local_s3_client,
    local_s3_payload_storage_env_value,
    start_local_s3,
)
from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.constants import ENV_ZENML_STORE_PREFIX
from zenml.enums import ExecutionStatus
from zenml.exceptions import (
    IllegalOperationError,
    NonRetryablePayloadStorageError,
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
from zenml.zen_server.pipeline_execution import utils as execution_utils
from zenml.zen_server.pipeline_execution.snapshot_run_dispatcher import (
    SnapshotRunExecutionRequest,
)
from zenml.zen_server.utils import get_with_best_effort_metadata
from zenml.zen_stores.payload_storage import PayloadStorageConfiguration
from zenml.zen_stores.schemas import (
    PayloadBlobSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore

BUCKET = "payloads"
PREFIX = "blobs"
PAYLOAD_SCHEMAS = [
    PipelineSnapshotSchema,
    StepConfigurationSchema,
    StepRunSchema,
    PipelineRunSchema,
]
CONTROL_COLUMNS = {
    StepRunSchema: ["step_type", "substitutions"],
    StepConfigurationSchema: ["upstream_steps"],
    PipelineSnapshotSchema: ["execution_mode", "enable_heartbeat"],
}


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
def s3_server() -> Generator[ThreadedMotoServer, None, None]:
    """A local S3 server with an empty bucket for the payloads."""
    server = start_local_s3(BUCKET)
    yield server
    server.stop()


@pytest.fixture
def store(
    s3_server: ThreadedMotoServer,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> SqlZenStore:
    """The store of a clean client, offloading payloads to the S3 server."""
    monkeypatch.setenv(
        f"{ENV_ZENML_STORE_PREFIX}PAYLOAD_STORAGE",
        local_s3_payload_storage_env_value(
            s3_server, f"s3://{BUCKET}/{PREFIX}"
        ),
    )
    # Created only now, so that its store reads the settings above.
    client = request.getfixturevalue("clean_client")
    zen_store = client.zen_store
    assert isinstance(zen_store, SqlZenStore)
    assert zen_store.config.payload_storage.offload_enabled
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
                for field in schema.PAYLOAD_COLUMNS:
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
                    for field in schema.PAYLOAD_COLUMNS
                    if (blob_id := field.get_blob_id(row))
                ]
            )
            for row in rows:
                for field in schema.PAYLOAD_COLUMNS:
                    if blob_id := field.get_blob_id(row):
                        setattr(row, field.name, values[blob_id])
                        setattr(row, field.blob_id_column_name, None)
            session.add_all(rows)
            session.commit()


def _read_control_columns(store: SqlZenStore) -> Dict[Tuple[UUID, str], Any]:
    """Read the control columns of every row."""
    with Session(store.engine) as session:
        return {
            (row.id, name): getattr(row, name)
            for schema, names in CONTROL_COLUMNS.items()
            for row in session.exec(select(schema)).all()
            for name in names
        }


def _make_rows_predate_payload_storage(store: SqlZenStore) -> None:
    """Hold rows as releases before payload storage and control columns did."""
    _move_payloads_inline(store)
    with Session(store.engine) as session:
        session.execute(delete(PayloadBlobSchema))
        for schema, names in CONTROL_COLUMNS.items():
            session.execute(
                update(schema).values({name: None for name in names})
            )
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
    snapshot_id: UUID,
    tags: Optional[List[str]] = None,
    project_id: Optional[UUID] = None,
) -> PipelineRunRequest:
    """A request for a new running run of a snapshot."""
    return PipelineRunRequest(
        project=project_id or Client().active_project.id,
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


def _get_config_blob_key(store: SqlZenStore, snapshot_id: UUID) -> str:
    """The S3 key of the pipeline configuration of a snapshot."""
    with Session(store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, snapshot_id)
        assert snapshot and snapshot.pipeline_configuration_blob_id
        blob = session.get(
            PayloadBlobSchema, snapshot.pipeline_configuration_blob_id
        )
        assert blob
        return f"{PREFIX}/{blob.sha256}"


def test_offloaded_and_inline_payloads_read_the_same(
    store: SqlZenStore,
) -> None:
    """Runs read the same whether their payloads are offloaded or inline."""
    static_pipeline()
    dynamic_pipeline()
    columns = _count_payload_columns(store)
    assert columns["offloaded"] > 0
    assert columns["inline"] == 0

    offloaded = _hydrated_responses(_open_store(store, cache_max_bytes=0))
    _move_payloads_inline(store)
    assert _count_payload_columns(store)["offloaded"] == 0
    inline = _hydrated_responses(store)

    assert offloaded == inline


def test_storage_outage_fails_only_what_needs_payloads(
    store: SqlZenStore, s3_server: ThreadedMotoServer
) -> None:
    """While storage is down, only creations and reads with metadata fail."""
    cold = _open_store(store, cache_max_bytes=0, backend_timeout_seconds=5)
    run = _start_run(cold)
    step_run = _start_step(cold, run.id)
    s3_server.stop()

    with pytest.raises(PayloadStorageUnavailableError):
        _create_snapshot(cold)
    with pytest.raises(PayloadStorageUnavailableError):
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


def test_run_creation_writes_nothing_when_storage_fails(
    store: SqlZenStore, s3_server: ThreadedMotoServer
) -> None:
    """A missing blob while creating a run leaves no half-created run."""
    cold = _open_store(store, cache_max_bytes=0)
    snapshot = _create_snapshot(cold)
    request = _run_request(snapshot.id, tags=["payloads"])
    s3 = local_s3_client(s3_server)
    key = _get_config_blob_key(cold, snapshot.id)
    data = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    s3.delete_object(Bucket=BUCKET, Key=key)

    with pytest.raises(NonRetryablePayloadStorageError):
        cold.get_or_create_run(request)

    with Session(cold.engine) as session:
        assert not session.exec(
            select(PipelineRunSchema.id).where(
                PipelineRunSchema.snapshot_id == snapshot.id
            )
        ).all()

    s3.put_object(Bucket=BUCKET, Key=key, Body=data)
    run, created = cold.get_or_create_run(request)
    assert created
    assert [tag.name for tag in run.tags] == ["payloads"]


def test_update_with_metadata_writes_nothing_when_storage_fails(
    store: SqlZenStore, s3_server: ThreadedMotoServer
) -> None:
    """A storage failure while updating a run with metadata changes nothing."""
    cold = _open_store(store, cache_max_bytes=0)
    run = _start_run(cold)
    s3 = local_s3_client(s3_server)
    s3.delete_object(
        Bucket=BUCKET, Key=_get_config_blob_key(cold, run.snapshot.id)
    )

    with pytest.raises(NonRetryablePayloadStorageError):
        cold.update_run(
            run.id, PipelineRunUpdate(add_tags=["updated"]), hydrate=True
        )

    assert cold.get_run(run.id, hydrate=False).tags == []


def test_corrupted_blob_is_rejected_and_not_cached(
    store: SqlZenStore, s3_server: ThreadedMotoServer
) -> None:
    """Bytes that are not the registered ones never reach a response."""
    snapshot = _create_snapshot(store, config_name="original-configuration")
    cached = _open_store(store, cache_max_bytes=64 * 1024 * 1024)
    s3 = local_s3_client(s3_server)
    key = _get_config_blob_key(store, snapshot.id)
    original = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()

    # Same size, so that only the SHA-256 tells the bytes apart.
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=original.replace(b"original", b"tampered"),
    )
    with pytest.raises(PayloadIntegrityError):
        cached.get_snapshot(snapshot.id, hydrate=True)

    s3.put_object(Bucket=BUCKET, Key=key, Body=original)
    restored = cached.get_snapshot(snapshot.id, hydrate=True)
    assert restored.pipeline_configuration.name == "original-configuration"


def test_storage_location_cannot_move_once_it_holds_payloads(
    store: SqlZenStore,
) -> None:
    """Blobs are only read from where they were written.

    Another path is another location, even in the same bucket, and so is the
    same path on another S3-compatible endpoint; another spelling of the same
    path or other credentials are not.
    """
    backend_config = store.config.payload_storage.backend_config
    moved = {**backend_config, "path": f"s3://{BUCKET}/moved"}
    # Started while nothing was offloaded, so it had no reason to refuse.
    started_before = _open_store(
        store, cache_max_bytes=0, backend_config=moved
    )
    run = _start_run(store)

    with pytest.raises(
        NonRetryablePayloadStorageError, match="payload storage location"
    ):
        started_before.get_run(run.id, hydrate=True)
    with pytest.raises(RuntimeError, match="cannot move once it holds"):
        _open_store(store, backend_config=moved)
    other_endpoint = {
        **backend_config,
        "client_kwargs": {
            **backend_config["client_kwargs"],
            "endpoint_url": "http://127.0.0.1:1",
        },
    }
    with pytest.raises(RuntimeError, match="cannot move once it holds"):
        _open_store(store, backend_config=other_endpoint)

    same_location = _open_store(
        store,
        cache_max_bytes=0,
        backend_config={
            **backend_config,
            "path": f"s3://{BUCKET}/{PREFIX}/",
            "key": "rotated",
            "secret": "rotated",
        },
    )
    assert same_location.get_run(run.id, hydrate=True).config == run.config


def test_process_without_backend_answers_committed_updates(
    store: SqlZenStore,
) -> None:
    """A process without a backend fails payload reads as a storage error.

    It was started before anything was offloaded. A committed update is then
    answered without the payloads instead of failing, which would make
    clients retry an update that already happened.
    """
    unconfigured = _open_store(
        store, offload_enabled=False, backend=None, backend_config={}
    )
    run = _start_run(store)

    with pytest.raises(
        NonRetryablePayloadStorageError, match="no payload storage backend"
    ):
        unconfigured.get_run(run.id, hydrate=True)

    unconfigured.update_run(run.id, PipelineRunUpdate(add_tags=["updated"]))
    response = get_with_best_effort_metadata(unconfigured.get_run, run.id)
    assert [tag.name for tag in response.tags] == ["updated"]
    assert response.metadata is None


@pytest.mark.parametrize(
    "schema_class",
    [PipelineRunSchema, PipelineSnapshotSchema],
    ids=["run", "snapshot"],
)
def test_shared_entity_is_read_without_its_payloads(
    store: SqlZenStore, s3_server: ThreadedMotoServer, schema_class: Any
) -> None:
    """Sharing an entity reads it without the payloads of its metadata.

    Storage is down, so the entity must be read without any payload.
    """
    cold = _open_store(store, cache_max_bytes=0, backend_timeout_seconds=5)
    run = _start_run(cold)
    entity_id = (
        run.id if schema_class is PipelineRunSchema else run.snapshot.id
    )
    s3_server.stop()

    entity = cold.get_entity_by_id(entity_id, schema_class)

    assert entity is not None and entity.id == entity_id


def test_prepared_run_that_cannot_start_is_failed(
    store: SqlZenStore,
    s3_server: ThreadedMotoServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A storage failure while the server starts a prepared run fails the run.

    Otherwise the run stays initializing forever, and a synchronous start
    returns a retryable error, on which clients start another run.
    """
    cold = _open_store(store, cache_max_bytes=0, backend_timeout_seconds=5)
    snapshot = _create_snapshot(cold)
    run, _ = cold.get_or_create_run(
        _run_request(snapshot.id).model_copy(
            update={"status": ExecutionStatus.INITIALIZING}
        )
    )
    monkeypatch.setattr(execution_utils, "zen_store", lambda: cold)
    s3_server.stop()

    with pytest.raises(RuntimeError, match="Failed to start pipeline run"):
        execution_utils.execute_snapshot_run(
            SnapshotRunExecutionRequest(run_id=run.id, snapshot_id=snapshot.id)
        )

    assert cold.get_run_status(run.id) == ExecutionStatus.FAILED


def test_backfill_offloads_existing_rows_as_new_writes_would(
    store: SqlZenStore,
) -> None:
    """The backfill offloads inline payloads and fills the control columns.

    Reads return the same before and after, and the control columns get the
    values that writers set. Small batches cover the scan across batches.
    """
    static_pipeline()
    dynamic_pipeline()
    control_values = _read_control_columns(store)
    _make_rows_predate_payload_storage(store)
    inline_responses = _hydrated_responses(store)
    inline_store = _open_store(store, offload_enabled=False)
    with pytest.raises(IllegalOperationError, match="offloading enabled"):
        inline_store.backfill_payloads()

    results = store.backfill_payloads(batch_size=3, pause_seconds=0)

    assert not any(result.failed_rows for result in results)
    assert store.get_payload_backfill_completion()
    assert _count_payload_columns(store)["inline"] == 0
    assert _read_control_columns(store) == control_values
    cold = _open_store(store, cache_max_bytes=0)
    assert _hydrated_responses(cold) == inline_responses
    reports = store.get_payload_backfill_report()
    assert [report.pending_rows for report in reports] == [0] * 4
    rerun = store.backfill_payloads(pause_seconds=0)
    assert sum(result.rows_updated for result in rerun) == 0


def test_backfill_keeps_a_value_rewritten_while_it_runs(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A value rewritten during the backfill is not replaced by the old one.

    A server with offloading disabled rewrites the orchestrator environment
    inline when it replaces a placeholder run. The new value only differs in
    case, which MySQL collations ignore when comparing text.
    """
    run = _start_run(store)
    _make_rows_predate_payload_storage(store)
    with Session(store.engine) as session:
        schema = session.get(PipelineRunSchema, run.id)
        assert schema and schema.orchestrator_environment
        original = schema.orchestrator_environment
    rewritten = original.upper()
    offload = store.payload_store.offload

    def offload_while_rewritten(values: Any) -> Any:
        values = list(values)
        if any(value.text == original for value in values):
            with Session(store.engine) as session:
                session.execute(
                    update(PipelineRunSchema)
                    .where(PipelineRunSchema.id == run.id)
                    .values(orchestrator_environment=rewritten)
                )
                session.commit()
        return offload(values)

    monkeypatch.setattr(
        store.payload_store, "offload", offload_while_rewritten
    )
    results = store.backfill_payloads(pause_seconds=0)

    assert results[-1].rows_skipped == 1
    assert store.get_payload_backfill_completion() is None
    with Session(store.engine) as session:
        schema = session.get(PipelineRunSchema, run.id)
        assert schema and schema.orchestrator_environment == rewritten
    monkeypatch.undo()
    store.backfill_payloads(pause_seconds=0)
    cold = _open_store(store, cache_max_bytes=0)
    assert cold.get_run(run.id).orchestrator_environment == {
        key.upper(): value.upper()
        for key, value in run.orchestrator_environment.items()
    }


def test_backfill_stops_before_the_payloads_a_failed_row_reads(
    store: SqlZenStore,
) -> None:
    """A step run whose configuration cannot be read stops the backfill.

    Its step configuration and snapshot stay inline, which is where reads of
    the step run look for them, until the step run is fixed or deleted.
    """
    run = _start_run(store)
    step_run = _start_step(store, run.id)
    _make_rows_predate_payload_storage(store)
    with Session(store.engine) as session:
        session.execute(
            update(StepRunSchema)
            .where(StepRunSchema.id == step_run.id)
            .values(name="renamed")
        )
        session.commit()
    results = store.backfill_payloads(pause_seconds=0)

    assert [result.table for result in results] == ["step_run"]
    assert list(results[0].failed_rows) == [step_run.id]
    assert store.get_payload_backfill_completion() is None
    assert _count_payload_columns(store)["offloaded"] == 0

    store.delete_run(run.id)
    rerun = store.backfill_payloads(pause_seconds=0)
    assert not any(result.failed_rows for result in rerun)
    assert _count_payload_columns(store)["inline"] == 0


def test_backfill_writes_nothing_while_storage_is_down(
    store: SqlZenStore, s3_server: ThreadedMotoServer
) -> None:
    """A storage failure stops the backfill without changing or failing rows."""
    _start_run(store)
    _make_rows_predate_payload_storage(store)
    cold = _open_store(store, backend_timeout_seconds=5)
    pending = cold.get_payload_backfill_report()
    s3_server.stop()

    with pytest.raises(PayloadStorageUnavailableError):
        cold.backfill_payloads(pause_seconds=0)

    assert cold.get_payload_backfill_report() == pending
