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

import asyncio
import os
import threading
from datetime import timedelta
from typing import Any, Callable, Dict, Iterator, List, Tuple, Type
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, update
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, col, select

from zenml import pipeline, step
from zenml.client import Client
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.constants import (
    DEFAULT_ZENML_SERVER_PAYLOAD_BACKFILL_DELAY,
    ENV_ZENML_STORE_PREFIX,
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.enums import ExecutionStatus
from zenml.models import (
    PipelineBuildRequest,
    PipelineRequest,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineSnapshotFilter,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    RunTemplateFilter,
    RunTemplateRequest,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_server.payload_backfill_runner import PayloadBackfillTask
from zenml.zen_stores import payload_backfill, sql_zen_store
from zenml.zen_stores.payload_backfill import BACKFILL_MAX_PASSES
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
                select(ExecutionPayloadSchema.id, ExecutionPayloadSchema.value)
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
    """Turn payload references on or off, as the backfill does."""
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


def _open_store(store: SqlZenStore) -> SqlZenStore:
    """Open another store on the same database, as another process would."""
    return SqlZenStore(config=store.config, skip_default_registrations=True)


def _backfill(store: SqlZenStore) -> Any:
    """Run the backfill without pauses or a settle wait."""
    return store.backfill_payloads(pause_seconds=0, gate_settle_seconds=0)


def _gate_is_on(store: SqlZenStore) -> bool:
    """Whether new rows reference their payloads."""
    with Session(store.engine) as session:
        return bool(
            session.exec(
                select(ServerSettingsSchema.payload_references_enabled)
            ).one()
        )


def _read_control_columns(store: SqlZenStore) -> Dict[Tuple[UUID, str], Any]:
    """Read the control columns of every row."""
    with Session(store.engine) as session:
        return {
            (row.id, name): getattr(row, name)
            for schema, names in CONTROL_COLUMNS.items()
            for row in session.exec(select(schema)).all()
            for name in names
        }


def _read_payload_table(store: SqlZenStore) -> set[Tuple[str, int, str]]:
    """Read every stored payload, without the IDs that differ per database."""
    with Session(store.engine) as session:
        return {
            (payload.sha256, payload.size, payload.value)
            for payload in session.exec(select(ExecutionPayloadSchema)).all()
        }


def _make_rows_predate_payloads(store: SqlZenStore) -> None:
    """Hold rows as releases before execution payloads and control columns."""
    _set_payload_references(store, enabled=False)
    _move_payloads_inline(store, every_other=False)
    with Session(store.engine) as session:
        for payload in session.exec(select(ExecutionPayloadSchema)).all():
            session.delete(payload)
        for schema, names in CONTROL_COLUMNS.items():
            session.execute(
                update(schema).values({name: None for name in names})
            )
        session.commit()


def _create_snapshot(store: SqlZenStore) -> PipelineSnapshotResponse:
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
            pipeline_configuration={"name": uuid4().hex},
            client_version="test",
            server_version="test",
            step_configurations=steps,
            pipeline_spec=PipelineSpec(steps=[s.spec for s in steps.values()]),
            source_code=f"def pipeline(): ...  # {uuid4().hex}",
        )
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


def _patch_store_method(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    wrap: Callable[[Callable[..., Any]], Callable[..., Any]],
) -> None:
    """Wrap a method of every store, which Pydantic does not let instances do."""
    monkeypatch.setattr(SqlZenStore, name, wrap(getattr(SqlZenStore, name)))


def test_backfill_stores_existing_rows_as_new_writes_would(
    store: SqlZenStore,
) -> None:
    """The backfill moves inline payloads, fills control columns, flips the gate.

    The table, the control columns and every response end up as the writes
    of this release made them. Small batches cover the scan across batches.
    """
    static_pipeline()
    dynamic_pipeline()
    control_values = _read_control_columns(store)
    payload_table = _read_payload_table(store)
    responses = _hydrated_responses(store)
    _make_rows_predate_payloads(store)
    assert _read_payload_table(store) == set()
    assert not _gate_is_on(store)
    with pytest.raises(ValueError):
        store.backfill_payloads(batch_size=0)

    reports = store.get_payload_backfill_report()

    assert all(report.pending_rows for report in reports)
    assert not _gate_is_on(store)
    assert store.get_payload_backfill_completion() is None

    result = store.backfill_payloads(
        batch_size=3, pause_seconds=0, gate_settle_seconds=0
    )

    assert result.completed
    assert not any(table.failed_rows for table in result.tables)
    assert all(table.duration.count for table in result.tables)
    assert _gate_is_on(store)
    assert store.get_payload_backfill_completion()
    assert _count_payload_columns(store)["inline"] == 0
    assert _read_control_columns(store) == control_values
    assert _read_payload_table(store) == payload_table
    assert _hydrated_responses(store) == responses
    reports = store.get_payload_backfill_report()
    assert [report.pending_rows for report in reports] == [0] * len(
        payload_backfill.BACKFILL_ORDER
    )
    rerun = _backfill(store)
    assert sum(table.rows_updated for table in rerun.tables) == 0


def test_backfill_keeps_a_value_rewritten_while_it_runs(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A value rewritten during a pass is kept, and the next pass moves it.

    A server that reads the gate as off rewrites the orchestrator environment
    inline when it replaces a placeholder run. The new value only differs in
    case, which MySQL collations ignore when comparing text.
    """
    run = _start_run(store)
    _make_rows_predate_payloads(store)
    with Session(store.engine) as session:
        schema = session.get(PipelineRunSchema, run.id)
        assert schema and schema.orchestrator_environment
        original = schema.orchestrator_environment
    rewritten = original.upper()

    def store_while_rewritten(
        real: Callable[..., Any],
    ) -> Callable[..., Any]:
        def wrapper(self: SqlZenStore, values: Any) -> Any:
            values = list(values)
            if any(value.text == original for value in values):
                with Session(store.engine) as session:
                    session.execute(
                        update(PipelineRunSchema)
                        .where(PipelineRunSchema.id == run.id)
                        .values(orchestrator_environment=rewritten)
                    )
                    session.commit()
            return real(self, values)

        return wrapper

    _patch_store_method(monkeypatch, "_store_payloads", store_while_rewritten)
    result = _backfill(store)

    assert result.tables[-1].rows_skipped == 1
    assert result.completed
    assert _count_payload_columns(store)["inline"] == 0
    assert store.get_run(run.id).orchestrator_environment == {
        key.upper(): value.upper()
        for key, value in run.orchestrator_environment.items()
    }


def test_backfill_stops_before_the_payloads_a_failed_row_reads(
    store: SqlZenStore,
) -> None:
    """A step run whose configuration cannot be read stops the backfill.

    Its step configuration and snapshot stay inline until the step run is
    fixed or deleted.
    """
    run = _start_run(store)
    step_run = _start_step(store, run.id)
    _make_rows_predate_payloads(store)
    with Session(store.engine) as session:
        session.execute(
            update(StepRunSchema)
            .where(StepRunSchema.id == step_run.id)
            .values(name="renamed")
        )
        session.commit()

    result = _backfill(store)

    assert not result.completed
    assert list(result.tables[0].failed_rows) == [step_run.id]
    assert not any(table.rows_updated for table in result.tables[1:])
    assert store.get_payload_backfill_completion() is None
    assert _count_payload_columns(store)["referenced"] == 0

    store.delete_run(run.id)
    assert store.backfill_payloads(
        pause_seconds=0, gate_settle_seconds=0
    ).completed
    assert _count_payload_columns(store)["inline"] == 0


def test_backfill_reads_parents_whether_inline_or_referenced(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A step run skipped in every pass stays readable, and a rerun finishes.

    It computes its control columns from its step configuration and snapshot.
    Those are inline while the step run is skipped, and referenced on the
    rerun if only the step run was left behind: the backfill must read both.
    """
    run = _start_run(store)
    step_run = _start_step(store, run.id)
    control_values = _read_control_columns(store)
    _make_rows_predate_payloads(store)

    def store_while_rewritten(
        real: Callable[..., Any],
    ) -> Callable[..., Any]:
        def wrapper(self: SqlZenStore, values: Any) -> Any:
            with Session(store.engine) as session:
                session.execute(
                    update(StepRunSchema)
                    .where(StepRunSchema.id == step_run.id)
                    .values(docstring=uuid4().hex)
                )
                session.commit()
            return real(self, values)

        return wrapper

    with monkeypatch.context() as m:
        _patch_store_method(m, "_store_payloads", store_while_rewritten)
        result = store.backfill_payloads(
            pause_seconds=0, gate_settle_seconds=0
        )

    assert not result.completed
    assert result.tables[0].rows_skipped == BACKFILL_MAX_PASSES
    assert not any(table.rows_updated for table in result.tables[1:])
    assert store.get_payload_backfill_completion() is None
    assert store.get_run_step(step_run.id)

    # Parents moved by an earlier run, the step run still lacking columns.
    parents_only = payload_backfill.BACKFILL_ORDER[1:]
    with monkeypatch.context() as m:
        m.setattr(sql_zen_store, "BACKFILL_ORDER", parents_only)
        _backfill(store)
    assert _count_payload_columns(store)["referenced"] > 0
    assert _read_control_columns(store)[(step_run.id, "substitutions")] is None

    assert store.backfill_payloads(
        pause_seconds=0, gate_settle_seconds=0
    ).completed
    assert _read_control_columns(store) == control_values


def test_backfill_skips_rows_another_backfill_finished(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rows finished by a concurrent backfill after the scan are left alone."""
    _start_step(store, _start_run(store).id)
    _make_rows_predate_payloads(store)
    other = _open_store(store)
    select_rows = sql_zen_store.select_backfill_rows

    def select_rows_finished_meanwhile(*args: Any) -> Any:
        monkeypatch.undo()
        _backfill(other)
        return select_rows(*args)

    monkeypatch.setattr(
        sql_zen_store, "select_backfill_rows", select_rows_finished_meanwhile
    )

    result = _backfill(store)

    assert result.completed
    assert _count_payload_columns(store)["inline"] == 0
    assert sum(table.rows_updated for table in result.tables) == 0


def _write_while_backfilling(
    store: SqlZenStore,
    monkeypatch: pytest.MonkeyPatch,
    write: str,
    run_id: UUID,
) -> Tuple[Any, Any]:
    """Write once while the backfill stores the payloads of a batch.

    Args:
        store: The store to backfill.
        monkeypatch: The monkeypatch fixture.
        write: `update_run` or `create_run_step`.
        run_id: The run to write to.

    Returns:
        The response of the write, and the backfill result.
    """
    writer = _open_store(store)
    responses = []

    def store_while_writing(real: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: SqlZenStore, values: Any) -> Any:
            if not responses and self is not writer:
                if write == "update_run":
                    responses.append(
                        writer.update_run(
                            run_id, PipelineRunUpdate(add_tags=["race"])
                        )
                    )
                else:
                    responses.append(_start_step(writer, run_id))
            return real(self, values)

        return wrapper

    _patch_store_method(monkeypatch, "_store_payloads", store_while_writing)
    result = _backfill(store)
    assert responses
    return responses[0], result


def _create_run_while_backfilling(
    store: SqlZenStore, snapshot_id: UUID
) -> Tuple[PipelineRunResponse, Any]:
    """Create a run, and backfill right after its row commits.

    Run creation reads the snapshot's configuration again after that commit.

    Args:
        store: The store to create the run in.
        snapshot_id: The snapshot to run.

    Returns:
        The created run, and the backfill result.
    """
    other = _open_store(store)
    results = []

    def mark_run_insert(session: Session, context: Any) -> None:
        if any(isinstance(row, PipelineRunSchema) for row in session.new):
            session.info["run_insert"] = True

    def backfill_after_run_commit(session: Session) -> None:
        if session.info.pop("run_insert", False) and not results:
            results.append(_backfill(other))

    event.listen(Session, "after_flush", mark_run_insert)
    event.listen(Session, "after_commit", backfill_after_run_commit)
    try:
        run, _ = store.get_or_create_run(_run_request(snapshot_id))
    finally:
        event.remove(Session, "after_flush", mark_run_insert)
        event.remove(Session, "after_commit", backfill_after_run_commit)
    assert results
    return run, results[0]


@pytest.mark.parametrize(
    "write", ["update_run", "create_run_step", "get_or_create_run"]
)
def test_write_answers_whole_while_backfill_moves_its_rows(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch, write: str
) -> None:
    """A write answers in full while the backfill moves the rows it reads."""
    run = _start_run(store)
    _make_rows_predate_payloads(store)

    if write == "get_or_create_run":
        assert run.snapshot
        response, result = _create_run_while_backfilling(
            store, run.snapshot.id
        )
    else:
        response, result = _write_while_backfilling(
            store, monkeypatch, write, run.id
        )

    assert result.completed
    assert _count_payload_columns(store)["inline"] == 0
    fresh: Any = (
        store.get_run_step(response.id)
        if write == "create_run_step"
        else store.get_run(response.id)
    )
    assert response.get_metadata() == fresh.get_metadata()


def _run_with_stragglers(
    store: SqlZenStore,
    monkeypatch: pytest.MonkeyPatch,
    passes_with_writes: int,
) -> Tuple[Any, SqlZenStore]:
    """Backfill while a process that reads the gate as off keeps writing.

    Args:
        store: The store to backfill.
        monkeypatch: The monkeypatch fixture.
        passes_with_writes: The passes after which the straggler writes a new
            run inline.

    Returns:
        The backfill result, and the straggler.
    """
    straggler = _open_store(store)
    _patch_store_method(
        monkeypatch,
        "_payload_references_enabled",
        lambda real: lambda self: False if self is straggler else real(self),
    )
    finished_passes = []

    def write_after_each_pass(real: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(
            self: SqlZenStore, schema: Type[Any], *args: Any, **kwargs: Any
        ) -> Any:
            lacking = real(self, schema, *args, **kwargs)
            if schema is PipelineRunSchema:
                finished_passes.append(schema)
                if len(finished_passes) <= passes_with_writes:
                    _start_run(straggler)
            return lacking

        return wrapper

    _patch_store_method(monkeypatch, "_backfill_table", write_after_each_pass)
    result = _backfill(store)
    return result, straggler


def test_backfill_catches_a_straggler_that_wrote_inline_after_the_gate_turned_on(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rows a straggler writes inline behind a pass are moved by the next.

    The straggler is a store whose read of the gate says off, like a request
    that read it just before the backfill turned it on.
    """
    static_pipeline()
    _make_rows_predate_payloads(store)

    result, _ = _run_with_stragglers(store, monkeypatch, passes_with_writes=1)

    assert result.completed
    assert store.get_payload_backfill_completion()
    assert _count_payload_columns(store)["inline"] == 0
    assert [r.pending_rows for r in store.get_payload_backfill_report()] == [
        0
    ] * 4


def test_backfill_does_not_complete_while_a_straggler_keeps_writing(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A process that writes inline in every pass stops completion.

    Completion is recorded once the straggler is gone, by a later run.
    """
    static_pipeline()
    _make_rows_predate_payloads(store)

    result, _ = _run_with_stragglers(
        store, monkeypatch, passes_with_writes=BACKFILL_MAX_PASSES
    )

    assert not result.completed
    assert store.get_payload_backfill_completion() is None
    assert _count_payload_columns(store)["inline"] > 0
    monkeypatch.undo()

    assert store.backfill_payloads(
        pause_seconds=0, gate_settle_seconds=0
    ).completed
    assert _count_payload_columns(store)["inline"] == 0


def test_backfill_retries_a_batch_rolled_back_by_a_deadlock(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deadlock with a server transaction costs a pass, not the backfill."""
    _start_run(store)
    _make_rows_predate_payloads(store)
    deadlocks = []
    build = sql_zen_store.build_backfill_update

    def build_with_one_deadlock(*args: Any) -> Any:
        if not deadlocks:
            deadlocks.append(args[1])
            raise OperationalError(
                "UPDATE", {}, Exception(1213, "Deadlock found")
            )
        return build(*args)

    monkeypatch.setattr(
        sql_zen_store, "build_backfill_update", build_with_one_deadlock
    )

    result = _backfill(store)

    assert deadlocks
    assert sum(table.rows_skipped for table in result.tables) > 0
    assert result.completed
    assert _count_payload_columns(store)["inline"] == 0


def test_servers_finish_the_backfill_across_a_restart(
    store: SqlZenStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Servers run the backfill once it is due, and a restart resumes it.

    A server that shuts down during the backfill stops it without recording
    completion; the next server to start finishes it.
    """
    _start_run(store)
    _make_rows_predate_payloads(store)
    with Session(store.engine) as session:
        session.execute(
            update(ServerSettingsSchema).values(
                execution_payloads_added=utc_now() - timedelta(hours=2)
            )
        )
        session.commit()
    _patch_store_method(
        monkeypatch,
        "backfill_payloads",
        lambda real: (
            lambda self, **kwargs: real(
                self, **kwargs, pause_seconds=0, gate_settle_seconds=0
            )
        ),
    )
    batch_reached, batch_released = threading.Event(), threading.Event()

    def hold_first_batch(real: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: SqlZenStore, *args: Any) -> Any:
            batch_reached.set()
            batch_released.wait(30)
            return real(self, *args)

        return wrapper

    _patch_store_method(monkeypatch, "_backfill_rows", hold_first_batch)

    async def shut_down_during_first_batch() -> None:
        server = PayloadBackfillTask(
            store, DEFAULT_ZENML_SERVER_PAYLOAD_BACKFILL_DELAY
        )
        server.start()
        try:
            assert await asyncio.to_thread(batch_reached.wait, 30)
        finally:
            # Shutdown first, so that the held batch is the last one.
            shutdown = asyncio.create_task(server.shutdown())
            await asyncio.sleep(0)
            batch_released.set()
            await shutdown

    async def run_until_completed() -> None:
        server = PayloadBackfillTask(
            store, DEFAULT_ZENML_SERVER_PAYLOAD_BACKFILL_DELAY
        )
        server.start()
        for _ in range(300):
            if await asyncio.to_thread(store.get_payload_backfill_completion):
                break
            await asyncio.sleep(0.1)
        await server.shutdown()

    asyncio.run(shut_down_during_first_batch())

    assert store.get_payload_backfill_completion() is None
    assert _count_payload_columns(store)["inline"] > 0

    asyncio.run(run_until_completed())

    assert store.get_payload_backfill_completion()
    assert _gate_is_on(store)
    assert _count_payload_columns(store)["inline"] == 0
