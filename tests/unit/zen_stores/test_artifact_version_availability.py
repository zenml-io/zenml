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
"""Unit tests for artifact version availability transitions."""

from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

import pytest

from zenml.enums import (
    ArtifactSaveType,
    ArtifactType,
    ArtifactVersionAvailability,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    ArtifactVersionRequest,
    ArtifactVersionUpdate,
    ProjectFilter,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """Create a fresh SQLite-backed SqlZenStore for tests."""
    db_dir = tmp_path / "zenml-cfg"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
    db_path = db_dir / "test.db"
    config = SqlZenStoreConfiguration(url=f"sqlite:///{db_path}")
    store = SqlZenStore(config=config, skip_default_registrations=False)
    yield store


def _create_artifact_version(
    store: SqlZenStore, availability: ArtifactVersionAvailability
) -> UUID:
    project_id = (
        store.list_projects(project_filter_model=ProjectFilter()).items[0].id
    )
    return store.create_artifact_version(
        ArtifactVersionRequest(
            artifact_name=f"artifact-{uuid4()}",
            version=1,
            type=ArtifactType.DATA,
            uri=f"s3://bucket/{uuid4()}",
            materializer="module.materializer_class",
            data_type="module.data_type_class",
            project=project_id,
            save_type=ArtifactSaveType.STEP_OUTPUT,
            availability=availability,
        )
    ).id


def test_availability_updates_from_pending(sql_store: SqlZenStore):
    """Pending artifact versions can transition to available or failed."""
    pending_id = _create_artifact_version(
        sql_store, ArtifactVersionAvailability.PENDING
    )
    updated = sql_store.update_artifact_version(
        artifact_version_id=pending_id,
        artifact_version_update=ArtifactVersionUpdate(
            availability=ArtifactVersionAvailability.AVAILABLE
        ),
    )
    assert updated.availability == ArtifactVersionAvailability.AVAILABLE

    failed_id = _create_artifact_version(
        sql_store, ArtifactVersionAvailability.PENDING
    )
    updated = sql_store.update_artifact_version(
        artifact_version_id=failed_id,
        artifact_version_update=ArtifactVersionUpdate(
            availability=ArtifactVersionAvailability.UPLOAD_FAILED
        ),
    )
    assert updated.availability == ArtifactVersionAvailability.UPLOAD_FAILED


def test_availability_updates_from_non_pending(sql_store: SqlZenStore):
    """Non-pending artifact versions can only transition to deleted."""
    available_id = _create_artifact_version(
        sql_store, ArtifactVersionAvailability.AVAILABLE
    )
    with pytest.raises(IllegalOperationError):
        sql_store.update_artifact_version(
            artifact_version_id=available_id,
            artifact_version_update=ArtifactVersionUpdate(
                availability=ArtifactVersionAvailability.PENDING
            ),
        )

    updated = sql_store.update_artifact_version(
        artifact_version_id=available_id,
        artifact_version_update=ArtifactVersionUpdate(
            availability=ArtifactVersionAvailability.DELETED
        ),
    )
    assert updated.availability == ArtifactVersionAvailability.DELETED


def test_availability_updates_for_unmaterialized(sql_store: SqlZenStore):
    """Unmaterialized artifact versions can not transition at all."""
    unmaterialized_id = _create_artifact_version(
        sql_store, ArtifactVersionAvailability.UNMATERIALIZED
    )
    with pytest.raises(IllegalOperationError):
        sql_store.update_artifact_version(
            artifact_version_id=unmaterialized_id,
            artifact_version_update=ArtifactVersionUpdate(
                availability=ArtifactVersionAvailability.DELETED
            ),
        )
