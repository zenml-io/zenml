# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""SQL transaction boundaries and the shared execution-detail lock order.

Retention opens sessions directly so every phase controls its transaction from
the first authority read. MySQL uses ``READ COMMITTED`` to avoid gap locks on
unrelated trees; SQLite uses ``BEGIN IMMEDIATE`` for mutation phases so no
writer can slip between validation and the first fenced update. The store's
general session helpers do not provide these isolation guarantees.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from sqlite3 import Connection as SQLiteConnection
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from alembic.migration import MigrationContext
from sqlalchemy import (
    Connection,
    Delete,
    Engine,
    Insert,
    Update,
    func,
    select,
    update,
)
from sqlmodel import Session, col

from zenml.enums import RetentionFailure
from zenml.exceptions import (
    ExecutionRetentionConflictError,
    ExecutionRetentionIntegrityError,
)
from zenml.zen_stores.schemas import BaseSchema, PipelineRunSchema

T = TypeVar("T")


@contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    """Commit a short mutation transaction only after its body succeeds.

    Args:
        engine: Metadata database for the retention mutation.

    Yields:
        Caller-owned mutation session.
    """
    with engine.connect() as connection:
        if engine.dialect.name in ("mysql", "mariadb"):
            # READ COMMITTED avoids gap locks blocking unrelated execution trees.
            connection = connection.execution_options(
                isolation_level="READ COMMITTED"
            )
        with (
            connection.begin(),
            Session(connection, expire_on_commit=False) as session,
        ):
            _begin_sqlite(connection, immediate=True)
            yield session
            session.flush()


def _begin_sqlite(connection: Connection, *, immediate: bool = False) -> None:
    """Begin an explicit SQLite read or mutation transaction.

    Args:
        connection: Current SQLAlchemy transaction connection.
        immediate: Acquire write exclusion before reading mutation authority.
    """
    if connection.dialect.name == "sqlite":
        driver = cast(
            SQLiteConnection, connection.connection.driver_connection
        )
        if not driver.in_transaction:
            connection.exec_driver_sql(
                "BEGIN IMMEDIATE" if immediate else "BEGIN"
            )


def begin_read(session: Session) -> None:
    """Read retention authority and detail from one consistent snapshot.

    Args:
        session: Caller-owned session for one phase of a retention detail read.
    """
    _begin_sqlite(session.connection())


def begin_write(session: Session) -> None:
    """Acquire SQLite write exclusion before reading mutation authority.

    Args:
        session: Caller-owned session for a guarded store mutation.
    """
    _begin_sqlite(session.connection(), immediate=True)


def database_now(session: Session) -> datetime:
    """Read the database clock shared by all workers.

    Args:
        session: Current transaction.

    Returns:
        Timestamp in the database session's configured time zone.
    """
    return cast(
        datetime,
        session.execute(select(func.current_timestamp())).scalar_one(),
    )


def require_one(
    session: Session, statement: Union[Insert, Update, Delete]
) -> None:
    """Execute a conditional mutation that must affect exactly one row.

    Args:
        session: Current transaction.
        statement: Fenced row insertion, update or deletion.

    Raises:
        ExecutionRetentionConflictError: If the expected claim no longer matches.
    """
    if session.connection().execute(statement).rowcount != 1:
        raise ExecutionRetentionConflictError(
            "Retention claim expired or was replaced.",
            error_code=RetentionFailure.BUSY,
        )


def update_identity(
    session: Session,
    schema: Type[BaseSchema],
    identity: UUID,
    values: Dict[str, Any],
) -> None:
    """Update exactly one known schema identity under the caller's fences.

    Args:
        session: Current mutation transaction.
        schema: SQL schema selected from a typed record mapping.
        identity: Retained row identity.
        values: Explicit payload and marker assignments.
    """
    require_one(
        session,
        update(schema).where(col(schema.id) == identity).values(**values),
    )


def lock_root(
    session: Session, project_id: UUID, root_id: UUID
) -> PipelineRunSchema:
    """Lock a surviving canonical root belonging to the authorized project.

    Args:
        session: Current mutation transaction.
        project_id: Authorized project identity.
        root_id: Canonical root identity.

    Returns:
        Refreshed root header.

    Raises:
        ExecutionRetentionConflictError: If the root disappeared or is not canonical.
    """
    root = session.execute(
        select(PipelineRunSchema)
        .filter_by(id=root_id, project_id=project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if (
        root is None
        or root.parent_run_id is not None
        or root.root_run_id not in (None, root.id)
    ):
        raise ExecutionRetentionConflictError(
            "Retention requires a surviving canonical execution root.",
            error_code=RetentionFailure.BUSY,
        )
    return cast(PipelineRunSchema, root)


def batches(values: Iterable[T]) -> Iterator[List[T]]:
    """Yield deduplicated identities in stable, bind-limited batches.

    Args:
        values: Bounded identities or two-column definition keys.

    Yields:
        At most 400 values, leaving room for paired keys and fixed binds.
    """
    ordered = sorted(set(values), key=str)
    for start in range(0, len(ordered), 400):
        yield ordered[start : start + 400]


def lock_ids(
    session: Session, schema: Type[BaseSchema], ids: Iterable[UUID]
) -> None:
    """Lock one ordered identity set without transferring payload columns.

    Args:
        session: Final mutation transaction.
        schema: Explicit SQL schema selected by the caller.
        ids: Previously captured identities.
    """
    for group in batches(ids):
        session.execute(
            select(col(schema.id))
            .where(col(schema.id).in_(group))
            .order_by(col(schema.id))
            .with_for_update()
        ).all()


def writer_revision(session: Session) -> str:
    """Read the single Alembic revision from the mutation connection.

    Args:
        session: Current short SQL transaction.

    Returns:
        Writer revision checked before retirement or restore.

    Raises:
        ExecutionRetentionIntegrityError: If no versioned writer schema exists.
    """
    revision = MigrationContext.configure(
        session.connection()
    ).get_current_revision()
    if revision is None:
        raise ExecutionRetentionIntegrityError(
            "Retention requires a versioned database schema."
        )
    return revision
