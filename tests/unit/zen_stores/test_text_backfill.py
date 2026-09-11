"""Maintenance backfill preserves content and resumes across partial failures."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from click.testing import CliRunner
from sqlalchemy import MetaData, Table, event, select

from zenml.cli.base import backfill_database
from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.models import PipelineRequest, PipelineSnapshotRequest
from zenml.zen_stores.compressed_text import (
    COMPRESSED_TEXT_PREFIX,
    decode_compressed_text,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore
from zenml.zen_stores.text_backfill import (
    COLUMNS,
    backfill_compressed_text,
    backfill_from_config,
)


@pytest.fixture
def store(clean_client: Client) -> SqlZenStore:
    """Create real snapshots and step configurations through the store."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    pipeline = store.create_pipeline(
        PipelineRequest(
            project=clean_client.active_project.id, name="backfill"
        )
    )
    for i in range(3):
        store.create_snapshot(
            PipelineSnapshotRequest(
                project=clean_client.active_project.id,
                pipeline=pipeline.id,
                stack=clean_client.active_stack.id,
                run_name_template="run",
                pipeline_configuration=PipelineConfiguration(name="backfill"),
                client_environment={"details": "α" * 1000},
                client_version="test",
                server_version="test",
                source_code="x = '" + "α" * 1000 + "'" if i else None,
                step_configurations={
                    "step": Step(
                        spec=StepSpec(
                            source=Source(
                                module="acme", type=SourceType.INTERNAL
                            ),
                            upstream_steps=[],
                        ),
                        config=StepConfiguration(
                            name="step", parameters={"payload": "x" * 1000}
                        ),
                    )
                },
            )
        )
    return store


def _raw(store: SqlZenStore) -> dict[str, list[dict[str, Any]]]:
    with store.engine.connect() as connection:
        return {
            name: [
                dict(row)
                for row in connection.execute(
                    select(table).order_by(table.c.id)
                ).mappings()
            ]
            for name in COLUMNS
            for table in [
                Table(
                    name,
                    MetaData(),
                    autoload_with=connection,
                    resolve_fks=False,
                )
            ]
        }


def test_dry_run_resume_and_exact_content_parity(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """Dry-run is read-only; bounded passes finish with identical decoded rows."""
    before = _raw(store)
    details = [
        store.get_snapshot(UUID(row["id"])).model_dump()
        for row in before["pipeline_snapshot"]
    ]
    checkpoint = tmp_path / "dry.json"
    dry = backfill_compressed_text(store.engine, checkpoint, max_batches=100)
    assert len(dry.completed) == 5 and dry.changed > 0
    assert dry.bytes_after < dry.bytes_before and _raw(store) == before
    checkpoint = tmp_path / "apply.json"
    progress = backfill_compressed_text(
        store.engine, checkpoint, apply=True, batch_size=1, max_batches=1
    )
    assert progress.scanned == 1 and len(progress.completed) < 5
    for _ in range(30):
        progress = backfill_compressed_text(
            store.engine, checkpoint, apply=True, batch_size=1, max_batches=1
        )
        if len(progress.completed) == 5:
            break
    assert len(progress.completed) == 5 and progress.changed == dry.changed
    after = _raw(store)
    assert any(
        row["config"].startswith(COMPRESSED_TEXT_PREFIX)
        for row in after["step_configuration"]
    )
    for name, rows in after.items():
        for row in rows:
            for column in COLUMNS[name]:
                if row[column] is not None:
                    row[column] = decode_compressed_text(row[column], column)
    assert after == before
    assert [
        store.get_snapshot(UUID(row["id"])).model_dump()
        for row in before["pipeline_snapshot"]
    ] == details
    again = backfill_compressed_text(
        store.engine, tmp_path / "again.json", apply=True, max_batches=100
    )
    assert again.changed == 0


def test_checkpoint_cannot_change_mode_or_database(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """A cursor cannot silently skip work when reused against a new scope."""
    checkpoint = tmp_path / "progress.json"
    backfill_compressed_text(store.engine, checkpoint, max_batches=1)
    with pytest.raises(ValueError, match="differs"):
        backfill_compressed_text(store.engine, checkpoint, apply=True)
    state = json.loads(checkpoint.read_text())
    state["target"] = "different database"
    checkpoint.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="differs"):
        backfill_compressed_text(store.engine, checkpoint)


def test_failed_batch_rolls_back(store: SqlZenStore, tmp_path: Path) -> None:
    """A driver failure cannot leave a partially committed batch."""
    before = _raw(store)
    updates = 0

    def fail_second_update(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        many: bool,
    ) -> None:
        nonlocal updates
        if statement.startswith("UPDATE"):
            updates += 1
            if updates == 2:
                raise RuntimeError("interrupted write")

    event.listen(store.engine, "before_cursor_execute", fail_second_update)
    checkpoint = tmp_path / "apply.json"
    try:
        with pytest.raises(RuntimeError, match="interrupted write"):
            backfill_compressed_text(store.engine, checkpoint, apply=True)
    finally:
        event.remove(store.engine, "before_cursor_execute", fail_second_update)
    assert _raw(store) == before
    assert json.loads(checkpoint.read_text())["scanned"] == 0
    assert (
        backfill_compressed_text(
            store.engine, checkpoint, apply=True, max_batches=100
        ).changed
        > 0
    )


def test_commit_before_checkpoint_failure_is_replayable(
    store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Losing the checkpoint after SQL commit never double-compresses data."""
    checkpoint = tmp_path / "apply.json"
    replace = Path.replace
    calls = 0

    def fail_after_commit(path: Path, target: Any) -> Path:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("checkpoint unavailable")
        return replace(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_after_commit)
        with pytest.raises(OSError, match="checkpoint unavailable"):
            backfill_compressed_text(
                store.engine,
                checkpoint,
                apply=True,
                batch_size=1,
                max_batches=1,
            )
    assert json.loads(checkpoint.read_text())["scanned"] == 0
    progress = backfill_compressed_text(
        store.engine, checkpoint, apply=True, max_batches=100
    )
    assert len(progress.completed) == 5
    assert (
        backfill_compressed_text(
            store.engine, tmp_path / "verify.json", max_batches=100
        ).changed
        == 0
    )


def test_apply_requires_write_rollout(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """A configured reader alone does not authorize compressed writes."""
    before = _raw(store)
    with pytest.raises(ValueError, match="Enable compress_text_payloads"):
        backfill_from_config(
            store.config,
            tmp_path / "apply.json",
            apply=True,
            batch_size=1,
            max_batches=1,
        )
    assert _raw(store) == before


def test_cli_dry_run_and_apply(
    store: SqlZenStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operators get dry-run progress, rollout gating and resumable apply."""
    runner = CliRunner()
    before = _raw(store)
    result = runner.invoke(
        backfill_database,
        ["--checkpoint", str(tmp_path / "dry.json"), "--max-batches", "100"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["changed"] > 0
    assert _raw(store) == before
    args = [
        "--apply",
        "--checkpoint",
        str(tmp_path / "apply.json"),
        "--max-batches",
        "100",
    ]
    assert runner.invoke(backfill_database, args).exit_code != 0
    monkeypatch.setenv("ZENML_STORE_COMPRESS_TEXT_PAYLOADS", "true")
    monkeypatch.setenv("ZENML_STORE_URL", store.config.url)
    result = runner.invoke(backfill_database, args)
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.output)["completed"]) == 5


@pytest.mark.parametrize("failure", ["corrupt", "unknown version"])
def test_malformed_encoded_value_stops_without_writing(
    store: SqlZenStore,
    tmp_path: Path,
    failure: str,
) -> None:
    """Malformed or unsupported stored encodings cannot be silently rewritten."""
    with store.engine.begin() as connection:
        table = Table(
            "pipeline_snapshot",
            MetaData(),
            autoload_with=connection,
            resolve_fks=False,
        )
        marker = (
            COMPRESSED_TEXT_PREFIX
            if failure == "corrupt"
            else COMPRESSED_TEXT_PREFIX.replace("v1:", "v9:")
        )
        connection.execute(
            table.update().values(pipeline_configuration=marker + "broken")
        )
    before = _raw(store)
    with pytest.raises(RuntimeError):
        backfill_compressed_text(
            store.engine, tmp_path / "apply.json", apply=True
        )
    assert _raw(store) == before


def test_byte_budget_and_checkpoint_exclusivity(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """A large cell ends the batch, and another process cannot share its cursor."""
    import fcntl

    checkpoint = tmp_path / "progress.json"
    progress = backfill_compressed_text(
        store.engine, checkpoint, max_batches=1, byte_budget=1
    )
    assert progress.scanned == 1
    with checkpoint.with_name(checkpoint.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            backfill_compressed_text(store.engine, checkpoint)


def test_new_rows_are_left_for_a_later_sweep(
    store: SqlZenStore, tmp_path: Path
) -> None:
    """A finite pass does not chase new writes beyond its captured ID ceiling."""
    checkpoint = tmp_path / "apply.json"
    backfill_compressed_text(
        store.engine, checkpoint, apply=True, max_batches=1
    )
    with store.engine.begin() as connection:
        table = Table(
            "pipeline_snapshot",
            MetaData(),
            autoload_with=connection,
            resolve_fks=False,
        )
        row = dict(connection.execute(select(table).limit(1)).mappings().one())
        row.update(
            id="f" * 32, client_environment='{"late": "' + "x" * 1000 + '"}'
        )
        connection.execute(table.insert().values(row))
    backfill_compressed_text(
        store.engine, checkpoint, apply=True, max_batches=100
    )
    assert next(
        row
        for row in _raw(store)["pipeline_snapshot"]
        if row["id"] == "f" * 32
    )["client_environment"].startswith('{"late"')


def test_concurrent_writer_is_not_overwritten(
    store: SqlZenStore,
    tmp_path: Path,
) -> None:
    """The batch reserves the writer before reading, so later writes win."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    from threading import Event

    with store.engine.connect() as connection:
        table = Table(
            "pipeline_snapshot",
            MetaData(),
            autoload_with=connection,
            resolve_fks=False,
        )
        row_id = connection.scalar(
            select(table.c.id).order_by(table.c.id).limit(1)
        )
    locked, release, writing = Event(), Event(), Event()

    def hold_read(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        many: bool,
    ) -> None:
        if (
            statement.startswith(
                "SELECT pipeline_snapshot.pipeline_configuration"
            )
            and not locked.is_set()
        ):
            locked.set()
            assert release.wait(5)

    def writer() -> None:
        with store.engine.begin() as connection:
            writing.set()
            connection.execute(
                table.update()
                .where(table.c.id == row_id)
                .values(pipeline_configuration='{"name":"changed"}')
            )

    event.listen(store.engine, "after_cursor_execute", hold_read)
    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            backfill = workers.submit(
                backfill_compressed_text,
                store.engine,
                tmp_path / "apply.json",
                apply=True,
                max_batches=1,
            )
            try:
                assert locked.wait(5)
                write = workers.submit(writer)
                assert writing.wait(5)
                with pytest.raises(TimeoutError):
                    write.result(timeout=0.1)
            finally:
                release.set()
            backfill.result(timeout=5)
            write.result(timeout=5)
    finally:
        event.remove(store.engine, "after_cursor_execute", hold_read)
    assert (
        next(
            row
            for row in _raw(store)["pipeline_snapshot"]
            if row["id"] == row_id
        )["pipeline_configuration"]
        == '{"name":"changed"}'
    )
