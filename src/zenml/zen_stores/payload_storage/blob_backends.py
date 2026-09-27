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
import threading
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, TypeVar

from zenml.zen_stores.payload_storage.config import BlobBackendType

T = TypeVar("T")

if TYPE_CHECKING:
    from fsspec import AbstractFileSystem


class BlobBackend(ABC):
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

    @property
    @abstractmethod
    def location(self) -> str:
        """Where the blobs are stored, such as `s3://bucket/prefix`.

        It never includes credentials, so that they can change.

        Returns:
            The location of the blobs.
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


class FsspecBlobBackend(BlobBackend):
    """Holds payload blobs in object storage through its fsspec filesystem.

    Blobs are stored as `<path>/<sha256>`, such as
    `s3://bucket/prefix/<sha256>`. Each blob takes a single request to write
    or read.

    Every call is cancelled after the timeout, retries included. s3fs, gcsfs
    and adlfs are fsspec async filesystems, whose calls take a `timeout`; on
    their own, a call against a stalled endpoint keeps its thread for minutes
    (s3fs retries five times, gcsfs six).
    """

    def __init__(
        self,
        backend_type: BlobBackendType,
        path: str,
        filesystem_class: Type["AbstractFileSystem"],
        filesystem_options: Dict[str, Any],
        timeout: float,
    ) -> None:
        """Initializes the backend.

        Args:
            backend_type: The backend.
            path: Where the blobs are stored, such as `s3://bucket/prefix`.
            filesystem_class: The fsspec filesystem of the object store.
            filesystem_options: The options the filesystem is created with.
            timeout: The number of seconds after which a call is cancelled.
        """
        self._backend_type = backend_type
        self._location = path.rstrip("/")
        self._filesystem_class = filesystem_class
        self._filesystem_options = filesystem_options
        self._filesystem: Optional["AbstractFileSystem"] = None
        self._filesystem_lock = threading.Lock()
        self._timeout = timeout

    @property
    def location(self) -> str:
        """Where the blobs are stored: the path of the backend.

        Returns:
            The location of the blobs.
        """
        return self._location

    def _get_filesystem(self) -> "AbstractFileSystem":
        """Get the filesystem, which the first call creates.

        gcsfs and adlfs look up credentials when they are created, so the
        store starts even while those are unavailable, and the first call
        fails like any other. Concurrent first calls share one filesystem,
        and with it the connection pool.

        Returns:
            The filesystem.
        """
        filesystem = self._filesystem
        if filesystem is None:
            with self._filesystem_lock:
                if self._filesystem is None:
                    # The instance cache of fsspec would keep it alive for as
                    # long as the process.
                    self._filesystem = self._filesystem_class(
                        skip_instance_cache=True, **self._filesystem_options
                    )
                filesystem = self._filesystem
        return filesystem

    def _call_filesystem(self, function: Callable[[], T]) -> T:
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
            if self._is_permission_error(e):
                raise PermissionError(str(e)) from e
            if self._is_not_found_error(e):
                raise FileNotFoundError(str(e)) from e
            raise

    def _is_permission_error(self, error: Exception) -> bool:
        """Whether a provider error means that access was denied.

        Missing credentials count as denied access: they are a configuration
        error that no retry fixes.

        Args:
            error: The error.

        Returns:
            Whether access was denied.
        """
        if self._backend_type == BlobBackendType.S3:
            from botocore.exceptions import (
                NoCredentialsError,
                PartialCredentialsError,
            )

            return isinstance(
                error, (NoCredentialsError, PartialCredentialsError)
            )
        if self._backend_type == BlobBackendType.GCS:
            from gcsfs.retry import HttpError
            from google.auth.exceptions import DefaultCredentialsError

            return (
                isinstance(error, DefaultCredentialsError)
                or (isinstance(error, HttpError) and error.code in (401, 403))
                or (
                    type(error) is OSError
                    and str(error).startswith("Forbidden")
                )
            )
        if self._backend_type == BlobBackendType.AZURE:
            from azure.core.exceptions import (
                ClientAuthenticationError,
                HttpResponseError,
            )

            return (
                isinstance(error, ClientAuthenticationError)
                or (
                    isinstance(error, HttpResponseError)
                    and error.status_code == 403
                )
                # adlfs without an account or a connection string.
                or (type(error) is ValueError and "account_name" in str(error))
            )
        return False

    def _is_not_found_error(self, error: Exception) -> bool:
        """Whether a provider error means that the object or bucket is missing.

        Args:
            error: The error.

        Returns:
            Whether the object or bucket is missing.
        """
        if self._backend_type == BlobBackendType.AZURE:
            from azure.core.exceptions import ResourceNotFoundError

            return isinstance(error, ResourceNotFoundError)
        return False

    def put(self, sha256: str, data: bytes) -> None:
        """Durably store bytes under their SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.
            data: The bytes to store.
        """
        # Object stores only make an object visible once its upload has
        # completed, so the bytes are written straight to their final key.
        self._call_filesystem(
            lambda: self._get_filesystem().pipe_file(
                f"{self._location}/{sha256}", data, timeout=self._timeout
            )
        )

    def get(self, sha256: str) -> bytes:
        """Load the bytes stored under a SHA-256.

        Args:
            sha256: The hex SHA-256 of the bytes.

        Returns:
            The stored bytes.
        """
        data: bytes = self._call_filesystem(
            lambda: self._get_filesystem().cat_file(
                f"{self._location}/{sha256}", timeout=self._timeout
            )
        )
        return data


def create_blob_backend(
    backend_type: BlobBackendType,
    configuration: Dict[str, Any],
    timeout: float,
    max_concurrent_calls: int,
) -> BlobBackend:
    """Create a payload backend from its configuration.

    Creating a backend never connects to its storage, so a store starts even
    while its storage is unavailable. A missing filesystem library fails
    here, when the store starts.

    Args:
        backend_type: The backend to create.
        configuration: The `path` of the blobs and the options of the fsspec
            filesystem of the backend.
        timeout: The number of seconds after which a call is cancelled.
        max_concurrent_calls: The number of calls the backend receives at once.

    Returns:
        The payload backend.
    """
    import fsspec

    options = dict(configuration)
    path = options.pop("path")
    if backend_type == BlobBackendType.S3:
        # The S3 client keeps 10 connections by default, and the timeout of a
        # call also runs while it waits for one, so calls beyond 10 would
        # time out on healthy storage.
        options["config_kwargs"] = {
            "max_pool_connections": max_concurrent_calls,
            **(options.get("config_kwargs") or {}),
        }
    elif backend_type == BlobBackendType.AZURE:
        # Older adlfs versions access containers anonymously by default.
        options.setdefault("anon", False)
    protocol, _ = fsspec.core.split_protocol(path)
    return FsspecBlobBackend(
        backend_type,
        path,
        filesystem_class=fsspec.get_filesystem_class(protocol),
        filesystem_options=options,
        timeout=timeout,
    )
