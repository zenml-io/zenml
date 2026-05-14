#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of the GCP Artifact Store."""

import posixpath
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)
from uuid import uuid4

import gcsfs
from google.api_core.exceptions import NotFound, PreconditionFailed
from google.cloud import storage
from google.oauth2 import credentials as gcp_credentials

from zenml.artifact_stores import (
    BaseArtifactStore,
    BulkDeleteResult,
    ObjectDeleteFailure,
    ObjectInfo,
)
from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
    GCP_PATH_PREFIX,
    GCPArtifactStoreConfig,
)
from zenml.io.fileio import convert_to_str
from zenml.logger import get_logger
from zenml.secret.schemas import GCPSecretSchema
from zenml.stack.authentication_mixin import AuthenticationMixin

logger = get_logger(__name__)
PathType = Union[bytes, str]

GCS_COMPOSE_MAX_SOURCES = 32
GCS_COMPOSE_TEMPORARY_PREFIX = ".zenml-compose-"


class GCPArtifactStore(BaseArtifactStore, AuthenticationMixin):
    """Artifact Store for Google Cloud Storage based artifacts."""

    _filesystem: Optional[gcsfs.GCSFileSystem] = None
    _storage_client: Optional[storage.Client] = None

    @property
    def config(self) -> GCPArtifactStoreConfig:
        """Returns the `GCPArtifactStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(GCPArtifactStoreConfig, self._config)

    def get_credentials(
        self,
    ) -> Optional[Union[Dict[str, Any], gcp_credentials.Credentials]]:
        """Returns the credentials for the GCP Artifact Store if configured.

        Returns:
            The credentials.

        Raises:
            RuntimeError: If the linked connector returns the wrong type of
                client.
        """
        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, storage.Client):
                raise RuntimeError(
                    f"Expected a google.cloud.storage.Client while trying to "
                    f"use the linked connector, but got {type(client)}."
                )
            return client._credentials

        secret = self.get_typed_authentication_secret(
            expected_schema_type=GCPSecretSchema
        )
        return secret.get_credential_dict() if secret else None

    @property
    def filesystem(self) -> gcsfs.GCSFileSystem:
        """The gcsfs filesystem to access this artifact store.

        Returns:
            The gcsfs filesystem to access this artifact store.
        """
        # Refresh the credentials also if the connector has expired
        if self._filesystem and not self.connector_has_expired():
            return self._filesystem

        token = self.get_credentials()
        self._filesystem = gcsfs.GCSFileSystem(token=token)

        return self._filesystem

    @property
    def storage_client(self) -> storage.Client:
        """The native GCS client for provider-side object operations.

        Returns:
            A Google Cloud Storage client configured with the same connector or
            secret credentials as the gcsfs filesystem.

        Raises:
            RuntimeError: If the linked connector returns the wrong client type.
        """
        if self._storage_client and not self.connector_has_expired():
            return self._storage_client

        connector = self.get_connector()
        if connector:
            client = connector.connect()
            if not isinstance(client, storage.Client):
                raise RuntimeError(
                    f"Expected a google.cloud.storage.Client while trying to "
                    f"use the linked connector, but got {type(client)}."
                )
            self._storage_client = client
            return self._storage_client

        secret = self.get_typed_authentication_secret(
            expected_schema_type=GCPSecretSchema
        )
        if secret:
            self._storage_client = storage.Client.from_service_account_info(
                secret.get_credential_dict()
            )
        else:
            self._storage_client = storage.Client()

        return self._storage_client

    @staticmethod
    def _split_gcs_uri(uri: str) -> Tuple[str, str]:
        """Split a GCS URI into bucket and object path parts."""
        if not uri.startswith(GCP_PATH_PREFIX):
            raise ValueError(f"Expected a GCS URI, got `{uri}`.")

        path_without_prefix = uri[len(GCP_PATH_PREFIX) :]
        bucket_name, _, blob_name = path_without_prefix.partition("/")
        if not bucket_name:
            raise ValueError(f"GCS URI `{uri}` does not include a bucket.")

        return bucket_name, blob_name

    @staticmethod
    def _build_gcs_uri(bucket_name: str, blob_name: str) -> str:
        """Build a GCS URI from bucket and object path parts."""
        if blob_name:
            return f"{GCP_PATH_PREFIX}{bucket_name}/{blob_name}"
        return f"{GCP_PATH_PREFIX}{bucket_name}"

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
        """Get a blob path relative to a listed GCS prefix."""
        normalized_prefix = prefix_blob_name.rstrip("/")
        if not normalized_prefix:
            return blob_name
        if blob_name == normalized_prefix:
            return posixpath.basename(blob_name)

        prefix_with_separator = f"{normalized_prefix}/"
        if blob_name.startswith(prefix_with_separator):
            return blob_name[len(prefix_with_separator) :]

        return posixpath.basename(blob_name)

    def _get_blob_info(
        self, blob: storage.Blob, bucket_name: str, prefix_blob_name: str
    ) -> ObjectInfo:
        """Build object metadata from a native GCS blob."""
        return ObjectInfo(
            uri=self._build_gcs_uri(bucket_name, blob.name),
            relative_path=self._get_relative_blob_path(
                blob.name, prefix_blob_name
            ),
            size=blob.size,
            etag=blob.etag,
            generation=str(blob.generation) if blob.generation else None,
            last_modified=blob.updated,
        )

    def _compose_blob(
        self,
        bucket: storage.Bucket,
        source_blob_names: Sequence[str],
        destination_blob_name: str,
        overwrite: bool,
    ) -> None:
        """Compose source blobs into one destination blob."""
        source_blobs = [bucket.blob(name) for name in source_blob_names]
        destination_blob = bucket.blob(destination_blob_name)
        if_generation_match = None if overwrite else 0
        destination_blob.compose(
            source_blobs,
            client=self.storage_client,
            if_generation_match=if_generation_match,
        )

    def _cleanup_intermediate_compose_objects(
        self, object_uris: Sequence[str], destination_uri: str
    ) -> None:
        """Best-effort cleanup for temporary GCS compose objects."""
        if not object_uris:
            return

        cleanup_result = self.delete_objects(object_uris)
        if cleanup_result.failures:
            logger.warning(
                "Composed GCS object %s, but failed to clean up %d "
                "temporary compose objects: %s",
                destination_uri,
                len(cleanup_result.failures),
                [failure.path for failure in cleanup_result.failures],
            )

    def list_objects(
        self, prefix: PathType, recursive: bool = False
    ) -> Iterable[ObjectInfo]:
        """List GCS objects below a prefix with native object metadata."""
        sanitized_prefix = self._sanitize_path(prefix)
        bucket_name, prefix_blob_name = self._split_gcs_uri(sanitized_prefix)
        listing_prefix = prefix_blob_name.rstrip("/")

        objects: List[ObjectInfo] = []
        for blob in self.storage_client.list_blobs(
            bucket_name, prefix=listing_prefix
        ):
            if blob.name.endswith("/"):
                continue
            if not self._blob_matches_prefix(blob.name, prefix_blob_name):
                continue

            object_info = self._get_blob_info(
                blob, bucket_name, prefix_blob_name
            )
            if recursive or "/" not in object_info.relative_path.strip("/"):
                objects.append(object_info)

        return objects

    def delete_objects(self, paths: Iterable[PathType]) -> BulkDeleteResult:
        """Delete multiple GCS objects with native delete calls."""
        deleted_paths: List[str] = []
        failures: List[ObjectDeleteFailure] = []

        for path in paths:
            sanitized_path = self._sanitize_path(path)
            try:
                bucket_name, blob_name = self._split_gcs_uri(sanitized_path)
                if not blob_name:
                    raise ValueError(
                        f"Cannot delete GCS bucket root `{sanitized_path}`."
                    )

                bucket = self.storage_client.bucket(bucket_name)
                bucket.blob(blob_name).delete(client=self.storage_client)
            except NotFound:
                deleted_paths.append(sanitized_path)
            except Exception as e:
                failures.append(
                    ObjectDeleteFailure(path=sanitized_path, error=e)
                )
            else:
                deleted_paths.append(sanitized_path)

        return BulkDeleteResult(deleted_paths=deleted_paths, failures=failures)

    def compose_objects(
        self,
        sources: Sequence[PathType],
        destination: PathType,
        overwrite: bool = False,
    ) -> bool:
        """Compose GCS source objects into a destination object in order."""
        sanitized_sources = [self._sanitize_path(source) for source in sources]
        sanitized_destination = self._sanitize_path(destination)
        if not sanitized_sources:
            return False

        destination_bucket_name, destination_blob_name = self._split_gcs_uri(
            sanitized_destination
        )
        bucket = self.storage_client.bucket(destination_bucket_name)
        source_blob_names: List[str] = []
        for source in sanitized_sources:
            source_bucket_name, source_blob_name = self._split_gcs_uri(source)
            if source_bucket_name != destination_bucket_name:
                raise ValueError(
                    "GCS compose requires all source and destination objects "
                    "to be in the same bucket."
                )
            source_blob_names.append(source_blob_name)

        destination_directory = posixpath.dirname(destination_blob_name)
        compose_id = uuid4().hex
        intermediate_uris: List[str] = []
        current_blob_names = source_blob_names
        level = 0

        try:
            while len(current_blob_names) > GCS_COMPOSE_MAX_SOURCES:
                next_blob_names: List[str] = []
                for batch_index in range(
                    0, len(current_blob_names), GCS_COMPOSE_MAX_SOURCES
                ):
                    batch = current_blob_names[
                        batch_index : batch_index + GCS_COMPOSE_MAX_SOURCES
                    ]
                    temporary_blob_name = posixpath.join(
                        destination_directory,
                        f"{GCS_COMPOSE_TEMPORARY_PREFIX}"
                        f"{compose_id}-{level}-{len(next_blob_names):06d}.log",
                    )
                    self._compose_blob(
                        bucket=bucket,
                        source_blob_names=batch,
                        destination_blob_name=temporary_blob_name,
                        overwrite=False,
                    )
                    next_blob_names.append(temporary_blob_name)
                    intermediate_uris.append(
                        self._build_gcs_uri(
                            destination_bucket_name, temporary_blob_name
                        )
                    )

                current_blob_names = next_blob_names
                level += 1
        except Exception:
            self._cleanup_intermediate_compose_objects(
                intermediate_uris, sanitized_destination
            )
            raise

        try:
            self._compose_blob(
                bucket=bucket,
                source_blob_names=current_blob_names,
                destination_blob_name=destination_blob_name,
                overwrite=overwrite,
            )
        except PreconditionFailed:
            destination_blob = bucket.blob(destination_blob_name)
            if not overwrite and destination_blob.exists(
                client=self.storage_client
            ):
                self._cleanup_intermediate_compose_objects(
                    intermediate_uris, sanitized_destination
                )
                return True

            self._cleanup_intermediate_compose_objects(
                intermediate_uris, sanitized_destination
            )
            raise
        except Exception:
            self._cleanup_intermediate_compose_objects(
                intermediate_uris, sanitized_destination
            )
            raise

        self._cleanup_intermediate_compose_objects(
            intermediate_uris, sanitized_destination
        )
        return True

    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently, only
                'rb' and 'wb' to read and write binary files are supported.

        Returns:
            A file-like object that can be used to read or write to the file.
        """
        if mode in ("a", "ab"):
            logger.warning(
                "GCS Filesystem is immutable, so append mode will overwrite existing files."
            )
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
        return [
            f"{GCP_PATH_PREFIX}{path}"
            for path in self.filesystem.glob(path=pattern)
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
            path: The path of the directory to list.

        Returns:
            A list of paths of files in the directory.
        """
        path_without_prefix = convert_to_str(path)
        if path_without_prefix.startswith(GCP_PATH_PREFIX):
            path_without_prefix = path_without_prefix[len(GCP_PATH_PREFIX) :]

        def _extract_basename(file_dict: Dict[str, Any]) -> str:
            """Extracts the basename from a file info dict returned by GCP.

            Args:
                file_dict: A file info dict returned by the GCP filesystem.

            Returns:
                The basename of the file.
            """
            file_path = cast(str, file_dict["name"])
            base_name = file_path[len(path_without_prefix) :]
            return base_name.lstrip("/")

        return [
            _extract_basename(dict_)
            for dict_ in self.filesystem.listdir(path=path)
            # gcsfs.listdir also returns the root directory, so we filter
            # it out here
            if _extract_basename(dict_)
        ]

    def makedirs(self, path: PathType) -> None:
        """Create a directory at the given path.

        If needed also create missing parent directories.

        Args:
            path: The path of the directory to create.
        """
        self.filesystem.makedirs(path=path, exist_ok=True)

    def mkdir(self, path: PathType) -> None:
        """Create a directory at the given path.

        Args:
            path: The path of the directory to create.
        """
        self.filesystem.makedir(path=path)

    def remove(self, path: PathType) -> None:
        """Remove the file at the given path.

        Args:
            path: The path of the file to remove.
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
            path: the path to get stat info for.

        Returns:
            A dictionary with the stat info.
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
        for (
            directory,
            subdirectories,
            files,
        ) in self.filesystem.walk(path=top):
            yield f"{GCP_PATH_PREFIX}{directory}", subdirectories, files
