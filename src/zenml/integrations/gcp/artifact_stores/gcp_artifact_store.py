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

from typing import (
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

import gcsfs
from google.cloud import storage
from google.oauth2 import credentials as gcp_credentials

from zenml.artifact_stores import BaseArtifactStore
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


class GCPArtifactStore(BaseArtifactStore, AuthenticationMixin):
    """Artifact Store for Google Cloud Storage based artifacts."""

    _filesystem: Optional[gcsfs.GCSFileSystem] = None

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
