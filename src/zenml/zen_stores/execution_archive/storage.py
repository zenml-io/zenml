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
"""Immutable, content-addressed object storage over any artifact store."""

import io
import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from zenml.exceptions import ArchiveUnavailableError
from zenml.logger import get_logger
from zenml.models import ExecutionArchiveObject
from zenml.zen_stores.execution_archive.codec import (
    decompress,
    sha256_digest,
    verify_sha256,
)
from zenml.zen_stores.execution_archive.models import (
    ArchiveObjectKind,
    ExecutionArchiveManifest,
)
from zenml.zen_stores.execution_archive.payload import (
    ExecutionPayload,
    SnapshotPayload,
)

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore

logger = get_logger(__name__)


class BaseExecutionArchiveObjectStore(ABC):
    """Storage of one archive target."""

    @property
    @abstractmethod
    def target_id(self) -> UUID:
        """The storage target this store writes to."""

    @abstractmethod
    def put_if_absent(
        self, kind: ArchiveObjectKind, scope_id: UUID, payload: bytes
    ) -> ExecutionArchiveObject:
        """Store bytes under their digest unless they are already stored.

        Args:
            kind: The kind of object.
            scope_id: The project the object belongs to.
            payload: The exact bytes.

        Returns:
            The verified object reference.
        """

    @abstractmethod
    def get_exact(
        self,
        kind: ArchiveObjectKind,
        scope_id: UUID,
        object_: ExecutionArchiveObject,
    ) -> bytes:
        """Read bytes and verify them against their reference.

        Args:
            kind: The kind of object.
            scope_id: The project the object belongs to.
            object_: The object reference.

        Returns:
            The verified bytes.
        """

    def get_decompressed(
        self,
        kind: ArchiveObjectKind,
        scope_id: UUID,
        object_: ExecutionArchiveObject,
    ) -> bytes:
        """Read, verify and decompress a compressed object.

        Args:
            kind: The kind of object.
            scope_id: The scope the object was written under.
            object_: The object reference.

        Returns:
            The decompressed bytes.
        """
        return decompress(self.get_exact(kind, scope_id, object_))

    def read_manifest(
        self, scope_id: UUID, object_: ExecutionArchiveObject
    ) -> ExecutionArchiveManifest:
        """Read and validate a manifest.

        Args:
            scope_id: The project of the archive.
            object_: The manifest reference.

        Returns:
            The manifest.
        """
        return ExecutionArchiveManifest.model_validate_json(
            self.get_exact(ArchiveObjectKind.MANIFEST, scope_id, object_)
        )

    def read_execution(
        self, scope_id: UUID, object_: ExecutionArchiveObject
    ) -> ExecutionPayload:
        """Read, decompress and validate an execution payload.

        Args:
            scope_id: The project of the archive.
            object_: The payload reference.

        Returns:
            The execution payload.
        """
        return ExecutionPayload.model_validate_json(
            self.get_decompressed(
                ArchiveObjectKind.EXECUTION, scope_id, object_
            )
        )

    def read_snapshots(
        self, scope_id: UUID, object_: ExecutionArchiveObject
    ) -> SnapshotPayload:
        """Read, decompress and validate a snapshot payload.

        Args:
            scope_id: The project of the archive.
            object_: The payload reference.

        Returns:
            The snapshot payload.
        """
        return SnapshotPayload.model_validate_json(
            self.get_decompressed(
                ArchiveObjectKind.SNAPSHOT, scope_id, object_
            )
        )


class ArtifactStoreExecutionArchiveObjectStore(
    BaseExecutionArchiveObjectStore
):
    """Archive storage on top of the common artifact store contract.

    S3, GCS, Azure, local, S3-compatible and custom artifact stores share
    this one implementation. Keys contain the payload digest, so concurrent
    writers of the same key always write the same bytes and no write ever
    needs to be conditional.
    """

    def __init__(
        self,
        artifact_store: "BaseArtifactStore",
        *,
        target_id: UUID,
        path_prefix: str,
        workspace_id: UUID,
    ) -> None:
        """Initialize the store.

        Args:
            artifact_store: The artifact store instance.
            target_id: The storage target the instance belongs to.
            path_prefix: The directory below the artifact store path that
                holds every archive object.
            workspace_id: The workspace whose archives are stored; part of
                every key so one target can serve several workspaces.
        """
        self._artifact_store = artifact_store
        self._target_id = target_id
        self._path_prefix = path_prefix
        self._workspace_id = workspace_id

    @property
    def target_id(self) -> UUID:
        """The storage target this store writes to.

        Returns:
            The target ID.
        """
        return self._target_id

    def put_if_absent(
        self, kind: ArchiveObjectKind, scope_id: UUID, payload: bytes
    ) -> ExecutionArchiveObject:
        """Store bytes under their digest unless they are already stored.

        New objects are written to a temporary path and renamed into place.
        Whether the object was just written or already there, it is read
        back and verified before its reference is returned, so an object
        that was overwritten or corrupted in the store never becomes
        authoritative.

        Args:
            kind: The kind of object.
            scope_id: The project the object belongs to.
            payload: The exact bytes.

        Returns:
            The verified object reference.
        """
        object_ = ExecutionArchiveObject(
            sha256=sha256_digest(payload), stored_bytes=len(payload)
        )
        path = self._path(kind, scope_id, object_)
        if not self._artifact_store.exists(path):
            self._write(path, payload)
        self.get_exact(kind, scope_id, object_)
        return object_

    def _write(self, path: str, payload: bytes) -> None:
        parent = os.path.dirname(path)
        self._artifact_store.makedirs(parent)
        temporary_path = os.path.join(
            parent, f".{os.path.basename(path)}.{uuid4().hex}.tmp"
        )
        try:
            with self._artifact_store.open(temporary_path, "wb") as stream:
                stream.write(payload)
                _fsync(stream)
            try:
                self._artifact_store.rename(
                    temporary_path, path, overwrite=False
                )
            except FileExistsError:
                # Another writer stored the same bytes first; both wrote the
                # same content, so the loser's copy is simply discarded.
                self._remove(temporary_path)
        except Exception:
            self._remove(temporary_path)
            raise

    def get_exact(
        self,
        kind: ArchiveObjectKind,
        scope_id: UUID,
        object_: ExecutionArchiveObject,
    ) -> bytes:
        """Read bytes and verify them against their reference.

        Args:
            kind: The kind of object.
            scope_id: The project the object belongs to.
            object_: The object reference.

        Returns:
            The verified bytes.

        Raises:
            ArchiveUnavailableError: If the object cannot be read or its
                digest or size differ from the reference.
        """
        path = self._path(kind, scope_id, object_)
        try:
            with self._artifact_store.open(path, "rb") as stream:
                payload = cast(bytes, stream.read())
        except Exception as e:
            raise ArchiveUnavailableError(
                f"Archive object {object_.sha256} of storage target "
                f"{self._target_id} cannot be read: {e}"
            ) from e
        verify_sha256(payload, object_.sha256)
        if len(payload) != object_.stored_bytes:
            raise ArchiveUnavailableError(
                f"Archive object {object_.sha256} has {len(payload)} bytes "
                f"instead of the recorded {object_.stored_bytes}."
            )
        return payload

    def _path(
        self,
        kind: ArchiveObjectKind,
        scope_id: UUID,
        object_: ExecutionArchiveObject,
    ) -> str:
        return os.path.join(
            self._artifact_store.path,
            self._path_prefix,
            "workspaces",
            str(self._workspace_id),
            "projects",
            str(scope_id),
            kind.value,
            object_.sha256[:2],
            f"{object_.sha256}.{kind.extension}",
        )

    def _remove(self, path: str) -> None:
        try:
            if self._artifact_store.exists(path):
                self._artifact_store.remove(path)
        except Exception as e:
            logger.warning(f"Could not remove archive object {path}: {e}")


def _fsync(stream: object) -> None:
    """Flush a stream to durable storage where the store supports it.

    Args:
        stream: The open write stream.
    """
    try:
        os.fsync(stream.fileno())  # type: ignore[attr-defined]
    except (AttributeError, OSError, io.UnsupportedOperation):
        pass
