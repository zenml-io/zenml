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

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence
from uuid import UUID, uuid4

import pytest
from fsspec import config as fsspec_config
from fsspec.asyn import AsyncFileSystem
from moto.server import ThreadedMotoServer
from sqlmodel import Session, select

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
from zenml.zen_stores.payload_storage import PayloadStorageConfiguration
from zenml.zen_stores.payload_storage.blob_backends import (
    FsspecBlobBackend,
    create_blob_backend,
)
from zenml.zen_stores.payload_storage.config import BlobBackendType
from zenml.zen_stores.payload_storage.payload_store import (
    BLOB_CHUNK_SIZE,
    PayloadStore,
)
from zenml.zen_stores.payload_storage.payloads import PayloadValue
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
    """While storage is down, only creations and reads with metadata fail.

    Updates are committed and answered without their metadata.
    """
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
    updated_step = cold.update_run_step(
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
    assert updated_step.metadata is None
    assert (updated.status, updated.metadata) == (ExecutionStatus.FAILED, None)


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
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Payloads are only written to and read from one location.

    The first payloads that are stored bind the deployment to their location,
    even for a process that started earlier with another location and was
    uploading while they were stored, but a write that failed does not.
    Another path is another location, even in the same bucket, and so is the
    same path on another S3-compatible endpoint; another spelling of the same
    path or other credentials are not.
    """
    backend_config = store.config.payload_storage.backend_config
    moved = {**backend_config, "path": f"s3://{BUCKET}/moved"}
    missing_bucket = _open_store(
        store, backend_config={**backend_config, "path": "s3://missing/blobs"}
    )
    with pytest.raises(NonRetryablePayloadStorageError, match="refused"):
        _create_snapshot(missing_bucket)
    # Started while nothing was offloaded, so it had no reason to refuse.
    started_before = _open_store(
        store, cache_max_bytes=0, backend_config=moved
    )

    runs: List[PipelineRunResponse] = []
    backend = started_before.payload_store._backend
    put_many = backend.put_many

    def put_many_while_the_first_payloads_are_stored(
        data_by_sha256: Dict[str, bytes], timeout: float
    ) -> None:
        if not runs:
            runs.append(_start_run(store))
        put_many(data_by_sha256, timeout=timeout)

    monkeypatch.setattr(
        backend, "put_many", put_many_while_the_first_payloads_are_stored
    )
    with pytest.raises(
        NonRetryablePayloadStorageError, match="payload storage location"
    ):
        _create_snapshot(started_before)
    (run,) = runs
    shared = [PayloadValue(text="stored at the bound location")]
    store.payload_store.offload(shared)
    with pytest.raises(
        NonRetryablePayloadStorageError, match="payload storage location"
    ):
        started_before.payload_store.offload(shared)

    snapshots = store.list_snapshots(
        PipelineSnapshotFilter(project=Client().active_project.id)
    )
    assert [snapshot.id for snapshot in snapshots.items] == [run.snapshot.id]
    with Session(store.engine) as session:
        locations = set(
            session.exec(select(PayloadBlobSchema.location_fingerprint))
        )
    assert len(locations) == 1
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

    response = unconfigured.update_run(
        run.id, PipelineRunUpdate(add_tags=["updated"])
    )
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


class _RecordingFilesystem(AsyncFileSystem):
    """Records the paths of the requests it starts."""

    def __init__(self, started: List[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.started = started

    async def _cat_file(self, path: str, **kwargs: Any) -> bytes:
        self.started.append(path)
        return b""


class _SlowToCreateFilesystem(_RecordingFilesystem):
    """Looks up credentials for a second when created, as gcsfs can."""

    def __init__(self, started: List[str], **kwargs: Any) -> None:
        time.sleep(1)
        super().__init__(started, **kwargs)


class _LoopBlockingFilesystem(_RecordingFilesystem):
    """Blocks the event loop for a second, as gcsfs refreshing a token does."""

    async def _cat_file(self, path: str, **kwargs: Any) -> bytes:
        data = await super()._cat_file(path, **kwargs)
        time.sleep(1)
        return data


@pytest.mark.parametrize(
    ("filesystem_class", "started_requests"),
    [
        (_SlowToCreateFilesystem, []),
        (_LoopBlockingFilesystem, [f"gs://bucket/blobs/{'0' * 64}"]),
    ],
)
def test_backend_call_fails_in_time_while_the_client_hangs(
    filesystem_class: Any, started_requests: List[str]
) -> None:
    """A call raises within its timeout, and starts no request afterwards.

    When the first request blocks the event loop past the timeout, the second
    one, due right after it, must not start once the loop is free.
    """
    started: List[str] = []
    backend = FsspecBlobBackend(
        BlobBackendType.GCS,
        "gs://bucket/blobs",
        location="gs://bucket/blobs",
        filesystem_class=filesystem_class,
        filesystem_options={"started": started},
        max_concurrent_calls=4,
    )
    began = time.monotonic()
    with pytest.raises(TimeoutError):
        backend.get_many(["0" * 64, "1" * 64], timeout=0.2)
    elapsed = time.monotonic() - began

    assert backend.get_many([], timeout=5) == {}
    assert started == started_requests
    assert elapsed < 0.7


class _FailingFilesystem(AsyncFileSystem):
    """Fails every request with the error it is created with."""

    def __init__(self, error: Exception, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.error = error

    async def _cat_file(self, path: str, **kwargs: Any) -> bytes:
        raise self.error


@pytest.mark.parametrize(
    ("status", "message", "raised"),
    [
        (
            401,
            "Request had invalid authentication credentials.",
            "PermissionError",
        ),
        (503, "Backend Error", "HttpError"),
    ],
)
def test_gcs_rejecting_the_credentials_is_denied_access(
    status: int, message: str, raised: str
) -> None:
    """Rejected GCS credentials fail as denied access, an outage does not.

    gcsfs reports the rejection as a `ValueError` when the response calls the
    credentials invalid.
    """
    retry = pytest.importorskip("gcsfs.retry")
    with pytest.raises(Exception) as provider_error:
        retry.validate_response(
            status,
            json.dumps({"error": {"code": status, "message": message}}),
            "bucket/blobs",
        )
    backend = FsspecBlobBackend(
        BlobBackendType.GCS,
        "gs://bucket/blobs",
        location="gs://bucket/blobs",
        filesystem_class=_FailingFilesystem,
        filesystem_options={"error": provider_error.value},
        max_concurrent_calls=4,
    )

    with pytest.raises(Exception) as error:
        backend.get_many(["0" * 64], timeout=5)

    assert type(error.value).__name__ == raised


def _slow_down_reads(
    payload_store: PayloadStore,
    monkeypatch: pytest.MonkeyPatch,
    seconds: float,
) -> threading.Event:
    """Make each backend read take `seconds`, or time out if it has less.

    The returned event is set once a read starts.
    """
    backend = payload_store._backend
    assert backend
    get_many = backend.get_many
    reading = threading.Event()

    def slow_get_many(sha256s: Sequence[str], timeout: float) -> Any:
        reading.set()
        if timeout < seconds:
            time.sleep(max(timeout, 0))
            raise TimeoutError
        time.sleep(seconds)
        return get_many(sha256s, timeout=timeout - seconds)

    monkeypatch.setattr(backend, "get_many", slow_get_many)
    return reading


def test_load_shares_one_timeout_across_chunks(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A load of many chunks fails once their total time passes the timeout."""
    offloaded = _open_store(store).payload_store.offload(
        PayloadValue(text=f"value {index}")
        for index in range(2 * BLOB_CHUNK_SIZE + 1)
    )
    payload_store = _open_store(
        store, cache_max_bytes=0, backend_timeout_seconds=1
    ).payload_store
    _slow_down_reads(payload_store, monkeypatch, seconds=0.4)

    started = time.monotonic()
    with pytest.raises(PayloadStorageUnavailableError):
        payload_store.load(offloaded.values_by_blob_id)
    assert time.monotonic() - started < 1.3


def test_load_after_waiting_for_a_failed_load_keeps_its_timeout(
    store: SqlZenStore,
    s3_server: ThreadedMotoServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A load that waits for another one keeps its own timeout.

    The other load fails for good on a blob that only it needs, so the
    waiting load loads its blob again, in the time it has left.
    """
    offloaded = _open_store(store).payload_store.offload(
        [PayloadValue(text="healthy"), PayloadValue(text="missing")]
    )
    blob_ids = {
        text: blob_id for blob_id, text in offloaded.values_by_blob_id.items()
    }
    healthy, missing = blob_ids["healthy"], blob_ids["missing"]
    local_s3_client(s3_server).delete_object(
        Bucket=BUCKET, Key=f"{PREFIX}/{PayloadValue(text='missing').sha256}"
    )
    payload_store = _open_store(
        store, cache_max_bytes=0, backend_timeout_seconds=1
    ).payload_store
    # Loaded before reads slow down, so that creating the storage client does
    # not take from the 0.2 s that the owner's slow read leaves for reading.
    assert payload_store.load([healthy]) == {healthy: "healthy"}
    reading = _slow_down_reads(payload_store, monkeypatch, seconds=0.8)

    with ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(payload_store.load, [healthy, missing])
        assert reading.wait(timeout=5)
        waiter = executor.submit(payload_store.load, [healthy])
        with pytest.raises(PayloadStorageUnavailableError):
            waiter.result(timeout=1.3)
        with pytest.raises(NonRetryablePayloadStorageError):
            owner.result()


@pytest.fixture
def aws_config_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An empty AWS config file that botocore reads instead of the user's.

    Args:
        monkeypatch: Isolates the AWS environment variables.
        tmp_path: Holds the config and credentials files.

    Returns:
        The path of the config file, for the test to write.
    """
    for variable in list(os.environ):
        if variable.startswith("AWS_"):
            monkeypatch.delenv(variable)
    config_file = tmp_path / "aws-config"
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config_file))
    monkeypatch.setenv(
        "AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "aws-credentials")
    )
    return config_file


AWS_CONFIG = """
[default]
endpoint_url = http://127.0.0.1:14004

[profile services]
services = local

[profile regional]
region = eu-west-1

[services local]
s3 =
  endpoint_url = http://127.0.0.1:14005
"""
S3_PATH = {"path": "s3://payloads/blobs"}
AZURE_PATH = {"path": "az://payloads/blobs"}
GCS_PATH = {"path": "gs://payloads/blobs"}
AZURE_DEFAULT_LOCATION = (
    "az://payloads/blobs at https://sameaccount.blob.core.windows.net"
)


@pytest.mark.parametrize(
    "backend_type, options, environment, expected_location",
    [
        pytest.param(
            BlobBackendType.S3,
            {**S3_PATH, "endpoint_url": "http://127.0.0.1:14001/"},
            {"AWS_ENDPOINT_URL_S3": "http://127.0.0.1:14003"},
            "s3://payloads/blobs at http://127.0.0.1:14001",
            id="s3-option-over-environment",
        ),
        pytest.param(
            BlobBackendType.S3,
            S3_PATH,
            {"AWS_ENDPOINT_URL": "http://127.0.0.1:14002"},
            "s3://payloads/blobs at http://127.0.0.1:14002",
            id="s3-environment-over-config-file",
        ),
        pytest.param(
            BlobBackendType.S3,
            {**S3_PATH, "key": "rotated", "secret": "rotated"},
            {"AWS_ENDPOINT_URL": "http://127.0.0.1:14002"},
            "s3://payloads/blobs at http://127.0.0.1:14002",
            id="s3-other-credentials",
        ),
        pytest.param(
            BlobBackendType.S3,
            S3_PATH,
            {
                "AWS_ENDPOINT_URL": "http://127.0.0.1:14002",
                "AWS_ENDPOINT_URL_S3": "http://127.0.0.1:14003",
            },
            "s3://payloads/blobs at http://127.0.0.1:14003",
            id="s3-service-environment",
        ),
        pytest.param(
            BlobBackendType.S3,
            S3_PATH,
            {},
            "s3://payloads/blobs at http://127.0.0.1:14004",
            id="s3-config-file",
        ),
        pytest.param(
            BlobBackendType.S3,
            {**S3_PATH, "profile": "services"},
            {},
            "s3://payloads/blobs at http://127.0.0.1:14005",
            id="s3-profile-services-section",
        ),
        pytest.param(
            BlobBackendType.S3,
            S3_PATH,
            {"AWS_PROFILE": "services"},
            "s3://payloads/blobs at http://127.0.0.1:14005",
            id="s3-profile-from-environment",
        ),
        pytest.param(
            BlobBackendType.S3,
            {**S3_PATH, "profile": "regional"},
            {},
            "s3://payloads/blobs",
            id="s3-aws-region",
        ),
        pytest.param(
            BlobBackendType.S3,
            S3_PATH,
            {
                "AWS_ENDPOINT_URL": "http://127.0.0.1:14002",
                "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS": "true",
            },
            "s3://payloads/blobs",
            id="s3-ignored-environment-and-config-file",
        ),
        pytest.param(
            BlobBackendType.S3,
            {
                **S3_PATH,
                "config_kwargs": {"ignore_configured_endpoint_urls": True},
            },
            {},
            "s3://payloads/blobs",
            id="s3-ignored-by-client-config",
        ),
        pytest.param(
            BlobBackendType.S3,
            S3_PATH,
            {"FSSPEC_S3_ENDPOINT_URL": "http://127.0.0.1:14006"},
            "s3://payloads/blobs at http://127.0.0.1:14006",
            id="s3-fsspec-config",
        ),
        pytest.param(
            BlobBackendType.AZURE,
            {
                **AZURE_PATH,
                "account_name": "sameaccount",
                "account_key": "a2V5",
            },
            {},
            AZURE_DEFAULT_LOCATION,
            id="azure-account",
        ),
        pytest.param(
            BlobBackendType.AZURE,
            {
                **AZURE_PATH,
                "account_name": "sameaccount",
                "sas_token": "sv=2024&sig=secret",
            },
            {},
            AZURE_DEFAULT_LOCATION,
            id="azure-sas-token",
        ),
        pytest.param(
            BlobBackendType.AZURE,
            AZURE_PATH,
            {
                "AZURE_STORAGE_CONNECTION_STRING": (
                    "BlobEndpoint=https://sameaccount.blob.core.windows.net/;"
                    "SharedAccessSignature=sv=2024&sig=secret"
                )
            },
            AZURE_DEFAULT_LOCATION,
            id="azure-sas-connection-string",
        ),
        pytest.param(
            BlobBackendType.AZURE,
            {
                **AZURE_PATH,
                "account_name": "sameaccount",
                "account_key": "a2V5",
                "account_host": "sameaccount.blob.core.usgovcloudapi.net",
            },
            {},
            "az://payloads/blobs at "
            "https://sameaccount.blob.core.usgovcloudapi.net",
            id="azure-account-host",
        ),
        pytest.param(
            BlobBackendType.AZURE,
            {
                **AZURE_PATH,
                "connection_string": (
                    "AccountName=sameaccount;AccountKey=a2V5;"
                    "BlobEndpoint=http://127.0.0.1:14001/sameaccount;"
                ),
            },
            {},
            "az://payloads/blobs at http://127.0.0.1:14001/sameaccount",
            id="azure-blob-endpoint",
        ),
        pytest.param(
            BlobBackendType.AZURE,
            {
                **AZURE_PATH,
                "connection_string": (
                    "DefaultEndpointsProtocol=https;AccountName=sameaccount;"
                    "AccountKey=a2V5;EndpointSuffix=core.chinacloudapi.cn"
                ),
            },
            {},
            "az://payloads/blobs at https://sameaccount.blob.core.chinacloudapi.cn",
            id="azure-endpoint-suffix",
        ),
        pytest.param(
            BlobBackendType.GCS,
            {**GCS_PATH, "endpoint_url": "http://a:9023"},
            {},
            "gs://payloads/blobs at http://a:9023",
            id="gcs-option",
        ),
        pytest.param(
            BlobBackendType.GCS,
            GCS_PATH,
            {"STORAGE_EMULATOR_HOST": "http://b:9023"},
            "gs://payloads/blobs at http://b:9023",
            id="gcs-environment",
        ),
        pytest.param(
            BlobBackendType.GCS,
            GCS_PATH,
            {"FSSPEC_GCS_ENDPOINT_URL": "http://c:9023"},
            "gs://payloads/blobs at http://c:9023",
            id="gcs-fsspec-config",
        ),
    ],
)
def test_location_is_the_endpoint_the_client_uses(
    monkeypatch: pytest.MonkeyPatch,
    aws_config_file: Path,
    backend_type: BlobBackendType,
    options: Dict[str, Any],
    environment: Dict[str, str],
    expected_location: str,
) -> None:
    """The same path behind another endpoint is another location.

    The endpoint counts wherever the client takes it from, as the provider
    resolves it, while other credentials or the default endpoint of an AWS
    region do not.
    """
    pytest.importorskip(
        {
            BlobBackendType.S3: "s3fs",
            BlobBackendType.GCS: "gcsfs",
            BlobBackendType.AZURE: "adlfs",
        }[backend_type]
    )
    for variable in list(os.environ):
        if variable.startswith(("AZURE_STORAGE_", "FSSPEC_")) or (
            variable == "STORAGE_EMULATOR_HOST"
        ):
            monkeypatch.delenv(variable)
    aws_config_file.write_text(AWS_CONFIG)
    for variable, value in environment.items():
        monkeypatch.setenv(variable, value)
    # fsspec reads its configuration from the environment once, on import.
    monkeypatch.setattr(fsspec_config, "conf", {})
    fsspec_config.set_conf_env(fsspec_config.conf)

    backend = create_blob_backend(
        backend_type, options, max_concurrent_calls=4
    )

    assert backend.location == expected_location


def test_payloads_stay_at_the_endpoint_the_store_started_with(
    store: SqlZenStore, aws_config_file: Path
) -> None:
    """A store sends payloads to the endpoint in its location.

    The endpoint comes from the AWS config file, which names an endpoint
    without storage before the store first writes payloads. The store whose
    endpoint is in its options then reads them where they were written.
    """
    backend_config = store.config.payload_storage.backend_config
    client_kwargs = dict(backend_config["client_kwargs"])
    aws_config_file.write_text(
        f"[default]\nendpoint_url = {client_kwargs.pop('endpoint_url')}\n"
    )
    configured = _open_store(
        store,
        cache_max_bytes=0,
        backend_config={**backend_config, "client_kwargs": client_kwargs},
    )
    aws_config_file.write_text(
        "[default]\nendpoint_url = http://127.0.0.1:1\n"
    )

    snapshot = _create_snapshot(configured, config_name="before-the-change")

    for reader in (configured, store):
        read = reader.get_snapshot(snapshot.id, hydrate=True)
        assert read.pipeline_configuration.name == "before-the-change"
