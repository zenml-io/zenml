# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Execution archive capability discovery tests."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from zenml.config.server_config import ArchiveSettings, ServerConfiguration
from zenml.enums import AuthScheme
from zenml.models import ServerModel
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.sql_zen_store import SqlZenStore


def test_server_model_archive_capability_defaults_to_false() -> None:
    """Older store implementations do not advertise archive creation."""
    model = ServerModel(version="test", auth_scheme=AuthScheme.NO_AUTH)

    assert model.execution_archiving_enabled is False
    assert model.model_dump()["execution_archiving_enabled"] is False


def test_fresh_database_has_sweep_index(
    retention_store: SqlZenStore,
) -> None:
    """Fresh create-all databases have the same index as upgraded databases."""
    indexes = {
        index["name"]: index["column_names"]
        for index in inspect(retention_store.engine).get_indexes(
            "pipeline_run"
        )
    }

    assert Alembic(retention_store.engine).current_revisions() == [
        "c3f5a9e1d7b2"
    ]
    assert indexes["ix_pipeline_run_end_time_id"] == ["end_time", "id"]


@pytest.mark.parametrize(
    ("database_url", "archive_settings", "expected"),
    [
        (
            "sqlite:///:memory:",
            ArchiveSettings(backend="local", uri="/tmp/archive"),
            False,
        ),
        ("mysql://localhost", ArchiveSettings(), False),
        (
            "mysql://localhost",
            ArchiveSettings(
                backend="local", uri="/tmp/archive", enabled=False
            ),
            False,
        ),
        (
            "mysql://localhost",
            ArchiveSettings(
                backend="local",
                uri="/tmp/archive",
                schedule_enabled=False,
            ),
            True,
        ),
    ],
)
def test_store_info_reports_manual_archive_capability(
    database_url: str,
    archive_settings: ArchiveSettings,
    expected: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only enabled MySQL stores advertise manual archive creation."""
    base_info = ServerModel(version="test", auth_scheme=AuthScheme.NO_AUTH)
    server_settings = SimpleNamespace(
        server_id=uuid4(),
        server_name="test",
        active=True,
        last_user_activity=None,
        enable_analytics=False,
    )
    store = object.__new__(SqlZenStore)
    object.__setattr__(store, "config", SimpleNamespace(url=database_url))
    monkeypatch.setattr(
        BaseZenStore, "get_store_info", lambda _store: base_info
    )
    monkeypatch.setattr(
        SqlZenStore,
        "get_server_settings",
        lambda _store, hydrate: server_settings,
    )
    monkeypatch.setattr(
        ServerConfiguration,
        "get_server_config",
        classmethod(lambda _cls: SimpleNamespace(archive=archive_settings)),
    )

    info = store.get_store_info()

    assert info.execution_archiving_enabled is expected
