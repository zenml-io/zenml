# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Execution archive capability discovery tests."""

import inspect as python_inspect
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from zenml.artifact_stores.base_artifact_store import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
)
from zenml.config.server_config import ArchiveSettings, ServerConfiguration
from zenml.constants import ENV_ZENML_SERVER
from zenml.enums import AuthScheme, StackComponentType
from zenml.exceptions import IllegalOperationError
from zenml.io import fileio, filesystem_registry
from zenml.io.local_filesystem import LocalFilesystem
from zenml.models import ServerModel
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.retention import storage as storage_module
from zenml.zen_stores.retention.storage import ArchiveStorage
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


def test_archive_startup_database_validation_is_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported databases fail startup outside the storage probe guard."""
    from zenml.zen_server import zen_server_api

    archive = ArchiveSettings(backend="local", uri="/tmp/archive")
    storage = SimpleNamespace(probe=Mock())

    class UnsupportedController:
        archive_storage = storage

        @property
        def archive_settings(self) -> ArchiveSettings:
            raise IllegalOperationError("unsupported database")

    monkeypatch.setattr(
        zen_server_api,
        "server_config",
        lambda: SimpleNamespace(archive=archive),
    )
    monkeypatch.setattr(
        zen_server_api, "retention_controller", UnsupportedController
    )

    with pytest.raises(IllegalOperationError, match="unsupported database"):
        zen_server_api._check_archive_store_on_startup()

    storage.probe.assert_not_called()


def test_archive_startup_storage_failure_is_a_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient archive storage failure does not prevent server startup."""
    from zenml.zen_server import zen_server_api

    archive = ArchiveSettings(backend="local", uri="/tmp/archive")
    storage = SimpleNamespace(probe=Mock(side_effect=OSError("temporary")))
    controller = SimpleNamespace(
        archive_settings=archive,
        archive_storage=storage,
    )
    warning = Mock()
    monkeypatch.setattr(
        zen_server_api,
        "server_config",
        lambda: SimpleNamespace(archive=archive),
    )
    monkeypatch.setattr(
        zen_server_api, "retention_controller", lambda: controller
    )
    monkeypatch.setattr(zen_server_api.logger, "warning", warning)

    zen_server_api._check_archive_store_on_startup()

    storage.probe.assert_called_once_with()
    warning.assert_called_once()


def test_archive_storage_does_not_replace_global_fileio_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal archive construction keeps an ordinary store registered."""
    monkeypatch.delenv(ENV_ZENML_SERVER, raising=False)

    class TestConfig(BaseArtifactStoreConfig):
        SUPPORTED_SCHEMES = {"s3://"}
        config_kwargs: Optional[Dict[str, Any]] = None

    def no_io(self, *args, **kwargs):
        return self.path

    implementation = type(
        "RetentionTestArtifactStore",
        (BaseArtifactStore,),
        {
            name: no_io
            for name, method in python_inspect.getmembers(BaseArtifactStore)
            if getattr(method, "__isabstractmethod__", False)
        },
    )
    flavor = SimpleNamespace(
        name="retention-test",
        implementation_class=implementation,
        config_class=TestConfig,
        service_connector_requirements=None,
    )
    registry = filesystem_registry.FileIORegistry()
    registry.register(LocalFilesystem)
    monkeypatch.setattr(
        filesystem_registry, "default_filesystem_registry", registry
    )
    monkeypatch.setattr(fileio, "default_filesystem_registry", registry)
    monkeypatch.setattr(storage_module, "_flavor_for", lambda _: flavor)
    now = utc_now()
    implementation(
        name="ordinary",
        id=uuid4(),
        config=TestConfig(path="s3://ordinary"),
        flavor=flavor.name,
        type=StackComponentType.ARTIFACT_STORE,
        user=None,
        created=now,
        updated=now,
    )
    before = registry.get_filesystem_for_path("s3://ordinary/object")

    archive = ArchiveStorage.from_uri("s3://archive")

    after = registry.get_filesystem_for_path("s3://ordinary/object")
    assert after is before
    assert archive.artifact_store.config.config_kwargs == {
        "connect_timeout": 10,
        "read_timeout": 60,
        "retries": {"mode": "standard", "total_max_attempts": 3},
    }


def test_objects_stay_readable_after_the_archive_root_changes(
    tmp_path,
) -> None:
    """A recorded URI under a former root is read where it was written."""
    former = ArchiveStorage.from_uri(str(tmp_path / "former"))
    uri = former.object_uri(uuid4(), uuid4(), uuid4())
    former.write(uri, b"archived")

    current = ArchiveStorage.from_uri(str(tmp_path / "current"))

    assert current.read(uri, 8) == b"archived"
