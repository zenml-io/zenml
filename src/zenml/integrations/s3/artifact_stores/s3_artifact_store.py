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
"""Implementation of the S3 Artifact Store."""

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

import s3fs

from zenml.artifact_stores import BaseArtifactStore
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
)
from zenml.io.fileio import convert_to_str
from zenml.secret.schemas import AWSSecretSchema
from zenml.stack.authentication_mixin import AuthenticationMixin

PathType = Union[bytes, str]


class S3ArtifactStore(BaseArtifactStore, AuthenticationMixin):
    """Artifact Store for S3 based artifacts."""

    _filesystem: Optional[s3fs.S3FileSystem] = None

    @property
    def config(self) -> S3ArtifactStoreConfig:
        """Get the config of this artifact store.

        Returns:
            The config of this artifact store.
        """
        return cast(S3ArtifactStoreConfig, self._config)

    def get_credentials(
        self,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Gets authentication credentials.

        If an authentication secret is configured, the secret values are
        returned. Otherwise, we fall back to the plain text component
        attributes.

        Returns:
            Tuple (key, secret, token) of credentials used to authenticate with
            the S3 filesystem.

        Raises:
            RuntimeError: If the AWS connector behaves unexpectedly.
        """
        connector = self.get_connector()
        if connector:
            from botocore.client import BaseClient

            client = connector.connect()
            if not isinstance(client, BaseClient):
                raise RuntimeError(
                    f"Expected a botocore.client.BaseClient while trying to "
                    f"use the linked connector, but got {type(client)}."
                )
            credentials = client.credentials
            return (
                credentials.access_key,
                credentials.secret_key,
                credentials.token,
            )

        secret = self.get_typed_authentication_secret(
            expected_schema_type=AWSSecretSchema
        )
        if secret:
            return (
                secret.aws_access_key_id,
                secret.aws_secret_access_key,
                secret.aws_session_token,
            )
        else:
            return self.config.key, self.config.secret, self.config.token

    @property
    def filesystem(self) -> s3fs.S3FileSystem:
        """The s3 filesystem to access this artifact store.

        Returns:
            The s3 filesystem.
        """
        # Refresh the credentials also if the connector has expired
        if self._filesystem and not self.connector_has_expired():
            return self._filesystem

        key, secret, token = self.get_credentials()

        self._filesystem = s3fs.S3FileSystem(
            key=key,
            secret=secret,
            token=token,
            client_kwargs=self.config.client_kwargs,
            config_kwargs=self.config.config_kwargs,
            s3_additional_kwargs=self.config.s3_additional_kwargs,
        )
        return self._filesystem

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
        return [f"s3://{path}" for path in self.filesystem.glob(path=pattern)]

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
            A list of paths that are files in the given directory.
        """
        # remove s3 prefix if given, so we can remove the directory later as
        # this method is expected to only return filenames
        path = convert_to_str(path)
        if path.startswith("s3://"):
            path = path[5:]

        def _extract_basename(file_dict: Dict[str, Any]) -> str:
            """Extracts the basename from a file info dict returned by the S3 filesystem.

            Args:
                file_dict: A file info dict returned by the S3 filesystem.

            Returns:
                The basename of the file.
            """
            file_path = cast(str, file_dict["Key"])
            base_name = file_path[len(path) :]
            return base_name.lstrip("/")

        return [
            _extract_basename(dict_)
            for dict_ in self.filesystem.listdir(path=path)
            # s3fs.listdir also returns the root directory, so we filter
            # it out here
            if _extract_basename(dict_)
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
            path: The path to get stat info for.

        Returns:
            A dictionary containing the stat info.
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
        for directory, subdirectories, files in self.filesystem.walk(path=top):
            yield f"s3://{directory}", subdirectories, files
