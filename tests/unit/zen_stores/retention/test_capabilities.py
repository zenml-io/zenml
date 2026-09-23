# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Execution archive capability discovery tests."""

import inspect as python_inspect
from types import SimpleNamespace
from typing import Any, Dict, Optional
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from zenml.artifact_stores.base_artifact_store import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
)
from zenml.constants import ENV_ZENML_SERVER
from zenml.enums import StackComponentType
from zenml.io import fileio, filesystem_registry
from zenml.io.local_filesystem import LocalFilesystem
from zenml.utils.time_utils import utc_now
from zenml.zen_server import archive_storage as storage_module
from zenml.zen_server.archive_storage import ArtifactStoreArchiveStorage
from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.mark.parametrize("migrate", [False, True])
def test_database_preserves_archive_catalog_on_project_delete(
    retention_store: SqlZenStore,
    migrate: bool,
) -> None:
    """Deleted projects leave archive locations available for cleanup."""
    if migrate:
        migrations = Alembic(retention_store.engine)
        migrations.downgrade("9f2b8c7d6e5a")
        migrations.upgrade("c3f5a9e1d7b2")
    inspector = inspect(retention_store.engine)
    assert Alembic(retention_store.engine).current_revisions() == [
        "c3f5a9e1d7b2"
    ]
    project_fk = next(
        fk
        for fk in inspector.get_foreign_keys("archive_bundle")
        if fk["constrained_columns"] == ["project_id"]
    )
    assert project_fk["options"]["ondelete"] == "SET NULL"
    assert next(
        column
        for column in inspector.get_columns("archive_bundle")
        if column["name"] == "project_id"
    )["nullable"]


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

    archive = ArtifactStoreArchiveStorage.from_uri("s3://archive")

    after = registry.get_filesystem_for_path("s3://ordinary/object")
    assert after is before
    assert archive.artifact_store.config.config_kwargs == {
        "connect_timeout": 10,
        "read_timeout": 60,
        "retries": {"mode": "standard", "total_max_attempts": 3},
    }


def test_objects_can_be_read_and_deleted_after_the_archive_root_changes(
    tmp_path,
) -> None:
    """Reads and cleanup use an object's recorded location after a move."""
    former = ArtifactStoreArchiveStorage.from_uri(str(tmp_path / "former"))
    uri = former.object_uri(uuid4(), uuid4(), uuid4())
    former.write(uri, b"archived")

    current = ArtifactStoreArchiveStorage.from_uri(str(tmp_path / "current"))

    assert current.read(uri, 8) == b"archived"
    assert current.remove(uri) is True
    assert not former.artifact_store.exists(uri)
    assert current.remove(uri) is True
