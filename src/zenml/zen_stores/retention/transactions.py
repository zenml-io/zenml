# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Transactions and row locks for retention writes.

Execution retention only runs on MySQL. Retention opens sessions directly so
each phase controls its transaction from the first read. Mutations use
``READ COMMITTED`` so locking one run's rows takes no gap locks that would
block writers of unrelated runs.

Every retention mutation locks rows in the same order: the run, its steps,
its owned snapshots, then their step configurations. Ordinary writers that
lock a step before its run can still deadlock with retirement; MySQL then
rolls one of them back and archiving skips that run.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Iterator, List, Type, TypeVar, cast
from uuid import UUID

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, col

from zenml.zen_stores.schemas import BaseSchema

T = TypeVar("T")

# MySQL error codes for a deadlock victim and a lock wait timeout.
_TRANSIENT_LOCK_ERRORS = frozenset({1205, 1213})
_ROLLBACK_CONFIRMED = "zenml_retention_rollback_confirmed"


@contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    """Commit a short mutation transaction only after its body succeeds.

    Args:
        engine: Metadata MySQL database.

    Yields:
        Caller-owned mutation session.

    Raises:
        BaseException: The transaction body, rollback, or commit failed.
    """
    with engine.connect() as connection:
        connection = connection.execution_options(
            isolation_level="READ COMMITTED"
        )
        database_transaction = connection.begin()
        with Session(connection, expire_on_commit=False) as session:
            try:
                yield session
                session.flush()
            except BaseException:
                database_transaction.rollback()
                session.info[_ROLLBACK_CONFIRMED] = True
                raise
            else:
                # A failure here has an unknown server-side outcome. Do not
                # attempt to turn it into a claimed rollback after COMMIT began.
                database_transaction.commit()


def rollback_was_confirmed(session: Session) -> bool:
    """Tell whether ``transaction`` completed rollback for this session.

    Args:
        session: Session yielded by ``transaction``.

    Returns:
        Whether its failed body was rolled back before the error escaped.
    """
    return session.info.get(_ROLLBACK_CONFIRMED) is True


def is_transient_lock_error(error: BaseException) -> bool:
    """Classify a MySQL deadlock or lock-wait timeout error.

    Args:
        error: Exception raised by a retention transaction.

    Returns:
        True for a deadlock victim or a lock wait timeout. Callers decide
        rollback certainty separately.
    """
    if not isinstance(error, OperationalError) or error.orig is None:
        return False
    arguments = error.orig.args
    return bool(arguments) and arguments[0] in _TRANSIENT_LOCK_ERRORS


def database_now(session: Session) -> datetime:
    """Read the database clock shared by all server replicas.

    Args:
        session: Current transaction.

    Returns:
        Naive UTC timestamp, comparable with the `utc_now()` values stored in
        execution rows.
    """
    # MySQL's CURRENT_TIMESTAMP follows the session time zone, which would
    # shift every age comparison on a non-UTC server.
    # SQLite's is always UTC and has no UTC_TIMESTAMP function.
    clock = (
        func.utc_timestamp()
        if session.get_bind().dialect.name == "mysql"
        else func.current_timestamp()
    )
    return cast(datetime, session.execute(select(clock)).scalar_one())


def batches(values: Iterable[T]) -> Iterator[List[T]]:
    """Yield deduplicated values in stable, bounded batches.

    Args:
        values: Identities or composite keys.

    Yields:
        At most 1,000 values, keeping each IN list well below MySQL's packet
        limit.
    """
    ordered = sorted(set(values), key=str)
    for start in range(0, len(ordered), 1000):
        yield ordered[start : start + 1000]


def lock_ids(
    session: Session, schema: Type[BaseSchema], ids: Iterable[UUID]
) -> None:
    """Lock known rows in identity order without reading their payloads.

    Args:
        session: Current mutation transaction.
        schema: Table holding the rows.
        ids: Row identities.
    """
    for group in batches(ids):
        session.execute(
            select(col(schema.id))
            .where(col(schema.id).in_(group))
            .order_by(col(schema.id))
            .with_for_update()
        ).all()
