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
"""End-to-end checks of execution payloads stored in their own table.

The clean client's database is created by this release, so new rows
reference their payloads. The tests run real pipelines and store calls, and
compare what referencing payloads could break: responses that differ from
inline ones, rows written while the gate is off, and reads that should not
load payloads at all.
"""

import os
from typing import Any, Dict, Iterator, List, Tuple
from uuid import uuid4

import pytest
from sqlalchemy import event, update
from sqlmodel import Session, col, select

from zenml import pipeline, step
from zenml.client import Client
from zenml.constants import (
    ENV_ZENML_STORE_PREFIX,
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineBuildRequest,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
    RunTemplateFilter,
    RunTemplateRequest,
    StepRunFilter,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    ExecutionPayloadSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    RunTemplateSchema,
    ServerSettingsSchema,
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
    """Double a value (× 2)."""
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
def store(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> SqlZenStore:
    """The store of a clean client.

    With `ZENML_TEST_PAYLOAD_MYSQL_URL` set to a MySQL or MariaDB server
    (`mysql://user:password@host:port`), each test gets a new database there
    instead of the clean client's SQLite one.
    """
    mysql_url = os.environ.get("ZENML_TEST_PAYLOAD_MYSQL_URL")
    if mysql_url:
        monkeypatch.setenv(
            f"{ENV_ZENML_STORE_PREFIX}URL",
            f"{mysql_url.rstrip('/')}/payloads_{uuid4().hex[:12]}",
        )
    # Created only now, so that its store reads the settings above.
    client = request.getfixturevalue("clean_client")
    zen_store = client.zen_store
    assert isinstance(zen_store, SqlZenStore)
    # The clean client falls back to SQLite silently.
    assert (zen_store.engine.dialect.name == "mysql") == bool(mysql_url)
    return zen_store


def _hydrated_responses(store: SqlZenStore) -> Dict[str, Any]:
    """Every hydrated run, step, snapshot and run DAG of the project."""
    project = Client().active_project.id
    responses: Dict[str, Any] = {}
    for run in store.list_runs(
        PipelineRunFilter(project=project, size=1000), hydrate=True
    ).items:
        responses[f"listed-run:{run.id}"] = run.model_dump(mode="json")
        responses[f"run:{run.id}"] = store.get_run(run.id).model_dump(
            mode="json"
        )
        responses[f"dag:{run.id}"] = store.get_pipeline_run_dag(
            run.id
        ).model_dump(mode="json")
    for step_run in store.list_run_steps(
        StepRunFilter(project=project, size=1000), hydrate=True
    ).items:
        responses[f"listed-step:{step_run.id}"] = step_run.model_dump(
            mode="json"
        )
        responses[f"step:{step_run.id}"] = store.get_run_step(
            step_run.id
        ).model_dump(mode="json")
    for snapshot in store.list_snapshots(
        PipelineSnapshotFilter(project=project, size=1000), hydrate=True
    ).items:
        responses[f"listed-snapshot:{snapshot.id}"] = snapshot.model_dump(
            mode="json"
        )
        responses[f"snapshot:{snapshot.id}"] = store.get_snapshot(
            snapshot.id
        ).model_dump(mode="json")
    for template in store.list_run_templates(
        RunTemplateFilter(project=project, size=1000), hydrate=True
    ).items:
        responses[f"listed-template:{template.id}"] = template.model_dump(
            mode="json"
        )
        responses[f"template:{template.id}"] = store.get_run_template(
            template.id
        ).model_dump(mode="json")
    return responses


def _create_run_template(store: SqlZenStore) -> None:
    """Create a run template of the snapshot of a run.

    Creating templates needs a snapshot with a build and a stack without
    local components, which local runs do not have. The template row is
    written directly, since only its reads are under test.
    """
    client = Client()
    project = client.active_project.id
    snapshot_id = (
        store.list_runs(PipelineRunFilter(project=project))
        .items[0]
        .snapshot.id
    )
    build = store.create_build(
        PipelineBuildRequest(
            project=project,
            stack=client.active_stack.id,
            images={},
            is_local=False,
            contains_code=True,
        )
    )
    with Session(store.engine) as session:
        session.execute(
            update(PipelineSnapshotSchema)
            .where(col(PipelineSnapshotSchema.id) == snapshot_id)
            .values(build_id=build.id)
        )
        session.add(
            RunTemplateSchema.from_request(
                RunTemplateRequest(
                    name=f"template-{uuid4().hex[:8]}",
                    source_snapshot_id=snapshot_id,
                    project=project,
                )
            )
        )
        session.commit()


def _count_payload_columns(store: SqlZenStore) -> Dict[str, int]:
    """Count the payload values held inline and referenced."""
    counts = {"inline": 0, "referenced": 0}
    with Session(store.engine) as session:
        for schema in PAYLOAD_SCHEMAS:
            for row in session.exec(select(schema)).all():
                for column in schema.PAYLOAD_COLUMNS:
                    if getattr(row, column.payload_id_column_name):
                        counts["referenced"] += 1
                    elif column.get_inline_value(row) is not None:
                        counts["inline"] += 1
    return counts


def _move_payloads_inline(store: SqlZenStore, every_other: bool) -> None:
    """Move referenced payloads back into their inline columns.

    Args:
        store: The store.
        every_other: Whether to move only every other row of each table, for
            tables that mix both forms.
    """
    with Session(store.engine) as session:
        values = dict(
            session.exec(
                select(
                    ExecutionPayloadSchema.sha256, ExecutionPayloadSchema.value
                )
            ).all()
        )
        for schema in PAYLOAD_SCHEMAS:
            rows = session.exec(select(schema).order_by(schema.id)).all()
            for row in rows[:: 2 if every_other else 1]:
                for column in schema.PAYLOAD_COLUMNS:
                    if payload_id := getattr(
                        row, column.payload_id_column_name
                    ):
                        setattr(row, column.name, values[payload_id])
                        setattr(row, column.payload_id_column_name, None)
            session.add_all(rows)
        session.commit()


def _set_payload_references(store: SqlZenStore, enabled: bool) -> None:
    """Turn payload references on or off for new rows."""
    with Session(store.engine) as session:
        session.execute(
            update(ServerSettingsSchema).values(
                payload_references_enabled=enabled
            )
        )
        session.commit()


def _run_request(snapshot_id: Any, **kwargs: Any) -> PipelineRunRequest:
    """A request for a run of a snapshot."""
    return PipelineRunRequest(
        project=Client().active_project.id,
        snapshot=snapshot_id,
        **{
            "name": f"run-{uuid4().hex[:8]}",
            "status": ExecutionStatus.RUNNING,
            "start_time": utc_now(),
            "orchestrator_run_id": uuid4().hex,
            "orchestrator_environment": {"pod": uuid4().hex},
            **kwargs,
        },
    )


def test_referenced_and_inline_payloads_read_the_same(
    store: SqlZenStore,
) -> None:
    """Responses are the same whether payloads are referenced or inline.

    Also with tables that mix both forms, and identical values share one
    payload row.
    """
    static_pipeline()
    static_pipeline()
    dynamic_pipeline()
    _create_run_template(store)
    columns = _count_payload_columns(store)
    assert columns["referenced"] > 0
    assert columns["inline"] == 0
    with Session(store.engine) as session:
        payload_rows = len(session.exec(select(ExecutionPayloadSchema)).all())
    assert payload_rows < columns["referenced"]

    referenced = _hydrated_responses(store)
    assert any(key.startswith("template:") for key in referenced)
    _move_payloads_inline(store, every_other=True)
    mixed_columns = _count_payload_columns(store)
    assert mixed_columns["inline"] > 0
    assert mixed_columns["referenced"] > 0
    mixed = _hydrated_responses(store)
    _move_payloads_inline(store, every_other=False)
    assert _count_payload_columns(store)["referenced"] == 0
    inline = _hydrated_responses(store)

    assert referenced == mixed == inline


def test_writes_keep_payloads_inline_while_references_are_off(
    store: SqlZenStore,
) -> None:
    """While the gate is off, new rows hold their payloads inline.

    Older releases in a mixed fleet only read inline values.
    """
    _set_payload_references(store, enabled=False)
    static_pipeline()
    dynamic_pipeline()

    columns = _count_payload_columns(store)
    assert columns["referenced"] == 0
    assert columns["inline"] > 0
    with Session(store.engine) as session:
        assert not session.exec(select(ExecutionPayloadSchema)).all()


@pytest.mark.parametrize(
    "environment, stored",
    [
        ({"replaced": "yes"}, {"replaced": "yes"}),
        ({"too large": "x" * TEXT_FIELD_MAX_LENGTH}, {}),
    ],
    ids=["fits", "too_large"],
)
def test_replaced_placeholder_run_references_its_new_environment(
    store: SqlZenStore, environment: Dict[str, str], stored: Dict[str, str]
) -> None:
    """Replacing a placeholder run replaces its environment payload too.

    An environment too large to store is dropped, as run creation does.
    """
    static_pipeline()
    snapshot_id = (
        store.list_snapshots(
            PipelineSnapshotFilter(project=Client().active_project.id)
        )
        .items[0]
        .id
    )
    placeholder, _ = store.get_or_create_run(
        _run_request(
            snapshot_id,
            status=ExecutionStatus.INITIALIZING,
            start_time=None,
            orchestrator_run_id=None,
            orchestrator_environment={"placeholder": True},
        )
    )
    with Session(store.engine) as session:
        placeholder_schema = session.get(PipelineRunSchema, placeholder.id)
        assert placeholder_schema is not None
        assert placeholder_schema.orchestrator_environment_payload_id

    run, created = store.get_or_create_run(
        _run_request(snapshot_id, orchestrator_environment=environment)
    )

    assert created and run.id == placeholder.id
    assert run.orchestrator_environment == stored
    assert store.get_run(run.id).orchestrator_environment == stored


def test_invalid_snapshot_request_stores_no_payloads(
    store: SqlZenStore,
) -> None:
    """A snapshot request with a missing reference stores no payloads."""
    request = PipelineSnapshotRequest(
        project=Client().active_project.id,
        stack=uuid4(),
        pipeline=uuid4(),
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        client_version="test",
        server_version="test",
        source_code=uuid4().hex,
    )

    with pytest.raises(KeyError):
        store.create_snapshot(request)

    with Session(store.engine) as session:
        assert not session.exec(select(ExecutionPayloadSchema)).all()


@pytest.fixture
def statements(store: SqlZenStore) -> Iterator[List[str]]:
    """The SQL statements the store sends while the test runs."""
    sent: List[str] = []

    def record(*args: Any) -> None:
        sent.append(args[2])

    event.listen(store.engine, "before_cursor_execute", record)
    yield sent
    event.remove(store.engine, "before_cursor_execute", record)


@pytest.mark.parametrize(
    "read",
    [
        "list_runs",
        "list_run_steps",
        "list_snapshots",
        "get_run",
        "get_run_step",
        "get_snapshot",
        "get_run_status",
        "get_entity_by_id",
    ],
)
def test_reads_without_metadata_never_load_payloads(
    store: SqlZenStore, statements: List[str], read: str
) -> None:
    """Lists, status polls and permission fetches never read payloads."""
    static_pipeline()
    project = Client().active_project.id
    run = store.list_runs(PipelineRunFilter(project=project)).items[0]
    step_run = store.list_run_steps(StepRunFilter(project=project)).items[0]
    snapshot_id = run.snapshot.id if run.snapshot else None
    reads: Dict[str, Tuple[Any, ...]] = {
        "list_runs": (
            store.list_runs,
            PipelineRunFilter(project=project),
        ),
        "list_run_steps": (
            store.list_run_steps,
            StepRunFilter(project=project),
        ),
        "list_snapshots": (
            store.list_snapshots,
            PipelineSnapshotFilter(project=project),
        ),
        "get_run": (store.get_run, run.id, False),
        "get_run_step": (store.get_run_step, step_run.id, False),
        "get_snapshot": (store.get_snapshot, snapshot_id, False),
        "get_run_status": (store.get_run_status, run.id),
        "get_entity_by_id": (
            store.get_entity_by_id,
            snapshot_id,
            PipelineSnapshotSchema,
        ),
    }
    method, *args = reads[read]
    statements.clear()

    method(*args)

    assert statements
    assert not [s for s in statements if "execution_payload" in s]
