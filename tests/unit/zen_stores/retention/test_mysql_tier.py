# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Opt-in MySQL round trip and two races using separate database connections."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Event, current_thread

import pytest
from sqlalchemy import update

from zenml.enums import RetentionOutcome
from zenml.exceptions import ExecutionRetentionConflictError
from zenml.zen_stores.retention import transactions
from zenml.zen_stores.schemas import ArchiveBundleSchema

pytestmark = pytest.mark.retention_mysql


def test_expired_restore_cannot_overwrite_replacement(
    mysql_store, tree_factory, archive_one_tree, storage, monkeypatch, rows
):
    """A late fetch loses its claim on both SQLite and the local MySQL tier."""
    store = mysql_store
    ids = tree_factory(store)
    bundle_id = archive_one_tree(store, ids)
    started, release = Event(), Event()
    original = storage.open

    def blocked(path, mode="r"):
        if current_thread().name.startswith("expired-restore"):
            started.set()
            assert release.wait(20)
        return original(path, mode)

    monkeypatch.setattr(storage, "open", blocked)
    with ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="expired-restore"
    ) as pool:
        stale = pool.submit(store.restore_pipeline_run, ids.run)
        try:
            assert started.wait(10)
            with transactions.transaction(store.engine) as session:
                session.execute(
                    update(ArchiveBundleSchema)
                    .where(ArchiveBundleSchema.id == bundle_id)
                    .values(claim_expires_at=datetime(2000, 1, 1))
                )
            replacement = store.restore_pipeline_run(ids.run)
            assert replacement.outcome == RetentionOutcome.SUCCEEDED
            expected = rows(store)
        finally:
            release.set()
        with pytest.raises(ExecutionRetentionConflictError):
            stale.result(timeout=10)
    assert rows(store) == expected
