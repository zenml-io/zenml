#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Two-connection authority-switch tests for MySQL locking semantics.

SQLite serializes writers and ignores ``SELECT ... FOR UPDATE``. Set
``ZENML_TEST_EXECUTION_ARCHIVE_MYSQL_URL`` to a MySQL server URL whose user may
create temporary databases to exercise the real race; otherwise these tests
are skipped.
"""

import os
import threading
from pathlib import Path
from typing import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, col, select

from tests.unit.zen_stores.execution_archive.service import authority, exporter
from tests.unit.zen_stores.execution_archive.utils import populate_family
from zenml.enums import ExecutionArchiveState
from zenml.zen_stores.execution_archive.catalog import ExecutionArchiveCatalog
from zenml.zen_stores.schemas import PipelineSnapshotSchema
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)

MYSQL_URL = os.environ.get("ZENML_TEST_EXECUTION_ARCHIVE_MYSQL_URL")

pytestmark = pytest.mark.skipif(
    not MYSQL_URL, reason="ZENML_TEST_EXECUTION_ARCHIVE_MYSQL_URL is not set"
)


@pytest.fixture
def mysql_store() -> Iterator[SqlZenStore]:
    """Yield a store backed by a fresh disposable MySQL database."""
    assert MYSQL_URL
    database = f"zenml_archive_test_{uuid4().hex[:12]}"
    url = make_url(MYSQL_URL)
    if url.drivername == "mysql":
        url = url.set(drivername="mysql+pymysql")
    admin_url = url.set(database=None)
    admin = create_engine(admin_url)
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {database}"))
        connection.commit()
    store_url = url.set(database=database).render_as_string(
        hide_password=False
    )
    store: SqlZenStore | None = None
    try:
        store = SqlZenStore(
            config=SqlZenStoreConfiguration(url=store_url),
            skip_default_registrations=False,
        )
        yield store
    finally:
        if store is not None:
            store.engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE {database}"))
            connection.commit()
        admin.dispose()


def test_authority_switch_waits_for_writer_and_rechecks_source(
    mysql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A writer that commits first makes the waiting switch fail parity."""
    family = populate_family(mysql_store)
    archive = exporter(mysql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )
    service = authority(mysql_store, tmp_path)
    outcome: dict[str, str] = {}

    with Session(mysql_store.engine) as writer:
        snapshot = writer.exec(
            select(PipelineSnapshotSchema)
            .where(col(PipelineSnapshotSchema.id) == family.snapshot_id)
            .with_for_update()
        ).one()

        def compact() -> None:
            try:
                service.compact(
                    archive_id=archive.id, project_id=family.project_id
                )
                outcome["result"] = "committed"
            except Exception as error:
                outcome["result"] = f"{type(error).__name__}: {error}"

        worker = threading.Thread(target=compact)
        worker.start()
        worker.join(timeout=2)
        assert worker.is_alive(), "the authority switch did not wait"

        snapshot.source_code = 'print("writer won")'
        writer.add(snapshot)
        writer.commit()
        worker.join(timeout=30)

    assert not worker.is_alive(), "the authority switch did not finish"
    assert outcome["result"].startswith("ExecutionArchiveParityError")
    failed = ExecutionArchiveCatalog(mysql_store.engine).require(archive.id)
    assert failed.state == ExecutionArchiveState.FAILED
    assert not failed.requires_restore


def test_locking_fence_sees_authority_committed_after_consistent_read(
    mysql_store: SqlZenStore, tmp_path: Path
) -> None:
    """A locking read sees the marker even after an older consistent read."""
    family = populate_family(mysql_store)
    archive = exporter(mysql_store, tmp_path).export(
        project_id=family.project_id, root_run_id=family.run_id
    )

    with Session(mysql_store.engine) as writer:
        snapshot = writer.get(PipelineSnapshotSchema, family.snapshot_id)
        assert snapshot is not None and snapshot.execution_archive_id is None

        authority(mysql_store, tmp_path).compact(
            archive_id=archive.id, project_id=family.project_id
        )
        marker = writer.exec(
            select(PipelineSnapshotSchema.execution_archive_id)
            .where(col(PipelineSnapshotSchema.id) == family.snapshot_id)
            .with_for_update()
        ).one()

    assert marker == archive.id
