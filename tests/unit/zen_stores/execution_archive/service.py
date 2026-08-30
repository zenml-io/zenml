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
"""Small test helpers for execution archive services."""

from pathlib import Path
from typing import Callable, Optional
from uuid import UUID

from tests.unit.zen_stores.execution_archive.utils import NOW
from zenml.config.server_config import ServerConfiguration
from zenml.models import ExecutionArchiveObject
from zenml.zen_stores.execution_archive.archiver import (
    ExecutionArchiveExporter,
)
from zenml.zen_stores.execution_archive.storage import (
    ExecutionArchiveStorage,
    build_execution_archive_storage,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


class CallbackStorage(ExecutionArchiveStorage):
    """Delegate storage while invoking a callback after the first write."""

    def __init__(
        self,
        inner: ExecutionArchiveStorage,
        callback: Callable[[], None],
    ) -> None:
        """Initialize the wrapper.

        Args:
            inner: Real local storage.
            callback: Mutation to run once after writing.
        """
        self._inner = inner
        self._callback: Optional[Callable[[], None]] = callback

    @property
    def target_digest(self) -> str:
        """Return the delegated target digest."""
        return self._inner.target_digest

    def object_key(
        self, *, project_id: UUID, archive_id: UUID, claim_token: int
    ) -> str:
        """Return the delegated object key.

        Args:
            project_id: Project owning the archive.
            archive_id: Archive generation ID.
            claim_token: Fencing token of the write attempt.

        Returns:
            Storage key for the archive object.
        """
        return self._inner.object_key(
            project_id=project_id,
            archive_id=archive_id,
            claim_token=claim_token,
        )

    def write_verified(
        self, key: str, payload: bytes, *, decoded_bytes: int
    ) -> ExecutionArchiveObject:
        """Write through and invoke the callback once.

        Args:
            key: Storage key.
            payload: Encoded archive bytes.
            decoded_bytes: Expected decoded size.

        Returns:
            Verified object metadata.
        """
        object_ = self._inner.write_verified(
            key, payload, decoded_bytes=decoded_bytes
        )
        if self._callback is not None:
            callback, self._callback = self._callback, None
            callback()
        return object_

    def read_verified(
        self, key: str, object_: ExecutionArchiveObject
    ) -> bytes:
        """Read through the delegate.

        Args:
            key: Storage key.
            object_: Expected object metadata.

        Returns:
            Verified encoded bytes.
        """
        return self._inner.read_verified(key, object_)

    def delete(self, key: str) -> None:
        """Delete through the delegate.

        Args:
            key: Storage key to delete.
        """
        self._inner.delete(key)

    def delete_other_attempts(self, committed_key: str) -> None:
        """Delete superseded attempts through the delegate.

        Args:
            committed_key: Verified object key that must remain available.
        """
        self._inner.delete_other_attempts(committed_key)


def local_storage(store: SqlZenStore, root: Path) -> ExecutionArchiveStorage:
    """Build local archive storage for a test store.

    Args:
        store: SQL store whose deployment namespace is used.
        root: Local artifact-store root.

    Returns:
        Configured local archive storage.
    """
    return build_execution_archive_storage(
        ServerConfiguration(
            execution_archive_flavor="local",
            execution_archive_configuration={"path": str(root)},
            execution_archive_path_prefix="execution-archive",
        ),
        workspace_id=store.get_deployment_id(),
    )


def exporter(
    store: SqlZenStore,
    root: Path,
    *,
    storage: Optional[ExecutionArchiveStorage] = None,
    owner: str = "test-worker",
    lease_seconds: float = 600,
) -> ExecutionArchiveExporter:
    """Build a deterministic exporter backed by local storage.

    Args:
        store: SQL store.
        root: Local artifact-store root.
        storage: Optional observable storage wrapper.
        owner: Worker identity.
        lease_seconds: Fenced lease duration.

    Returns:
        Configured exporter.
    """
    return ExecutionArchiveExporter(
        store=store,
        storage=storage or local_storage(store, root),
        clock=lambda: NOW,
        owner=owner,
        lease_seconds=lease_seconds,
    )
