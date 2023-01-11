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

import adlfs

from zenml.artifact_stores import BaseArtifactStore
from zenml.integrations.azure.flavors.azure_artifact_store_flavor import (
    AzureArtifactStoreConfig,
)
from zenml.secret.schemas import AzureSecretSchema
from zenml.stack.authentication_mixin import AuthenticationMixin
from zenml.utils.io_utils import convert_to_str

PathType = Union[bytes, str]


class AzureArtifactStore(BaseArtifactStore, AuthenticationMixin):
    """Artifact Store for Microsoft Azure based artifacts."""

    _filesystem: Optional[adlfs.AzureBlobFileSystem] = None

    @property
    def config(self) -> AzureArtifactStoreConfig:
        """Returns the `AzureArtifactStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureArtifactStoreConfig, self._config)

    @property
    def filesystem(self) -> adlfs.AzureBlobFileSystem:
        """The adlfs filesystem to access this artifact store.

        Returns:
            The adlfs filesystem to access this artifact store.
        """
        if not self._filesystem:
            secret = self.get_authentication_secret(
                expected_schema_type=AzureSecretSchema
            )
            credentials = secret.content if secret else {}

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

    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently, only
                'rb' and 'wb' to read and write binary files are supported.

        Returns:
            A file-like object.
        """
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
