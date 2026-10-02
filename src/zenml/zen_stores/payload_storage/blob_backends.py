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
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from zenml.zen_stores.payload_storage.config import BlobBackendType

T = TypeVar("T")

if TYPE_CHECKING:
    from fsspec.asyn import AsyncFileSystem

    Calls = List[Callable[[], Awaitable[T]]]


class BlobBackend(ABC):
    """Holds payload bytes outside the database, addressed by their SHA-256.

    Blobs are never overwritten with different bytes or deleted, so a backend
    only needs to store and load them, many at once. A denied access raises
    `PermissionError` and a missing object or bucket `FileNotFoundError`: the
    payload store fails those at once, and treats any other error as an
    unavailable backend that a retry may find again. Every call returns or
    raises within the timeout it is given, since it holds a server thread
    while it runs.
    """

    @property
    @abstractmethod
    def location(self) -> str:
        """Where the blobs are stored, such as `s3://bucket/prefix`.

        It includes the endpoint or account that selects the physical store
        when one is configured, and never credentials, so that they can
        change.

        Returns:
            The location of the blobs.
        """

    @abstractmethod
    def put_many(
        self, data_by_sha256: Mapping[str, bytes], timeout: float
    ) -> None:
        """Durably store bytes under their SHA-256.

        Concurrent writers of the same content store identical bytes, so
        storing bytes that are already stored must succeed.

        Args:
            data_by_sha256: The bytes to store by their hex SHA-256.
            timeout: The seconds after which the call raises `TimeoutError`.
        """

    @abstractmethod
    def get_many(
        self, sha256s: Sequence[str], timeout: float
    ) -> Dict[str, bytes]:
        """Load the bytes stored under SHA-256s.

        Args:
            sha256s: The hex SHA-256s of the bytes.
            timeout: The seconds after which the call raises `TimeoutError`.

        Returns:
            The stored bytes by SHA-256.
        """


class FsspecBlobBackend(BlobBackend):
    """Holds payload blobs in object storage through its fsspec filesystem.

    Blobs are stored as `<path>/<sha256>`, such as
    `s3://bucket/prefix/<sha256>`. Each blob takes a single request to write
    or read. A call runs the requests for its blobs concurrently on the event
    loop of fsspec, whose s3fs, gcsfs and adlfs filesystems are all async,
    rather than through their own batch methods: those differ per provider
    (adlfs reads one file at a time) and leave requests running when they
    time out. On their own, requests against a stalled endpoint keep going
    for minutes (s3fs retries five times, gcsfs six).
    """

    def __init__(
        self,
        backend_type: BlobBackendType,
        path: str,
        location: str,
        filesystem_class: Type["AsyncFileSystem"],
        filesystem_options: Dict[str, Any],
        max_concurrent_calls: int,
    ) -> None:
        """Initializes the backend.

        Args:
            backend_type: The backend.
            path: Where the blobs are stored, such as `s3://bucket/prefix`.
            location: The path, with the endpoint or account that selects the
                physical store when one is configured.
            filesystem_class: The fsspec filesystem of the object store.
            filesystem_options: The options the filesystem is created with.
            max_concurrent_calls: The number of requests one call sends to
                the object store at once.
        """
        self._backend_type = backend_type
        self._path = path.rstrip("/")
        self._location = location
        self._filesystem_class = filesystem_class
        self._filesystem_options = filesystem_options
        self._filesystem: Optional["AsyncFileSystem"] = None
        self._filesystem_creation: Optional[Future["AsyncFileSystem"]] = None
        self._filesystem_lock = threading.Lock()
        self._max_concurrent_calls = max_concurrent_calls

    @property
    def location(self) -> str:
        """Where the blobs are stored.

        Returns:
            The location of the blobs.
        """
        return self._location

    def _get_filesystem(self, timeout: float) -> "AsyncFileSystem":
        """Get the filesystem, which the first call creates.

        gcsfs and adlfs look up credentials when they are created, which can
        hang on an unreachable metadata server. So the filesystem is created
        in a thread of its own, which calls wait for only as long as their
        timeout allows. Concurrent first calls share that creation, and with
        it the connection pool, and a call after a failed creation retries.

        Args:
            timeout: The seconds to wait for the creation.

        Returns:
            The filesystem.

        Raises:
            TimeoutError: If the creation did not finish in time.
            Exception: The error of a failed creation.
        """
        if self._filesystem is not None:
            return self._filesystem
        with self._filesystem_lock:
            creation = self._filesystem_creation
            if creation is None:
                creation = self._filesystem_creation = Future()
                threading.Thread(
                    target=self._create_filesystem,
                    args=(creation,),
                    name="payload-storage-filesystem",
                    daemon=True,
                ).start()
        try:
            self._filesystem = creation.result(timeout=timeout)
        except FutureTimeoutError:
            raise TimeoutError(
                "The storage client was not created within "
                f"{max(timeout, 0):.1f} seconds."
            ) from None
        except Exception:
            with self._filesystem_lock:
                if self._filesystem_creation is creation:
                    self._filesystem_creation = None
            raise
        return self._filesystem

    def _create_filesystem(self, creation: "Future[AsyncFileSystem]") -> None:
        """Create the filesystem and resolve its creation with it.

        Args:
            creation: The creation to resolve.
        """
        try:
            # The instance cache of fsspec would keep it alive for as long
            # as the process.
            creation.set_result(
                self._filesystem_class(
                    skip_instance_cache=True, **self._filesystem_options
                )
            )
        except BaseException as e:
            creation.set_exception(e)

    def _call_filesystem(
        self,
        make_calls: Callable[["AsyncFileSystem"], "Calls[T]"],
        timeout: float,
    ) -> List[T]:
        """Run filesystem calls, with denied and missing errors translated.

        s3fs raises `PermissionError` and `FileNotFoundError` itself. gcsfs
        reports a 403 as a plain `OSError` and a 401 as its own `HttpError`,
        and adlfs lets Azure's exceptions through.

        Args:
            make_calls: Returns the calls to run on the filesystem.
            timeout: The seconds for creating the filesystem when needed and
                running the calls.

        Returns:
            The results of the calls, in their order.

        Raises:
            TimeoutError: If the calls did not return in time.
            PermissionError: If access was denied.
            FileNotFoundError: If an object or its bucket is missing.
            Exception: Any other error of a call.
        """
        from fsspec.asyn import sync

        deadline = time.monotonic() + timeout
        try:
            filesystem = self._get_filesystem(timeout)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("No time was left for the call.")
            # `sync` gets the timeout too: gcsfs blocks the event loop while it
            # refreshes its credentials.
            results: List[T] = sync(
                filesystem.loop,
                self._run_concurrently,
                make_calls(filesystem),
                remaining,
                timeout=remaining,
            )
            return results
        except Exception as e:
            if isinstance(e, asyncio.TimeoutError):
                raise TimeoutError(
                    "The call did not return within its remaining "
                    f"{max(timeout, 0):.1f} seconds."
                ) from e
            if self._is_permission_error(e):
                raise PermissionError(str(e)) from e
            if self._is_not_found_error(e):
                raise FileNotFoundError(str(e)) from e
            raise

    async def _run_concurrently(
        self, calls: "Calls[T]", timeout: float
    ) -> List[T]:
        """Run calls concurrently, all of them within the timeout.

        When the timeout passes or a call fails, the calls still running are
        cancelled, so that nothing keeps using the object store after the
        request failed.

        Args:
            calls: The calls to run.
            timeout: The seconds after which the calls are cancelled.

        Returns:
            The results of the calls, in their order.
        """
        semaphore = asyncio.Semaphore(self._max_concurrent_calls)

        async def run(call: Callable[[], Awaitable[T]]) -> T:
            async with semaphore:
                return await call()

        tasks = [asyncio.ensure_future(run(call)) for call in calls]
        try:
            return await asyncio.wait_for(asyncio.gather(*tasks), timeout)
        finally:
            for task in tasks:
                task.cancel()

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

    def put_many(
        self, data_by_sha256: Mapping[str, bytes], timeout: float
    ) -> None:
        """Durably store bytes under their SHA-256.

        Args:
            data_by_sha256: The bytes to store by their hex SHA-256.
            timeout: The seconds after which the call raises `TimeoutError`.
        """
        # Object stores only make an object visible once its upload has
        # completed, so the bytes are written straight to their final key.
        self._call_filesystem(
            lambda filesystem: [
                partial(filesystem._pipe_file, f"{self._path}/{sha256}", data)
                for sha256, data in data_by_sha256.items()
            ],
            timeout,
        )

    def get_many(
        self, sha256s: Sequence[str], timeout: float
    ) -> Dict[str, bytes]:
        """Load the bytes stored under SHA-256s.

        Args:
            sha256s: The hex SHA-256s of the bytes.
            timeout: The seconds after which the call raises `TimeoutError`.

        Returns:
            The stored bytes by SHA-256.
        """
        data: List[bytes] = self._call_filesystem(
            lambda filesystem: [
                partial(filesystem._cat_file, f"{self._path}/{sha256}")
                for sha256 in sha256s
            ],
            timeout,
        )
        return dict(zip(sha256s, data))


def _get_azure_account(options: Dict[str, Any]) -> Optional[str]:
    """Get the Azure storage account that adlfs connects to.

    Args:
        options: The options of the adlfs filesystem.

    Returns:
        The account, from the options or, as adlfs does, the environment.
    """
    connection_string = options.get("connection_string") or os.environ.get(
        "AZURE_STORAGE_CONNECTION_STRING"
    )
    if connection_string and (
        match := re.search(r"AccountName=([^;]+)", connection_string)
    ):
        return match.group(1)
    account: Optional[str] = options.get("account_name") or os.environ.get(
        "AZURE_STORAGE_ACCOUNT_NAME"
    )
    return account


def create_blob_backend(
    backend_type: BlobBackendType,
    configuration: Dict[str, Any],
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
        max_concurrent_calls: The number of requests one call sends to the
            object store at once.

    Returns:
        The payload backend.
    """
    import fsspec

    options = dict(configuration)
    path = options.pop("path")
    # Bucket names only select the physical store together with the endpoint
    # of an S3-compatible store or GCS emulator, or the Azure account.
    location = path.rstrip("/")
    if backend_type == BlobBackendType.GCS:
        endpoint_url = options.get("endpoint_url") or os.environ.get(
            "STORAGE_EMULATOR_HOST"
        )
        if endpoint_url and endpoint_url != "default":
            location = f"{location} at {endpoint_url.rstrip('/')}"
    elif backend_type == BlobBackendType.S3:
        endpoint_url = options.get("endpoint_url") or (
            options.get("client_kwargs") or {}
        ).get("endpoint_url")
        if endpoint_url:
            location = f"{location} at {endpoint_url.rstrip('/')}"
        # The S3 client keeps 10 connections by default, and a call's timeout
        # also runs while its requests wait for one.
        options["config_kwargs"] = {
            "max_pool_connections": max_concurrent_calls,
            **(options.get("config_kwargs") or {}),
        }
    elif backend_type == BlobBackendType.AZURE:
        # Older adlfs versions access containers anonymously by default.
        options.setdefault("anon", False)
        if account := _get_azure_account(options):
            location = f"{location} in account {account}"
    protocol, _ = fsspec.core.split_protocol(path)
    return FsspecBlobBackend(
        backend_type,
        path,
        location=location,
        filesystem_class=fsspec.get_filesystem_class(protocol),
        filesystem_options=options,
        max_concurrent_calls=max_concurrent_calls,
    )
