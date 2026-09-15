"""Bounded, restartable maintenance for existing snapshot/configuration text.

Maintenance deliberately reflects raw columns: the ORM hides their storage
encoding and rejects already encoded writes. Only the shared codec produces
replacement values; ordinary application reads/writes continue through the ORM.
"""

import hashlib
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import MetaData, Table, create_engine, func, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from zenml.config.store_config import StoreConfiguration
from zenml.enums import StoreType
from zenml.zen_stores.compressed_text import (
    COMPRESSED_TEXT_MARKER,
    MAX_DECOMPRESSED_TEXT_BYTES,
    MIN_COMPRESSIBLE_BYTES,
    decode_compressed_text,
    encode_compressed_text,
)

COLUMNS = {
    "pipeline_snapshot": (
        "pipeline_configuration",
        "client_environment",
        "pipeline_spec",
        "source_code",
    ),
    "step_configuration": ("config",),
}


class BackfillProgress(BaseModel):
    """Local progress, bound to one database, schema revision and mode.

    Counts describe checkpointed work. A crash after SQL commit but before the
    checkpoint can undercount changes; restarting still safely covers the rows.
    """

    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    target: str
    revisions: list[str]
    apply: bool
    upper_ids: dict[str, Optional[str]]
    cursors: dict[str, str] = Field(default_factory=dict)
    completed: set[str] = Field(default_factory=set)
    scanned: int = 0
    changed: int = 0
    bytes_before: int = 0
    bytes_after: int = 0


def _save(path: Path, progress: BackfillProgress) -> None:
    with path.with_name(path.name + ".tmp").open("w") as stream:
        stream.write(progress.model_dump_json(indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.with_name(path.name + ".tmp").replace(path)


def _batch(
    connection: Connection,
    table: Table,
    column: str,
    progress: BackfillProgress,
    batch_size: int,
    byte_budget: int,
) -> None:
    key = f"{table.name}.{column}"
    upper = progress.upper_ids[table.name]
    query = select(table.c.id).order_by(table.c.id).limit(batch_size)
    if upper is None:
        progress.completed.add(key)
        return
    query = query.where(table.c.id <= upper)
    if key in progress.cursors:
        query = query.where(table.c.id > progress.cursors[key])
    ids = connection.execute(query).scalars().all()
    consumed = 0
    for row_id in ids:
        cell = table.c[column]
        query = select(cell).where(table.c.id == row_id)
        if progress.apply:
            query = query.with_for_update()
        value = connection.execute(query).scalar_one_or_none()
        if value is not None:
            size = len(value.encode("utf-8"))
            consumed += size
            encoded = value
            if value.startswith(COMPRESSED_TEXT_MARKER):
                decode_compressed_text(value, key)
            elif MIN_COMPRESSIBLE_BYTES <= size <= MAX_DECOMPRESSED_TEXT_BYTES:
                candidate = encode_compressed_text(value)
                if len(candidate) < size:
                    encoded = candidate
            progress.bytes_before += size
            progress.bytes_after += len(encoded.encode("utf-8"))
            if encoded != value:
                if progress.apply:
                    connection.execute(
                        table.update()
                        .where(table.c.id == row_id)
                        .values({column: encoded})
                    )
                progress.changed += 1
        progress.scanned += 1
        progress.cursors[key] = row_id
        if consumed >= byte_budget:
            break
    else:
        if len(ids) < batch_size:
            progress.completed.add(key)


def backfill_compressed_text(
    engine: Engine,
    checkpoint: Path,
    *,
    apply: bool = False,
    batch_size: int = 100,
    max_batches: int = 10,
    byte_budget: int = 8 * 1024 * 1024,
) -> BackfillProgress:
    """Process bounded batches using a dedicated maintenance engine.

    SQL commits precede checkpoint writes; replay never double-compresses.
    MySQL locks each value before reading it; SQLite reserves the writer before
    reading a batch. Only payload columns are updated, never row timestamps.
    A batch reads at most the byte budget plus one column value, one at a time.
    The Linux/macOS checkpoint lock propagates BlockingIOError if busy.

    Args:
        engine: Dedicated engine for one already migrated database.
        checkpoint: Persistent local checkpoint; use different files per mode.
        apply: Whether to write SQL; otherwise measure potential savings only.
        batch_size: Maximum values examined in each transaction (1–1000).
        max_batches: Maximum transactions in this invocation (1–10000).
        byte_budget: Stop a batch after reading this many raw payload bytes.

    Returns:
        Cumulative checkpointed progress, including completed columns.

    Raises:
        ValueError: If limits, dialect, checkpoint identity or revision differ,
            or if the platform has no advisory file locks.
    """
    try:
        import fcntl
    except ImportError:
        raise ValueError(
            "The backfill needs advisory file locks and runs on Linux and "
            "macOS only."
        ) from None

    if (
        not 1 <= batch_size <= 1000
        or not 1 <= max_batches <= 10000
        or byte_budget < 1
    ):
        raise ValueError("Invalid backfill bounds.")
    if engine.dialect.name not in {"mysql", "mariadb", "sqlite"}:
        raise ValueError("Backfill supports only MySQL, MariaDB and SQLite.")
    database = engine.url.database
    if engine.dialect.name == "sqlite":
        if not database or database == ":memory:":
            raise ValueError("Backfill requires a persistent database.")
        database = str(Path(database).resolve())
    identity = (
        engine.url.host,
        engine.url.port,
        database,
        engine.url.query.get("unix_socket"),
        engine.dialect.name,
    )
    target = hashlib.sha256(repr(identity).encode()).hexdigest()
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint.with_name(checkpoint.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with engine.connect() as connection:
            metadata = MetaData()
            tables = {
                name: Table(
                    name,
                    metadata,
                    autoload_with=connection,
                    include_columns=["id", *columns],
                    resolve_fks=False,
                )
                for name, columns in COLUMNS.items()
            }
            revision_table = Table(
                "alembic_version", metadata, autoload_with=connection
            )
            revisions = sorted(
                connection.execute(
                    select(revision_table.c.version_num)
                ).scalars()
            )
            if checkpoint.exists():
                progress = BackfillProgress.model_validate_json(
                    checkpoint.read_text()
                )
                if (progress.target, progress.apply, progress.revisions) != (
                    target,
                    apply,
                    revisions,
                ):
                    raise ValueError(
                        "Checkpoint database, mode or schema revision differs."
                    )
            else:
                upper_ids = {
                    name: connection.scalar(select(func.max(table.c.id)))
                    for name, table in tables.items()
                }
                progress = BackfillProgress(
                    target=target,
                    apply=apply,
                    revisions=revisions,
                    upper_ids=upper_ids,
                )
                _save(checkpoint, progress)
        for _ in range(max_batches):
            remaining = [
                (tables[name], column)
                for name, columns in COLUMNS.items()
                for column in columns
                if f"{name}.{column}" not in progress.completed
            ]
            if not remaining:
                break
            table, column = remaining[0]
            with engine.begin() as connection:
                if apply and engine.dialect.name == "sqlite":
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                elif apply:
                    connection.exec_driver_sql(
                        "SET SESSION innodb_lock_wait_timeout = 5"
                    )
                _batch(
                    connection,
                    table,
                    column,
                    progress,
                    batch_size,
                    byte_budget,
                )
            _save(checkpoint, progress)
    return progress


def backfill_from_config(
    config: StoreConfiguration,
    checkpoint: Path,
    *,
    apply: bool,
    batch_size: int,
    max_batches: int,
) -> BackfillProgress:
    """Run maintenance without initializing or migrating a ZenML store.

    Args:
        config: Existing direct SQL configuration, including authentication.
        checkpoint: Persistent local progress file.
        apply: Whether to compress existing values.
        batch_size: Values examined per transaction.
        max_batches: Maximum transactions for this pass.

    Returns:
        Cumulative progress for the selected mode.

    Raises:
        ValueError: If not directly connected to SQL or compressed writes are off.
        RuntimeError: If a database operation fails.
    """
    from zenml.zen_stores.sql_zen_store import SqlZenStoreConfiguration

    if config.type != StoreType.SQL:
        raise ValueError("Backfill requires a direct SQL store configuration.")
    config = SqlZenStoreConfiguration.model_validate(config.model_dump())
    if apply and not config.compress_text_payloads:
        raise ValueError(
            "Enable compress_text_payloads only after all readers have been upgraded."
        )
    url, connect_args, engine_args = config.get_sqlalchemy_config()
    if url.get_backend_name() == "mysql":
        connect_args.update(
            connect_timeout=10, read_timeout=30, write_timeout=30
        )
    else:
        connect_args["timeout"] = 5
    engine = create_engine(url, connect_args=connect_args, **engine_args)
    config.configure_engine_auth(engine)
    try:
        return backfill_compressed_text(
            engine,
            checkpoint,
            apply=apply,
            batch_size=batch_size,
            max_batches=max_batches,
        )
    except SQLAlchemyError as error:
        # Driver exceptions can contain the source code/environment in bind
        # parameters. The operator only needs the error class and checkpoint.
        raise RuntimeError(
            f"Backfill stopped ({type(error).__name__}); rerun with the same checkpoint."
        ) from None
    finally:
        engine.dispose()
