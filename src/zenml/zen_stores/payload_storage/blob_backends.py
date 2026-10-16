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

GCS_DEFAULT_ENDPOINT = "https://storage.googleapis.com"

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
    raises within the timeout it is given, plus a moment to clean up its
    requests, since it holds a server thread while it runs.
    """

    @property
    @abstractmethod
    def location(self) -> str:
        """Where the blobs are stored, such as `s3://bucket/prefix`.

        It includes the endpoint that the client sends requests to, wherever
        the provider takes it from, such as the environment or a config file,
        unless bucket names are global behind it, as on AWS and GCS. It never
        includes credentials, so that they can change.

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
    `s3://bucket/prefix/<sha256>`. A call writes or reads its blobs
    concurrently on the event loop of fsspec, whose s3fs, gcsfs and adlfs
    filesystems are all async, rather than through their own batch methods:
    those differ per provider (adlfs reads one file at a time) and leave
    requests running when they time out. On their own, requests against a
    stalled endpoint keep going for minutes (s3fs retries five times, gcsfs
    six).
    """

    _CLEANUP_GRACE_SECONDS = 0.1

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
            location: The path, with the endpoint that the client sends
                requests to unless bucket names are global behind it.
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
        reports a 403 as a plain `OSError`, a 401 as its own `HttpError` or,
        when it calls the credentials invalid, as a `ValueError`, and adlfs
        lets Azure's exceptions through.

        Args:
            make_calls: Returns the calls to run on the filesystem.
            timeout: The seconds for creating the filesystem when needed and
                running the calls.

        Returns:
            The results of the calls, in their order.

        Raises:
            RuntimeError: If called from the event loop of fsspec, which it
                would block.
            TimeoutError: If the calls did not return in time.
            PermissionError: If access was denied.
            FileNotFoundError: If an object or its bucket is missing.
            Exception: Any other error of a call.
        """
        deadline = time.monotonic() + timeout
        try:
            filesystem = self._get_filesystem(timeout)
            try:
                on_loop = asyncio.get_running_loop() is filesystem.loop
            except RuntimeError:
                on_loop = False
            if on_loop:
                raise RuntimeError(
                    "Payload storage cannot be called from the event loop "
                    "of fsspec, which it would block."
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("No time was left for the call.")
            future = asyncio.run_coroutine_threadsafe(
                self._run_concurrently(make_calls(filesystem), deadline),
                filesystem.loop,
            )
            try:
                # The caller times out on its own too: gcsfs blocks the event
                # loop while it refreshes its credentials.
                return future.result(
                    timeout=remaining + self._CLEANUP_GRACE_SECONDS
                )
            finally:
                future.cancel()
        except (TimeoutError, asyncio.TimeoutError, FutureTimeoutError) as e:
            raise TimeoutError(
                "The call did not return within its remaining "
                f"{max(timeout, 0):.1f} seconds."
            ) from e
        except Exception as e:
            if self._is_permission_error(e):
                raise PermissionError(str(e)) from e
            if self._is_not_found_error(e):
                raise FileNotFoundError(str(e)) from e
            raise

    async def _run_concurrently(
        self, calls: "Calls[T]", deadline: float
    ) -> List[T]:
        """Run calls concurrently, all of them before a deadline.

        When the deadline passes or a call fails, the calls still running are
        cancelled and awaited, so that nothing keeps using the object store
        after the request failed. A call that is due after the deadline, such
        as once a blocked event loop is free again, never starts.

        Args:
            calls: The calls to run.
            deadline: The `time.monotonic()` after which the calls are
                cancelled.

        Returns:
            The results of the calls, in their order.

        Raises:
            asyncio.TimeoutError: If the deadline passed before every call
                returned.
        """
        semaphore = asyncio.Semaphore(self._max_concurrent_calls)

        async def run(call: Callable[[], Awaitable[T]]) -> T:
            async with semaphore:
                if time.monotonic() >= deadline:
                    raise asyncio.TimeoutError
                return await call()

        # `asyncio.wait` rejects an empty set of calls.
        if not calls:
            return []
        tasks = [asyncio.ensure_future(run(call)) for call in calls]
        # Not `wait_for` around `gather`: when the caller gives up and cancels
        # this, Python 3.10 to 3.12 can leave either of them with an error
        # that nobody retrieves, which asyncio then logs.
        try:
            done, pending = await asyncio.wait(
                tasks,
                timeout=deadline - time.monotonic(),
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for task in done:
                task.result()
            if pending:
                raise asyncio.TimeoutError
            return [task.result() for task in tasks]
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

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
                # gcsfs raises this for an error response that calls the
                # request invalid, such as a 401 for invalid credentials,
                # and never retries it itself.
                or (
                    type(error) is ValueError
                    and str(error).startswith("Bad Request: ")
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
                partial(self._read, filesystem, f"{self._path}/{sha256}")
                for sha256 in sha256s
            ],
            timeout,
        )
        return dict(zip(sha256s, data))

    async def _read(self, filesystem: "AsyncFileSystem", path: str) -> bytes:
        """Read the bytes of a blob.

        adlfs reads Azure blobs with the `readall` of the Azure SDK, which
        downloads a blob larger than its first request in tasks of its own,
        and cancelling the read leaves them running. Iterating the chunks of
        the download instead downloads them one after another in the read
        itself.

        Args:
            filesystem: The filesystem of the blob.
            path: The path of the blob.

        Returns:
            The bytes of the blob.
        """
        if self._backend_type != BlobBackendType.AZURE:
            data: bytes = await filesystem._cat_file(path)
            return data
        container, blob = filesystem.split_path(path)[:2]
        async with filesystem.service_client.get_blob_client(
            container=container, blob=blob
        ) as client:
            download = await client.download_blob()
            return b"".join([chunk async for chunk in download.chunks()])


def _pin_s3_endpoint(options: Dict[str, Any]) -> Dict[str, Any]:
    """Pin the S3 client of s3fs to the endpoint it would send requests to.

    Without one in the options, botocore takes the endpoint from the
    environment or the AWS config file, for the profile s3fs creates its
    session with, when s3fs creates the client on the first call. So the
    endpoint they configure now becomes the `endpoint_url` option, which
    takes precedence over them, and the client ignores them.

    Args:
        options: The options of the s3fs filesystem.

    Returns:
        The options, with the `endpoint_url` that the client sends requests
        to, or None for the default endpoint of the AWS region.
    """
    endpoint_url: Optional[str] = options.get("endpoint_url") or (
        options.get("client_kwargs") or {}
    ).get("endpoint_url")
    try:
        # botocore calls this provider private, but its clients resolve
        # configured endpoints with it, while a client's own endpoint does not
        # tell them apart from the default one of its region. Versions without
        # it ignore configured endpoints, and have no option to ignore them.
        from botocore.configprovider import ConfiguredEndpointProvider
    except ImportError:
        return {**options, "endpoint_url": endpoint_url}
    import botocore.session

    config_kwargs = options.get("config_kwargs") or {}
    if not endpoint_url:
        session = botocore.session.Session(profile=options.get("profile"))
        ignore_configured_endpoint = config_kwargs.get(
            "ignore_configured_endpoint_urls"
        )
        if ignore_configured_endpoint is None:
            ignore_configured_endpoint = session.get_config_variable(
                "ignore_configured_endpoint_urls"
            )
        if not ignore_configured_endpoint:
            endpoint_url = ConfiguredEndpointProvider(
                full_config=session.full_config,
                scoped_config=session.get_scoped_config(),
                client_name="s3",
            ).provide()
    return {
        **options,
        "endpoint_url": endpoint_url,
        "config_kwargs": {
            **config_kwargs,
            "ignore_configured_endpoint_urls": True,
        },
    }


def _get_azure_endpoint(options: Dict[str, Any]) -> Optional[str]:
    """Get the blob endpoint that adlfs connects to.

    As in adlfs, a connection string takes precedence over an account name,
    and the endpoint of an account is its `account_host` or else in the
    public Azure cloud.

    Args:
        options: The options of the adlfs filesystem.

    Returns:
        The endpoint, without the SAS token it may hold, or None without an
        account to connect to.
    """
    connection_string = options.get("connection_string")
    if connection_string:
        from azure.storage.blob import BlobServiceClient

        client = BlobServiceClient.from_connection_string(connection_string)
        url: str = client.url
        return url.partition("?")[0]
    account_name = options.get("account_name")
    if not account_name:
        return None
    account_host = (
        options.get("account_host") or f"{account_name}.blob.core.windows.net"
    )
    return f"https://{account_host}"


def create_blob_backend(
    backend_type: BlobBackendType,
    configuration: Dict[str, Any],
    max_concurrent_calls: int,
) -> BlobBackend:
    """Create a payload backend from its configuration.

    Creating a backend never connects to its storage, so a store starts even
    while its storage is unavailable. A missing filesystem library, or a
    configuration the client would reject when resolving the endpoint, such
    as an unknown AWS profile or an invalid Azure connection string, fails
    here, when the store starts.

    The endpoint is resolved here, once, and passed to the client as an
    option, since the first call creates the client and it would resolve the
    endpoint again, from configuration that may have changed since.

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
    from fsspec.config import apply_config

    protocol, _ = fsspec.core.split_protocol(configuration["path"])
    filesystem_class = fsspec.get_filesystem_class(protocol)
    options = apply_config(filesystem_class, configuration)
    path = options.pop("path")
    endpoint_url: Optional[str] = None
    if backend_type == BlobBackendType.GCS:
        # gcsfs calls this private resolver of the environment's endpoint for
        # every request without an endpoint in its options.
        from gcsfs.core import _location

        options["endpoint_url"] = options.get("endpoint_url") or _location()
        if options["endpoint_url"] != GCS_DEFAULT_ENDPOINT:
            endpoint_url = options["endpoint_url"]
    elif backend_type == BlobBackendType.S3:
        options = _pin_s3_endpoint(options)
        endpoint_url = options["endpoint_url"]
        # The S3 client keeps 10 connections by default, and a call's timeout
        # also runs while its requests wait for one.
        options["config_kwargs"] = {
            "max_pool_connections": max_concurrent_calls,
            **(options.get("config_kwargs") or {}),
        }
    elif backend_type == BlobBackendType.AZURE:
        # Older adlfs versions access containers anonymously by default.
        options.setdefault("anon", False)
        # adlfs takes these from the environment when it is created.
        for option, variable in (
            ("connection_string", "AZURE_STORAGE_CONNECTION_STRING"),
            ("account_name", "AZURE_STORAGE_ACCOUNT_NAME"),
        ):
            options[option] = options.get(option) or os.environ.get(variable)
        endpoint_url = _get_azure_endpoint(options)
    location = path.rstrip("/")
    if endpoint_url:
        location = f"{location} at {endpoint_url.rstrip('/')}"
    return FsspecBlobBackend(
        backend_type,
        path,
        location=location,
        filesystem_class=filesystem_class,
        filesystem_options=options,
        max_concurrent_calls=max_concurrent_calls,
    )
