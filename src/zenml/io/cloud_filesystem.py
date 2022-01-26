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
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from fsspec.asyn import AsyncFileSystem
from tfx.dsl.io.fileio import NotFoundError

from zenml.io.fileio import convert_to_str
from zenml.io.filesystem import Filesystem, PathType


class CloudFilesystem(Filesystem):
    """Abstract cloud filesystem that delegates to fsspec async filesystems.

    **Note**: To allow TFX to check for various error conditions, we need to
    raise their custom `NotFoundError` instead of the builtin python
    FileNotFoundError."""

    SUPPORTED_SCHEMES: List[str] = []
    fs: AsyncFileSystem

    @classmethod
    def _ensure_filesystem_set(cls) -> None:
        """Ensures that the filesystem is set."""
        raise NotImplementedError()

    @classmethod
    def open(cls, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.
        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently only
                'rb' and 'wb' to read and write binary files are supported.
        """
        cls._ensure_filesystem_set()

        try:
            return cls.fs.open(path=path, mode=mode)
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def copy(
        cls, src: PathType, dst: PathType, overwrite: bool = False
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
        cls._ensure_filesystem_set()
        if not overwrite and cls.fs.exists(dst):
            raise FileExistsError(
                f"Unable to copy to destination '{convert_to_str(dst)}', "
                f"file already exists. Set `overwrite=True` to copy anyway."
            )

        # TODO [ENG-151]: Check if it works with overwrite=True or if we need to
        #  manually remove it first
        try:
            cls.fs.copy(path1=src, path2=dst)
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def exists(cls, path: PathType) -> bool:
        """Check whether a path exists."""
        cls._ensure_filesystem_set()
        return cls.fs.exists(path=path)  # type: ignore[no-any-return]

    @classmethod
    def glob(cls, pattern: PathType) -> List[PathType]:
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
        cls._ensure_filesystem_set()
        return cls.fs.glob(path=pattern)  # type: ignore[no-any-return]

    @classmethod
    def isdir(cls, path: PathType) -> bool:
        """Check whether a path is a directory."""
        cls._ensure_filesystem_set()
        return cls.fs.isdir(path=path)  # type: ignore[no-any-return]

    @classmethod
    def listdir(cls, path: PathType) -> List[PathType]:
        """Return a list of files in a directory."""
        cls._ensure_filesystem_set()
        try:
            return cls.fs.listdir(path=path)  # type: ignore[no-any-return]
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def makedirs(cls, path: PathType) -> None:
        """Create a directory at the given path. If needed also
        create missing parent directories."""
        cls._ensure_filesystem_set()
        cls.fs.makedirs(path=path, exist_ok=True)

    @classmethod
    def mkdir(cls, path: PathType) -> None:
        """Create a directory at the given path."""
        cls._ensure_filesystem_set()
        cls.fs.makedir(path=path)

    @classmethod
    def remove(cls, path: PathType) -> None:
        """Remove the file at the given path."""
        cls._ensure_filesystem_set()
        try:
            cls.fs.rm_file(path=path)
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def rename(
        cls, src: PathType, dst: PathType, overwrite: bool = False
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
        cls._ensure_filesystem_set()
        if not overwrite and cls.fs.exists(dst):
            raise FileExistsError(
                f"Unable to rename file to '{convert_to_str(dst)}', "
                f"file already exists. Set `overwrite=True` to rename anyway."
            )

        # TODO [ENG-152]: Check if it works with overwrite=True or if we need
        #  to manually remove it first
        try:
            cls.fs.rename(path1=src, path2=dst)
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def rmtree(cls, path: PathType) -> None:
        """Remove the given directory."""
        cls._ensure_filesystem_set()
        try:
            cls.fs.delete(path=path, recursive=True)
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def stat(cls, path: PathType) -> Dict[str, Any]:
        """Return stat info for the given path."""
        cls._ensure_filesystem_set()
        try:
            return cls.fs.stat(path=path)  # type: ignore[no-any-return]
        except FileNotFoundError as e:
            raise NotFoundError() from e

    @classmethod
    def walk(
        cls,
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
        cls._ensure_filesystem_set()
        # TODO [ENG-153]: Additional params
        return cls.fs.walk(path=top)  # type: ignore[no-any-return]
