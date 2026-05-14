#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the Azure Artifact Store integration."""

import posixpath
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

import adlfs

from zenml.artifact_stores import (
    BaseArtifactStore,
    BulkDeleteResult,
    ObjectDeleteFailure,
    ObjectInfo,
)
from zenml.integrations.azure.flavors.azure_artifact_store_flavor import (
    AzureArtifactStoreConfig,
)
from zenml.io.fileio import convert_to_str
from zenml.secret.schemas import AzureSecretSchema
from zenml.stack.authentication_mixin import AuthenticationMixin
from zenml.utils import io_utils

if TYPE_CHECKING:
    from azure.storage.blob import BlobServiceClient

PathType = Union[bytes, str]

AZURE_APPEND_BLOB_MAX_BLOCK_BYTES = 4 * 1024 * 1024
AZURE_APPEND_BLOB_MAX_BLOCKS = 50000
AZURE_BLOB_BATCH_DELETE_LIMIT = 256


class _AzureAppendBlobWriter:
    """Small file-like writer backed by Azure append blobs."""

    def __init__(
        self,
        blob_client: Any,
        committed_block_count: int,
    ) -> None:
        """Initialize the append blob writer."""
        self._blob_client = blob_client
        self._committed_block_count = committed_block_count
        self._closed = False

    def __enter__(self) -> "_AzureAppendBlobWriter":
        """Enter the writer context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Close the writer when leaving the context manager."""
        self.close()

    def writable(self) -> bool:
        """Return whether this object supports writing."""
        return True

    def write(self, data: Union[str, bytes]) -> int:
        """Append data to the backing append blob in provider-safe blocks."""
        if self._closed:
            raise ValueError(
                "I/O operation on closed Azure append blob writer."
            )

        if isinstance(data, str):
            encoded_data = data.encode("utf-8")
            written_length = len(data)
        else:
            encoded_data = data
            written_length = len(data)

        if not encoded_data:
            return written_length

        block_count = (
            len(encoded_data) + AZURE_APPEND_BLOB_MAX_BLOCK_BYTES - 1
        ) // AZURE_APPEND_BLOB_MAX_BLOCK_BYTES
        if (
            self._committed_block_count + block_count
            > AZURE_APPEND_BLOB_MAX_BLOCKS
        ):
            raise OSError(
                "Azure append blob block limit reached; falling back to "
                "the regular adlfs append path is required."
            )

        for start in range(
            0, len(encoded_data), AZURE_APPEND_BLOB_MAX_BLOCK_BYTES
        ):
            block = encoded_data[
                start : start + AZURE_APPEND_BLOB_MAX_BLOCK_BYTES
            ]
            self._blob_client.append_block(block)
            self._committed_block_count += 1

        return written_length

    def flush(self) -> None:
        """Flush pending data.

        Writes are sent immediately by ``write()``, so there is nothing to do.
        """

    def close(self) -> None:
        """Close the writer."""
        self._closed = True


class AzureArtifactStore(BaseArtifactStore, AuthenticationMixin):
    """Artifact Store for Microsoft Azure based artifacts."""

    _filesystem: Optional[adlfs.AzureBlobFileSystem] = None
    _blob_service_client: Optional["BlobServiceClient"] = None

    @property
    def config(self) -> AzureArtifactStoreConfig:
        """Returns the `AzureArtifactStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureArtifactStoreConfig, self._config)

    def get_credentials(self) -> Optional[AzureSecretSchema]:
        """Returns the credentials for the Azure Artifact Store if configured.

        Returns:
            The credentials.

        Raises:
            RuntimeError: If the connector is not configured with Azure service
                principal credentials.
        """
        connector = self.get_connector()
        if connector:
            from azure.identity import (
                ClientSecretCredential,
                DefaultAzureCredential,
            )
            from azure.storage.blob import BlobServiceClient

            client = connector.connect()
            if not isinstance(client, BlobServiceClient):
                raise RuntimeError(
                    f"Expected a {BlobServiceClient.__module__}."
                    f"{BlobServiceClient.__name__} object while "
                    f"trying to use the linked connector, but got "
                    f"{type(client)}."
                )
            # Get the credentials from the client
            credentials = client.credential

            if isinstance(credentials, ClientSecretCredential):
                return AzureSecretSchema(
                    client_id=credentials._client_id,
                    client_secret=credentials._client_credential,
                    tenant_id=credentials._tenant_id,
                    account_name=client.account_name,
                )

            elif isinstance(credentials, DefaultAzureCredential):
                return AzureSecretSchema(account_name=client.account_name)

            else:
                raise RuntimeError(
                    "The Azure Artifact Store connector can only be used "
                    "with a service connector that is configured with "
                    "Azure service principal credentials or implicit authentication"
                )

        secret = self.get_typed_authentication_secret(
            expected_schema_type=AzureSecretSchema
        )
        return secret

    @property
    def blob_service_client(self) -> "BlobServiceClient":
        """The native Azure Blob Storage client for object operations.

        Returns:
            An Azure Blob service client configured with the same connector or
            secret credentials as the adlfs filesystem.
        """
        if self._blob_service_client and not self.connector_has_expired():
            return self._blob_service_client

        from azure.identity import (
            ClientSecretCredential,
            DefaultAzureCredential,
        )
        from azure.storage.blob import BlobServiceClient

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, BlobServiceClient):
                raise RuntimeError(
                    f"Expected a {BlobServiceClient.__module__}."
                    f"{BlobServiceClient.__name__} object while "
                    f"trying to use the linked connector, but got "
                    f"{type(client)}."
                )
            self._blob_service_client = client
            return self._blob_service_client

        secret = self.get_typed_authentication_secret(
            expected_schema_type=AzureSecretSchema
        )
        if secret and secret.connection_string:
            self._blob_service_client = (
                BlobServiceClient.from_connection_string(
                    secret.connection_string
                )
            )
            return self._blob_service_client

        credentials = secret.get_values() if secret else {}
        account_name = credentials.get("account_name")
        if not account_name:
            account_name = getattr(self.filesystem, "account_name", None)
        if not account_name:
            raise RuntimeError(
                "Cannot create an Azure BlobServiceClient without an "
                "account name. Configure Azure artifact store credentials "
                "with an account_name or use a service connector."
            )

        if credentials.get("client_id") and credentials.get("client_secret"):
            credential: Any = ClientSecretCredential(
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"],
                tenant_id=credentials["tenant_id"],
            )
        else:
            credential = credentials.get("account_key") or credentials.get(
                "sas_token"
            )
            if credential is None:
                credential = DefaultAzureCredential()

        account_url = f"https://{account_name}.blob.core.windows.net/"
        self._blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential,
        )
        return self._blob_service_client

    @property
    def filesystem(self) -> adlfs.AzureBlobFileSystem:
        """The adlfs filesystem to access this artifact store.

        Returns:
            The adlfs filesystem to access this artifact store.
        """
        if not self._filesystem:
            secret = self.get_credentials()
            credentials = secret.get_values() if secret else {}

            self._filesystem = adlfs.AzureBlobFileSystem(
                **credentials,
                anon=False,
                use_listings_cache=False,
            )
        return self._filesystem

    def _split_path(self, path: PathType) -> Tuple[str, str]:
        """Splits a path into the filesystem prefix and remainder.

        Example:
        ```python
        prefix, remainder = ZenAzure._split_path("az://my_container/test.txt")
        print(prefix, remainder)  # "az://" "my_container/test.txt"
        ```

        Args:
            path: The path to split.

        Returns:
            A tuple of the filesystem prefix and the remainder.
        """
        path = convert_to_str(path)
        prefix = ""
        for potential_prefix in self.config.SUPPORTED_SCHEMES:
            if path.startswith(potential_prefix):
                prefix = potential_prefix
                path = path[len(potential_prefix) :]
                break

        return prefix, path

    def _split_azure_uri(self, uri: str) -> Tuple[str, str, str]:
        """Split an Azure artifact URI into scheme, container, and blob path."""
        scheme, path = self._split_path(uri)
        if not scheme:
            raise ValueError(f"Expected an Azure URI, got `{uri}`.")

        container_name, _, blob_name = path.partition("/")
        if not container_name:
            raise ValueError(
                f"Azure URI `{uri}` does not include a container."
            )

        return scheme, container_name, blob_name

    @staticmethod
    def _build_azure_uri(
        scheme: str, container_name: str, blob_name: str
    ) -> str:
        """Build an Azure artifact URI from path parts."""
        if blob_name:
            return f"{scheme}{container_name}/{blob_name}"
        return f"{scheme}{container_name}"

    @staticmethod
    def _blob_matches_prefix(blob_name: str, prefix_blob_name: str) -> bool:
        """Return whether a blob belongs to a requested file/directory prefix."""
        if not prefix_blob_name:
            return True

        normalized_prefix = prefix_blob_name.rstrip("/")
        return blob_name == normalized_prefix or blob_name.startswith(
            f"{normalized_prefix}/"
        )

    @staticmethod
    def _get_relative_blob_path(blob_name: str, prefix_blob_name: str) -> str:
        """Get a blob path relative to a listed Azure prefix."""
        normalized_prefix = prefix_blob_name.rstrip("/")
        if not normalized_prefix:
            return blob_name
        if blob_name == normalized_prefix:
            return posixpath.basename(blob_name)

        prefix_with_separator = f"{normalized_prefix}/"
        if blob_name.startswith(prefix_with_separator):
            return blob_name[len(prefix_with_separator) :]

        return posixpath.basename(blob_name)

    def _get_container_client(self, container_name: str) -> Any:
        """Return a native Azure container client."""
        return self.blob_service_client.get_container_client(container_name)

    def _get_blob_client(self, uri: str) -> Any:
        """Return a native Azure blob client for an artifact URI."""
        _, container_name, blob_name = self._split_azure_uri(uri)
        if not blob_name:
            raise ValueError(
                f"Azure URI `{uri}` does not include a blob path."
            )
        return self.blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

    def _get_blob_info(
        self,
        blob: Any,
        scheme: str,
        container_name: str,
        prefix_blob_name: str,
    ) -> ObjectInfo:
        """Build object metadata from native Azure blob properties."""
        blob_name = cast(str, blob.name)
        size = getattr(blob, "size", None)
        if size is None:
            size = getattr(blob, "content_length", None)

        return ObjectInfo(
            uri=self._build_azure_uri(scheme, container_name, blob_name),
            relative_path=self._get_relative_blob_path(
                blob_name, prefix_blob_name
            ),
            size=size,
            etag=getattr(blob, "etag", None),
            version=getattr(blob, "version_id", None),
            last_modified=getattr(blob, "last_modified", None),
        )

    @staticmethod
    def _is_append_blob_type(blob_type: Any) -> bool:
        """Return whether an Azure blob type value describes an append blob."""
        value = getattr(blob_type, "value", blob_type)
        normalized_value = (
            str(value)
            .lower()
            .replace("blobtype.", "")
            .replace("_", "")
            .replace("-", "")
        )
        return normalized_value == "appendblob"

    def _get_append_blob_writer(
        self, path: PathType, mode: str
    ) -> Optional[_AzureAppendBlobWriter]:
        """Create an append-blob writer or return None for adlfs fallback."""
        try:
            sanitized_path = self._sanitize_path(path)
            blob_client = self._get_blob_client(sanitized_path)
            committed_block_count = 0

            from azure.core.exceptions import (
                ResourceExistsError,
                ResourceNotFoundError,
            )

            try:
                properties = blob_client.get_blob_properties()
            except ResourceNotFoundError:
                try:
                    blob_client.create_append_blob()
                except ResourceExistsError:
                    properties = blob_client.get_blob_properties()
                    if not self._is_append_blob_type(
                        getattr(properties, "blob_type", "")
                    ):
                        return None
                    committed_block_count = cast(
                        int,
                        getattr(
                            properties,
                            "append_blob_committed_block_count",
                            0,
                        )
                        or 0,
                    )
            else:
                if not self._is_append_blob_type(
                    getattr(properties, "blob_type", "")
                ):
                    return None

                committed_block_count = cast(
                    int,
                    getattr(
                        properties,
                        "append_blob_committed_block_count",
                        0,
                    )
                    or 0,
                )

            return _AzureAppendBlobWriter(
                blob_client=blob_client,
                committed_block_count=committed_block_count,
            )
        except Exception:
            return None

    def list_objects(
        self, prefix: PathType, recursive: bool = False
    ) -> Iterable[ObjectInfo]:
        """List Azure blobs below a prefix with native object metadata."""
        sanitized_prefix = self._sanitize_path(prefix)
        scheme, container_name, prefix_blob_name = self._split_azure_uri(
            sanitized_prefix
        )
        listing_prefix = prefix_blob_name.rstrip("/")
        container_client = self._get_container_client(container_name)

        objects: List[ObjectInfo] = []
        for blob in container_client.list_blobs(
            name_starts_with=listing_prefix
        ):
            blob_name = cast(str, blob.name)
            if blob_name.endswith("/"):
                continue
            if not self._blob_matches_prefix(blob_name, prefix_blob_name):
                continue

            object_info = self._get_blob_info(
                blob, scheme, container_name, prefix_blob_name
            )
            if recursive or "/" not in object_info.relative_path.strip("/"):
                objects.append(object_info)

        return objects

    def delete_objects(self, paths: Iterable[PathType]) -> BulkDeleteResult:
        """Delete multiple Azure blobs with native batch deletion."""
        deleted_paths: List[str] = []
        failures: List[ObjectDeleteFailure] = []
        grouped_paths: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}

        for path in paths:
            sanitized_path = self._sanitize_path(path)
            try:
                scheme, container_name, blob_name = self._split_azure_uri(
                    sanitized_path
                )
                if not blob_name:
                    raise ValueError(
                        f"Cannot delete Azure container root `{sanitized_path}`."
                    )
            except Exception as e:
                failures.append(
                    ObjectDeleteFailure(path=sanitized_path, error=e)
                )
                continue

            grouped_paths.setdefault((scheme, container_name), []).append(
                (sanitized_path, blob_name)
            )

        for (_, container_name), path_group in grouped_paths.items():
            container_client = self._get_container_client(container_name)
            for batch_start in range(
                0, len(path_group), AZURE_BLOB_BATCH_DELETE_LIMIT
            ):
                batch = path_group[
                    batch_start : batch_start + AZURE_BLOB_BATCH_DELETE_LIMIT
                ]
                try:
                    responses = container_client.delete_blobs(
                        *[blob_name for _, blob_name in batch],
                        delete_snapshots="include",
                    )
                    for _ in responses:
                        pass
                except Exception:
                    self._delete_blob_batch_individually(
                        container_client=container_client,
                        batch=batch,
                        deleted_paths=deleted_paths,
                        failures=failures,
                    )
                else:
                    deleted_paths.extend(path for path, _ in batch)

        return BulkDeleteResult(deleted_paths=deleted_paths, failures=failures)

    def _delete_blob_batch_individually(
        self,
        container_client: Any,
        batch: List[Tuple[str, str]],
        deleted_paths: List[str],
        failures: List[ObjectDeleteFailure],
    ) -> None:
        """Delete blobs one by one after a batch delete failure."""
        from azure.core.exceptions import ResourceNotFoundError

        for sanitized_path, blob_name in batch:
            try:
                container_client.delete_blob(
                    blob_name, delete_snapshots="include"
                )
            except ResourceNotFoundError:
                deleted_paths.append(sanitized_path)
            except Exception as e:
                failures.append(
                    ObjectDeleteFailure(path=sanitized_path, error=e)
                )
            else:
                deleted_paths.append(sanitized_path)

    def read_range(
        self, path: PathType, offset: int, length: Optional[int] = None
    ) -> bytes:
        """Read a byte range from an Azure blob."""
        if offset < 0:
            raise ValueError("Range read offset must be non-negative.")
        if length is not None and length < 0:
            raise ValueError("Range read length must be non-negative.")

        sanitized_path = self._sanitize_path(path)
        blob_client = self._get_blob_client(sanitized_path)
        return cast(
            bytes,
            blob_client.download_blob(offset=offset, length=length).readall(),
        )

    def download_objects_to_directory(
        self,
        objects: Iterable[ObjectInfo],
        local_dir: PathType,
        max_workers: Optional[int] = None,
    ) -> bool:
        """Download Azure blobs into a local directory."""
        local_dir_str = (
            convert_to_str(local_dir)
            if isinstance(local_dir, bytes)
            else str(local_dir)
        )
        if io_utils.is_remote(local_dir_str):
            raise ValueError("Download directory must be a local path.")
        local_path = Path(local_dir_str)
        download_root = local_path.resolve()

        for object_info in objects:
            destination = (download_root / object_info.relative_path).resolve()
            if not destination.is_relative_to(download_root):
                raise ValueError(
                    "Refusing to download Azure blob outside target "
                    f"directory: {object_info.relative_path}"
                )

            sanitized_uri = self._sanitize_path(object_info.uri)
            blob_client = self._get_blob_client(sanitized_uri)
            destination.parent.mkdir(parents=True, exist_ok=True)
            download_kwargs = {}
            if max_workers is not None:
                download_kwargs["max_concurrency"] = max_workers

            with destination.open("wb") as file:
                file.write(
                    blob_client.download_blob(**download_kwargs).readall()
                )

        return True

    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently, only
                'rb' and 'wb' to read and write binary files are supported.

        Returns:
            A file-like object.
        """
        if mode in ("a", "ab"):
            append_blob_writer = self._get_append_blob_writer(path, mode)
            if append_blob_writer:
                return append_blob_writer

        return self.filesystem.open(path=path, mode=mode)

    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file.

        Args:
            src: The path to copy from.
            dst: The path to copy to.
            overwrite: If a file already exists at the destination, this
                method will overwrite it if overwrite=`True` and
                raise a FileExistsError otherwise.

        Raises:
            FileExistsError: If a file already exists at the destination
                and overwrite is not set to `True`.
        """
        if not overwrite and self.filesystem.exists(dst):
            raise FileExistsError(
                f"Unable to copy to destination '{convert_to_str(dst)}', "
                f"file already exists. Set `overwrite=True` to copy anyway."
            )

        # TODO [ENG-151]: Check if it works with overwrite=True or if we need to
        #  manually remove it first
        self.filesystem.copy(path1=src, path2=dst)

    def exists(self, path: PathType) -> bool:
        """Check whether a path exists.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        return self.filesystem.exists(path=path)  # type: ignore[no-any-return]

    def glob(self, pattern: PathType) -> List[PathType]:
        """Return all paths that match the given glob pattern.

        The glob pattern may include:
        - '*' to match any number of characters
        - '?' to match a single character
        - '[...]' to match one of the characters inside the brackets
        - '**' as the full name of a path component to match to search
            in subdirectories of any depth (e.g. '/some_dir/**/some_file)

        Args:
            pattern: The glob pattern to match, see details above.

        Returns:
            A list of paths that match the given glob pattern.
        """
        prefix, _ = self._split_path(pattern)
        return [
            f"{prefix}{path}" for path in self.filesystem.glob(path=pattern)
        ]

    def isdir(self, path: PathType) -> bool:
        """Check whether a path is a directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a directory, False otherwise.
        """
        return self.filesystem.isdir(path=path)  # type: ignore[no-any-return]

    def listdir(self, path: PathType) -> List[PathType]:
        """Return a list of files in a directory.

        Args:
            path: The path to list.

        Returns:
            A list of files in the given directory.
        """
        _, path = self._split_path(path)

        def _extract_basename(file_dict: Dict[str, Any]) -> str:
            """Extracts the basename from a dictionary returned by the Azure filesystem.

            Args:
                file_dict: A dictionary returned by the Azure filesystem.

            Returns:
                The basename of the file.
            """
            file_path = cast(str, file_dict["name"])
            base_name = file_path[len(path) :]
            return base_name.lstrip("/")

        return [
            _extract_basename(dict_)
            for dict_ in self.filesystem.listdir(path=path)
        ]

    def makedirs(self, path: PathType) -> None:
        """Create a directory at the given path.

        If needed also create missing parent directories.

        Args:
            path: The path to create.
        """
        self.filesystem.makedirs(path=path, exist_ok=True)

    def mkdir(self, path: PathType) -> None:
        """Create a directory at the given path.

        Args:
            path: The path to create.
        """
        self.filesystem.makedir(path=path, exist_ok=True)

    def remove(self, path: PathType) -> None:
        """Remove the file at the given path.

        Args:
            path: The path to remove.
        """
        self.filesystem.rm_file(path=path)

    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename source file to destination file.

        Args:
            src: The path of the file to rename.
            dst: The path to rename the source file to.
            overwrite: If a file already exists at the destination, this
                method will overwrite it if overwrite=`True` and
                raise a FileExistsError otherwise.

        Raises:
            FileExistsError: If a file already exists at the destination
                and overwrite is not set to `True`.
        """
        if not overwrite and self.filesystem.exists(dst):
            raise FileExistsError(
                f"Unable to rename file to '{convert_to_str(dst)}', "
                f"file already exists. Set `overwrite=True` to rename anyway."
            )

        # TODO [ENG-152]: Check if it works with overwrite=True or if we need
        #  to manually remove it first
        self.filesystem.rename(path1=src, path2=dst)

    def rmtree(self, path: PathType) -> None:
        """Remove the given directory.

        Args:
            path: The path of the directory to remove.
        """
        self.filesystem.delete(path=path, recursive=True)

    def stat(self, path: PathType) -> Dict[str, Any]:
        """Return stat info for the given path.

        Args:
            path: The path to get stat info for.

        Returns:
            Stat info.
        """
        return self.filesystem.stat(path=path)  # type: ignore[no-any-return]

    def size(self, path: PathType) -> int:
        """Get the size of a file in bytes.

        Args:
            path: The path to the file.

        Returns:
            The size of the file in bytes.
        """
        return self.filesystem.size(path=path)  # type: ignore[no-any-return]

    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory.

        Args:
            top: Path of directory to walk.
            topdown: Unused argument to conform to interface.
            onerror: Unused argument to conform to interface.

        Yields:
            An Iterable of Tuples, each of which contain the path of the current
            directory path, a list of directories inside the current directory
            and a list of files inside the current directory.
        """
        # TODO [ENG-153]: Additional params
        prefix, _ = self._split_path(top)
        for (
            directory,
            subdirectories,
            files,
        ) in self.filesystem.walk(path=top):
            yield f"{prefix}{directory}", subdirectories, files
