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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Helpers that drive the archiver in tests, with observable storage."""

from typing import Any, Callable, Optional
from uuid import UUID

from tests.unit.zen_stores.execution_archive.utils import NOW
from zenml.models import ExecutionArchiveObject
from zenml.zen_stores.execution_archive.archiver import ExecutionArchiver
from zenml.zen_stores.execution_archive.models import ArchiveObjectKind
from zenml.zen_stores.execution_archive.storage import (
    BaseExecutionArchiveObjectStore,
)
from zenml.zen_stores.execution_archive.targets import ExecutionArchiveTargets
from zenml.zen_stores.sql_zen_store import SqlZenStore


class FaultyStores(ExecutionArchiveTargets):
    """Wraps the configured target's object store to observe and inject."""

    def __init__(
        self,
        store: SqlZenStore,
        *,
        before_manifest: Optional[Callable[[], None]] = None,
    ) -> None:
        """Wrap the targets of a store.

        Args:
            store: The store.
            before_manifest: Runs once, right before the manifest is written.
        """
        super().__init__(store)
        self._before_manifest = before_manifest
        self.reads = 0

    def object_store(self, target_id: UUID) -> BaseExecutionArchiveObjectStore:
        """Wrap the object store of a target.

        Args:
            target_id: The target.

        Returns:
            The wrapped object store.
        """
        inner = super().object_store(target_id)
        outer = self

        class _Store(BaseExecutionArchiveObjectStore):
            @property
            def target_id(self) -> UUID:
                return inner.target_id

            def put_if_absent(
                self, kind: ArchiveObjectKind, scope_id: UUID, payload: bytes
            ) -> ExecutionArchiveObject:
                if (
                    kind is ArchiveObjectKind.MANIFEST
                    and outer._before_manifest is not None
                ):
                    hook, outer._before_manifest = outer._before_manifest, None
                    hook()
                return inner.put_if_absent(kind, scope_id, payload)

            def get_exact(
                self,
                kind: ArchiveObjectKind,
                scope_id: UUID,
                object_: ExecutionArchiveObject,
            ) -> bytes:
                outer.reads += 1
                return inner.get_exact(kind, scope_id, object_)

        return _Store()


def archiver(
    store: SqlZenStore,
    stores: Optional[ExecutionArchiveTargets] = None,
    **kwargs: Any,
) -> ExecutionArchiver:
    """An archiver writing to the store's configured target at `NOW`.

    Args:
        store: The store.
        stores: Optional wrapped targets to observe or inject faults.
        **kwargs: Further archiver arguments.

    Returns:
        The archiver.
    """
    return ExecutionArchiver(
        store.engine,
        targets=stores or store.execution_archive_targets,
        workspace_id=store.get_deployment_id(),
        writer_version="0.97.0",
        writer_alembic_revision="ed9c52d0a1ff",
        clock=lambda: NOW,
        **kwargs,
    )
