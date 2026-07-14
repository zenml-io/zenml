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
"""Local staging of artifact data for deferred uploads."""

import contextvars
import os
import posixpath
import shutil
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Callable, Dict, List, NamedTuple, Optional
from uuid import UUID, uuid4

from zenml.constants import (
    ENV_ZENML_ARTIFACT_STAGING_MAX_SIZE,
    ENV_ZENML_ARTIFACT_UPLOAD_INTERVAL,
    ENV_ZENML_ARTIFACT_UPLOAD_WORKER_COUNT,
    handle_float_env_var,
    handle_int_env_var,
)
from zenml.enums import ArtifactVersionAvailability
from zenml.logger import get_logger
from zenml.utils import context_utils

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore

logger = get_logger(__name__)


class StagedArtifactUpload(NamedTuple):
    """Staged artifact upload."""

    artifact_version_id: UUID
    staging_uri: str
    target_uri: str


class ArtifactStagingContext(context_utils.BaseContext):
    """Artifact staging context."""

    __context_var__ = contextvars.ContextVar("artifact_staging_context")

    def __init__(
        self,
        staging_dir: str,
        upload_callback: Callable[[StagedArtifactUpload], None],
        max_size: Optional[int] = None,
    ) -> None:
        """Initialize the staging context.

        Args:
            staging_dir: The local directory in which to stage artifact data.
            upload_callback: Callback that is called for each staged artifact
                and is responsible for uploading its data.
            max_size: The maximum total size (in bytes) of staged artifact
                data. Staged data only counts towards this limit until it is
                discarded.
        """
        super().__init__()
        # Resolve symlinks so the paths match the resolved paths that the
        # artifact store validates against.
        self._staging_dir = os.path.realpath(staging_dir)
        self._upload_callback = upload_callback
        self._max_size = max_size
        self._used_bytes = 0
        self._staged_uris: Dict[UUID, str] = {}
        self._staged_sizes: Dict[UUID, int] = {}
        self._lock = threading.Lock()
        self._artifact_store = _build_staging_artifact_store(
            path=self._staging_dir
        )

    @property
    def artifact_store(self) -> "BaseArtifactStore":
        """Artifact store for the staging directory.

        Returns:
            Artifact store for the staging directory.
        """
        return self._artifact_store

    @property
    def has_capacity(self) -> bool:
        """Whether the staging directory has capacity for more artifact data.

        Returns:
            Whether the staging directory has capacity.
        """
        if self._max_size is None:
            return True

        with self._lock:
            return self._used_bytes < self._max_size

    def allocate_staging_uri(self) -> str:
        """Allocate a URI in the staging directory.

        Returns:
            The allocated URI.
        """
        return os.path.join(self._staging_dir, uuid4().hex)

    def submit_upload(
        self,
        artifact_version_id: UUID,
        staging_uri: str,
        target_uri: str,
    ) -> None:
        """Submit a staged artifact for upload.

        Args:
            artifact_version_id: The ID of the staged artifact version.
            staging_uri: The URI at which the artifact data is staged.
            target_uri: The URI to which the artifact data should be uploaded.
        """
        size = _get_directory_size(staging_uri)
        with self._lock:
            self._staged_uris[artifact_version_id] = staging_uri
            self._staged_sizes[artifact_version_id] = size
            self._used_bytes += size

        self._upload_callback(
            StagedArtifactUpload(
                artifact_version_id=artifact_version_id,
                staging_uri=staging_uri,
                target_uri=target_uri,
            )
        )

    def get_staged_uri(self, artifact_version_id: UUID) -> Optional[str]:
        """Get the staging URI for an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version.

        Returns:
            The staging URI, or None if the artifact version is not staged.
        """
        with self._lock:
            return self._staged_uris.get(artifact_version_id)

    def discard(self, artifact_version_id: UUID) -> None:
        """Discard the staged data for an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version.
        """
        with self._lock:
            staging_uri = self._staged_uris.pop(artifact_version_id, None)
            size = self._staged_sizes.pop(artifact_version_id, 0)
            self._used_bytes -= size

        if staging_uri:
            shutil.rmtree(staging_uri, ignore_errors=True)


class StagedArtifactUploader:
    """Uploader for staged artifact data."""

    def __init__(self, artifact_store: "BaseArtifactStore") -> None:
        """Initialize the uploader.

        Args:
            artifact_store: The artifact store to which to upload staged
                artifact data.
        """
        self._artifact_store = artifact_store
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: List["Future[None]"] = []
        self._pending_uploads: List[StagedArtifactUpload] = []
        self._upload_interval = handle_float_env_var(
            ENV_ZENML_ARTIFACT_UPLOAD_INTERVAL, default=0.0
        )
        self._flush_stop = threading.Event()
        self._flush_thread: Optional[threading.Thread] = None
        self._staging_dir = tempfile.mkdtemp(prefix="zenml-artifact-staging-")
        max_size = handle_int_env_var(
            ENV_ZENML_ARTIFACT_STAGING_MAX_SIZE, default=0
        )
        self._staging_context = ArtifactStagingContext(
            staging_dir=self._staging_dir,
            upload_callback=self._submit,
            max_size=max_size or None,
        )

    @property
    def staging_context(self) -> ArtifactStagingContext:
        """Staging context that submits its uploads to this uploader.

        Returns:
            The staging context.
        """
        return self._staging_context

    def wait(self) -> None:
        """Block until all uploads have finished.

        Raises:
            Exception: If any upload failed.
        """  # noqa: DOC502
        while True:
            self._flush()

            with self._lock:
                futures = list(self._futures)

            for future in futures:
                future.result()

            with self._lock:
                if not self._pending_uploads and len(futures) == len(
                    self._futures
                ):
                    return

    def shutdown(self) -> None:
        """Wait for all uploads to finish and release all resources."""
        self._flush_stop.set()
        if self._flush_thread:
            self._flush_thread.join()
        self._flush()

        with self._lock:
            executor = self._executor
            futures = list(self._futures)

        for future in futures:
            try:
                future.result()
            except Exception:
                # The failure was already logged and recorded on the artifact
                # version.
                pass

        if executor:
            executor.shutdown(wait=True)

        shutil.rmtree(self._staging_dir, ignore_errors=True)

    def _submit(self, upload: StagedArtifactUpload) -> None:
        """Submit a staged artifact upload.

        Args:
            upload: The staged artifact upload.
        """
        if self._upload_interval > 0:
            with self._lock:
                self._pending_uploads.append(upload)
                if self._flush_thread is None:
                    ctx = contextvars.copy_context()
                    self._flush_thread = threading.Thread(
                        name="StagedArtifactUploader-Flush-Loop",
                        target=lambda: ctx.run(self._flush_loop),
                        daemon=True,
                    )
                    self._flush_thread.start()
        else:
            with self._lock:
                self._submit_now(upload)

    def _submit_now(self, upload: StagedArtifactUpload) -> None:
        """Submit a staged artifact upload to the upload executor.

        This method must be called while holding the lock.

        Args:
            upload: The staged artifact upload.
        """
        if self._executor is None:
            worker_count = handle_int_env_var(
                ENV_ZENML_ARTIFACT_UPLOAD_WORKER_COUNT, default=4
            )
            self._executor = ThreadPoolExecutor(
                max_workers=worker_count,
                thread_name_prefix="StagedArtifactUploader",
            )

        future = self._executor.submit(self._upload, upload)
        self._futures.append(future)

    def _flush(self) -> None:
        """Submit all pending uploads to the upload executor."""
        with self._lock:
            pending = self._pending_uploads
            self._pending_uploads = []
            for upload in pending:
                self._submit_now(upload)

    def _flush_loop(self) -> None:
        """Flush pending uploads at a fixed interval."""
        while not self._flush_stop.wait(timeout=self._upload_interval):
            self._flush()

    def _upload(self, upload: StagedArtifactUpload) -> None:
        """Upload a staged artifact and update its availability.

        Args:
            upload: The staged artifact upload.

        Raises:
            Exception: If the upload failed.
        """  # noqa: DOC502
        from zenml.client import Client
        from zenml.models import ArtifactVersionUpdate

        try:
            upload_staged_artifact(
                upload=upload, artifact_store=self._artifact_store
            )
        except Exception:
            logger.exception(
                "Failed to upload staged artifact version `%s`.",
                upload.artifact_version_id,
            )
            try:
                Client().zen_store.update_artifact_version(
                    artifact_version_id=upload.artifact_version_id,
                    artifact_version_update=ArtifactVersionUpdate(
                        availability=ArtifactVersionAvailability.UPLOAD_FAILED
                    ),
                )
            except Exception:
                logger.exception(
                    "Failed to update the availability of artifact "
                    "version `%s`.",
                    upload.artifact_version_id,
                )
            raise
        else:
            Client().zen_store.update_artifact_version(
                artifact_version_id=upload.artifact_version_id,
                artifact_version_update=ArtifactVersionUpdate(
                    availability=ArtifactVersionAvailability.AVAILABLE
                ),
            )
            self._staging_context.discard(upload.artifact_version_id)


def _get_directory_size(path: str) -> int:
    """Get the total size of all files in a directory.

    Args:
        path: The directory path.

    Returns:
        The total size in bytes.
    """
    size = 0
    for root, _, files in os.walk(path):
        for file in files:
            size += os.path.getsize(os.path.join(root, file))

    return size


def _build_staging_artifact_store(path: str) -> "BaseArtifactStore":
    """Build a local artifact store for a staging directory.

    Args:
        path: The path of the staging directory.

    Returns:
        The artifact store.
    """
    from zenml.artifact_stores.local_artifact_store import (
        LocalArtifactStore,
        LocalArtifactStoreConfig,
    )
    from zenml.enums import StackComponentType
    from zenml.utils.time_utils import utc_now

    return LocalArtifactStore(
        name="artifact-staging",
        id=uuid4(),
        config=LocalArtifactStoreConfig(path=path),
        flavor="local",
        type=StackComponentType.ARTIFACT_STORE,
        user=None,
        created=utc_now(),
        updated=utc_now(),
    )


def upload_staged_artifact(
    upload: StagedArtifactUpload,
    artifact_store: "BaseArtifactStore",
) -> None:
    """Upload staged artifact data to its target URI.

    Args:
        upload: The staged artifact upload.
        artifact_store: The artifact store to which to upload the data.
    """
    for root, _, files in os.walk(upload.staging_uri):
        relative_dir = os.path.relpath(root, upload.staging_uri)
        target_dir = upload.target_uri
        if relative_dir != ".":
            target_dir = posixpath.join(
                target_dir, *relative_dir.split(os.sep)
            )
        artifact_store.makedirs(target_dir)

        for file in files:
            source_path = os.path.join(root, file)
            target_path = posixpath.join(target_dir, file)
            with (
                open(source_path, "rb") as source,
                artifact_store.open(target_path, "wb") as target,
            ):
                shutil.copyfileobj(source, target, 1024 * 1024)
