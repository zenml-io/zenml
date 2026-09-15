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
"""Fixtures shared by the log store tests."""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Iterator, Optional, Tuple
from uuid import UUID, uuid4

import pytest

from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
)
from zenml.enums import StackComponentType
from zenml.models import LogsResponse, LogsResponseBody


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> Iterator[Tuple[SimpleNamespace, SimpleNamespace]]:
    """Override the global auto_environment fixture with a lightweight stub.

    Reading log entries never goes through a ZenML store, so these tests do not
    need a provisioned test environment.

    Yields:
        The active environment and a connected client stub.
    """
    yield SimpleNamespace(), SimpleNamespace()


@pytest.fixture
def artifact_store(tmp_path) -> LocalArtifactStore:
    """A local artifact store rooted in the test's temporary directory."""
    return LocalArtifactStore(
        name="test",
        id=uuid4(),
        config=LocalArtifactStoreConfig(path=str(tmp_path)),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )


@pytest.fixture
def logs_model_factory():
    """Build a logs response model without going through the store."""

    def _build(
        uri: Optional[str] = None,
        artifact_store_id: Optional[UUID] = None,
        log_store_id: Optional[UUID] = None,
        created: Optional[datetime] = None,
    ) -> LogsResponse:
        return LogsResponse(
            id=uuid4(),
            body=LogsResponseBody(
                created=created or datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated=created or datetime(2026, 1, 1, tzinfo=timezone.utc),
                project_id=uuid4(),
                user_id=uuid4(),
                source="step",
                uri=uri,
                artifact_store_id=artifact_store_id,
                log_store_id=log_store_id,
            ),
        )

    return _build
