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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Protocol, cast
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.payload_storage.config import PayloadBackendType

if TYPE_CHECKING:
    from fsspec import AbstractFileSystem

    from zenml.artifact_stores import BaseArtifactStoreFlavor


class PayloadBackend(ABC):
    """Holds payload bytes outside the database, addressed by their SHA-256.

    Blobs are never overwritten with different bytes or deleted, so a backend
    only needs to store and load them.
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


class ArtifactStorePayloadBackend(PayloadBackend):
    """Holds payload blobs in object storage through a ZenML artifact store.

    Blobs are stored as `<path>/<sha256>`, where `path` is the path of the
    artifact store, such as `s3://bucket/prefix`. Each blob takes a single
    request to write or read, with the credentials of the artifact store.
    """

    def __init__(self, artifact_store: ObjectStoreArtifactStore) -> None:
        """Initializes the backend.

        Args:
            artifact_store: The artifact store holding the blobs.
        """
        self._artifact_store = artifact_store
        self._root = artifact_store.path.rstrip("/")

    def put(self, sha256: str, data: bytes) -> None:
        """Durably store bytes under their SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.
            data: The bytes to store.
        """
        # Object stores only make an object visible once its upload has
        # completed, so the bytes are written straight to their final key.
        self._artifact_store.filesystem.pipe_file(
            f"{self._root}/{sha256}", data
        )

    def get(self, sha256: str) -> bytes:
        """Load the bytes stored under a SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.

        Returns:
            The stored bytes.
        """
        data: bytes = self._artifact_store.filesystem.cat_file(
            f"{self._root}/{sha256}"
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
        timeout: The number of seconds a request waits for the backend.

    Returns:
        The payload backend.
    """
    if backend_type == PayloadBackendType.S3:
        # A request stops waiting after the timeout, but its call keeps a
        # backend thread until the client gives up. With the client defaults,
        # one read against a stalled S3 took 173 s (s3fs retries five times on
        # top of the attempts of botocore), so the threads stayed busy and
        # later requests queued. These bound each call to about twice the
        # timeout, unless the configuration sets them itself.
        configuration = {
            "retries": 1,
            **configuration,
            "config_kwargs": {
                "connect_timeout": timeout,
                "read_timeout": timeout,
                "retries": {"total_max_attempts": 2},
                **(configuration.get("config_kwargs") or {}),
            },
        }
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
        cast(ObjectStoreArtifactStore, artifact_store)
    )
