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
"""Backends that hold payload blobs outside the database."""

import asyncio
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Protocol,
    TypeVar,
    cast,
)
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.payload_storage.config import PayloadBackendType

T = TypeVar("T")

if TYPE_CHECKING:
    from fsspec import AbstractFileSystem

    from zenml.artifact_stores import BaseArtifactStoreFlavor


class PayloadBackend(ABC):
    """Holds payload bytes outside the database, addressed by their SHA-256.

    Blobs are never overwritten with different bytes or deleted, so a backend
    only needs to store and load them. A denied access raises
    `PermissionError` and a missing object or bucket `FileNotFoundError`: the
    payload store fails those at once, and treats any other error as an
    unavailable backend that a retry may find again. Every call returns or
    raises within the timeout the backend was created with, since a stuck
    call keeps one of the threads that the payload store shares between
    requests.
    """

    @abstractmethod
    def put(self, sha256: str, data: bytes) -> None:
        """Durably store bytes under their SHA-256.

        Concurrent writers of the same content store identical bytes, so
        storing bytes that are already stored must succeed.

        Args:
            sha256: The hex SHA-256 of the bytes.
            data: The bytes to store.
        """

    @abstractmethod
    def get(self, sha256: str) -> bytes:
        """Load the bytes stored under a SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.

        Returns:
            The stored bytes.
        """


class ObjectStoreArtifactStore(Protocol):
    """An artifact store whose files live in an fsspec filesystem."""

    @property
    def path(self) -> str:
        """The root path of the artifact store."""

    @property
    def filesystem(self) -> "AbstractFileSystem":
        """The filesystem holding the files of the artifact store."""


def _is_denied(backend_type: PayloadBackendType, error: Exception) -> bool:
    """Whether a provider error means that access was denied.

    Args:
        backend_type: The backend that raised the error.
        error: The error.

    Returns:
        Whether access was denied.
    """
    if backend_type == PayloadBackendType.GCS:
        from gcsfs.retry import HttpError

        return (isinstance(error, HttpError) and error.code in (401, 403)) or (
            type(error) is OSError and str(error).startswith("Forbidden")
        )
    if backend_type == PayloadBackendType.AZURE:
        from azure.core.exceptions import (
            ClientAuthenticationError,
            HttpResponseError,
        )

        return isinstance(error, ClientAuthenticationError) or (
            isinstance(error, HttpResponseError) and error.status_code == 403
        )
    return False


def _is_missing(backend_type: PayloadBackendType, error: Exception) -> bool:
    """Whether a provider error means that the object or bucket is missing.

    Args:
        backend_type: The backend that raised the error.
        error: The error.

    Returns:
        Whether the object or bucket is missing.
    """
    if backend_type == PayloadBackendType.AZURE:
        from azure.core.exceptions import ResourceNotFoundError

        return isinstance(error, ResourceNotFoundError)
    return False


class ArtifactStorePayloadBackend(PayloadBackend):
    """Holds payload blobs in object storage through a ZenML artifact store.

    Blobs are stored as `<path>/<sha256>`, where `path` is the path of the
    artifact store, such as `s3://bucket/prefix`. Each blob takes a single
    request to write or read, with the credentials of the artifact store.

    Every call is cancelled after the timeout, retries included. s3fs, gcsfs
    and adlfs are fsspec async filesystems, whose calls take a `timeout`; on
    their own, a call against a stalled endpoint keeps its thread for minutes
    (s3fs retries five times, gcsfs six).
    """

    def __init__(
        self,
        backend_type: PayloadBackendType,
        artifact_store: ObjectStoreArtifactStore,
        timeout: float,
    ) -> None:
        """Initializes the backend.

        Args:
            backend_type: The backend.
            artifact_store: The artifact store holding the blobs.
            timeout: The number of seconds after which a call is cancelled.
        """
        self._backend_type = backend_type
        self._artifact_store = artifact_store
        self._root = artifact_store.path.rstrip("/")
        self._timeout = timeout

    def _call(self, function: Callable[[], T]) -> T:
        """Call the filesystem, with denied and missing errors translated.

        s3fs raises `PermissionError` and `FileNotFoundError` itself. gcsfs
        reports a 403 as a plain `OSError` and a 401 as its own `HttpError`,
        and adlfs lets Azure's exceptions through.

        Args:
            function: The filesystem call.

        Returns:
            The result of the call.

        Raises:
            PermissionError: If access to the object was denied.
            FileNotFoundError: If the object or its bucket is missing.
            TimeoutError: If the call did not return in time.
            Exception: Any other error of the call.
        """
        try:
            return function()
        except Exception as e:
            # fsspec's timeout error subclasses `asyncio.TimeoutError` and
            # has no message.
            if isinstance(e, asyncio.TimeoutError):
                raise TimeoutError(
                    f"The call did not return within {self._timeout} seconds."
                ) from e
            if _is_denied(self._backend_type, e):
                raise PermissionError(str(e)) from e
            if _is_missing(self._backend_type, e):
                raise FileNotFoundError(str(e)) from e
            raise

    def put(self, sha256: str, data: bytes) -> None:
        """Durably store bytes under their SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.
            data: The bytes to store.
        """
        # Object stores only make an object visible once its upload has
        # completed, so the bytes are written straight to their final key.
        self._call(
            lambda: self._artifact_store.filesystem.pipe_file(
                f"{self._root}/{sha256}", data, timeout=self._timeout
            )
        )

    def get(self, sha256: str) -> bytes:
        """Load the bytes stored under a SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.

        Returns:
            The stored bytes.
        """
        data: bytes = self._call(
            lambda: self._artifact_store.filesystem.cat_file(
                f"{self._root}/{sha256}", timeout=self._timeout
            )
        )
        return data


def _get_artifact_store_flavor(
    backend_type: PayloadBackendType,
) -> "BaseArtifactStoreFlavor":
    """Get the artifact store flavor that implements a payload backend.

    Args:
        backend_type: The payload backend.

    Returns:
        The artifact store flavor.

    Raises:
        ValueError: If no artifact store flavor implements the backend.
    """
    if backend_type == PayloadBackendType.S3:
        from zenml.integrations.s3.flavors import S3ArtifactStoreFlavor

        return S3ArtifactStoreFlavor()
    if backend_type == PayloadBackendType.GCS:
        from zenml.integrations.gcp.flavors import GCPArtifactStoreFlavor

        return GCPArtifactStoreFlavor()
    if backend_type == PayloadBackendType.AZURE:
        from zenml.integrations.azure.flavors import AzureArtifactStoreFlavor

        return AzureArtifactStoreFlavor()
    raise ValueError(
        f"No artifact store implements the `{backend_type}` payload backend."
    )


def create_payload_backend(
    backend_type: PayloadBackendType,
    configuration: Dict[str, Any],
    timeout: float,
) -> PayloadBackend:
    """Create a payload backend from its configuration.

    Creating a backend never connects to its storage, so a store starts even
    while its storage is unavailable.

    Args:
        backend_type: The backend to create.
        configuration: The configuration of the backend.
        timeout: The number of seconds after which a call is cancelled.

    Returns:
        The payload backend.
    """
    flavor = _get_artifact_store_flavor(backend_type)
    now = utc_now()
    artifact_store = flavor.implementation_class(
        name=f"payload-storage-{backend_type.value}",
        id=uuid4(),
        config=flavor.config_class(**configuration),
        flavor=flavor.name,
        type=StackComponentType.ARTIFACT_STORE,
        user=None,
        created=now,
        updated=now,
        register_filesystem=False,
    )
    # Every object store flavor above exposes its filesystem. It is created
    # on first use, so that a store starts while its storage is unavailable.
    return ArtifactStorePayloadBackend(
        backend_type,
        cast(ObjectStoreArtifactStore, artifact_store),
        timeout=timeout,
    )
