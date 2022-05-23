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


import json
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

import s3fs
from pydantic import validator

from zenml.artifact_stores import BaseArtifactStore
from zenml.integrations.s3 import S3_ARTIFACT_STORE_FLAVOR
from zenml.io.utils import convert_to_str

PathType = Union[bytes, str]


class S3ArtifactStore(BaseArtifactStore):
    """Artifact Store for S3 based artifacts.

    All attributes of this class except `path` will be passed to the
    `s3fs.S3FileSystem` initialization. See
    [here](https://s3fs.readthedocs.io/en/latest/) for more information on how
    to use those configuration options to connect to any S3-compatible storage.

    When you want to register an S3ArtifactStore from the CLI and need to pass
    `client_kwargs`, `config_kwargs` or `s3_additional_kwargs`, you should pass
    them as a json string:
    ```
    zenml artifact-store register my_s3_store --type=s3 --path=s3://my_bucket \
    --client_kwargs='{"endpoint_url": "http://my-s3-endpoint"}'
    ```
    """

    key: Optional[str] = None
    secret: Optional[str] = None
    token: Optional[str] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    config_kwargs: Optional[Dict[str, Any]] = None
    s3_additional_kwargs: Optional[Dict[str, Any]] = None
    _filesystem: Optional[s3fs.S3FileSystem] = None

    # Class variables
    FLAVOR: ClassVar[str] = S3_ARTIFACT_STORE_FLAVOR
    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"s3://"}

    @validator(
        "client_kwargs", "config_kwargs", "s3_additional_kwargs", pre=True
    )
    def _convert_json_string(
        cls, value: Union[None, str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Converts potential JSON strings passed via the CLI to
        dictionaries.

        Raises:
            TypeError: If the value is not a `str`, `Dict` or `None`.
            ValueError: If the value is an invalid json string or a json string
                that does not decode into a dictionary.
        """
        if isinstance(value, str):
            try:
                dict_ = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid json string '{value}'") from e

            if not isinstance(dict_, Dict):
                raise ValueError(
                    f"Json string '{value}' did not decode into a dictionary."
                )

            return dict_
        elif isinstance(value, Dict) or value is None:
            return value
        else:
            raise TypeError(f"{value} is not a json string or a dictionary.")

    @property
    def filesystem(self) -> s3fs.S3FileSystem:
        """The s3 filesystem to access this artifact store."""
        if not self._filesystem:
            self._filesystem = s3fs.S3FileSystem(
                key=self.key,
                secret=self.secret,
                token=self.token,
                client_kwargs=self.client_kwargs,
                config_kwargs=self.config_kwargs,
                s3_additional_kwargs=self.s3_additional_kwargs,
            )
        return self._filesystem

    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.
        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently, only
                'rb' and 'wb' to read and write binary files are supported.
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
            FileNotFoundError: If the source file does not exist.
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
        """Check whether a path exists."""
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
        """Check whether a path is a directory."""
        return self.filesystem.isdir(path=path)  # type: ignore[no-any-return]

    def listdir(self, path: PathType) -> List[PathType]:
        """Return a list of files in a directory."""
        # remove s3 prefix if given, so we can remove the directory later as
        # this method is expected to only return filenames
        path = convert_to_str(path)
        if path.startswith("s3://"):
            path = path[5:]

        def _extract_basename(file_dict: Dict[str, Any]) -> str:
            """Extracts the basename from a file info dict returned by the S3
            filesystem."""
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
        """Create a directory at the given path. If needed also
        create missing parent directories."""
        self.filesystem.makedirs(path=path, exist_ok=True)

    def mkdir(self, path: PathType) -> None:
        """Create a directory at the given path."""
        self.filesystem.makedir(path=path)

    def remove(self, path: PathType) -> None:
        """Remove the file at the given path."""
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
            FileNotFoundError: If the source file does not exist.
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
        """Remove the given directory."""
        self.filesystem.delete(path=path, recursive=True)

    def stat(self, path: PathType) -> Dict[str, Any]:
        """Return stat info for the given path."""
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
        Returns:
            An Iterable of Tuples, each of which contain the path of the current
            directory path, a list of directories inside the current directory
            and a list of files inside the current directory.
        """
        # TODO [ENG-153]: Additional params
        for directory, subdirectories, files in self.filesystem.walk(path=top):
            yield f"s3://{directory}", subdirectories, files
