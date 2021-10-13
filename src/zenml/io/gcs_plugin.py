#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

""" Plugin which is created to add Google Cloud Store support to ZenML

It inherits from the base Filesystem created by TFX and overwrites the
corresponding functions thanks to gcsfs.

Finally, the plugin is registered in the filesystem registry.
"""

from builtins import FileNotFoundError
from typing import Any, Callable, Iterable, List, Optional, Tuple

import gcsfs
from tfx.dsl.io import filesystem, filesystem_registry
from tfx.dsl.io.filesystem import PathType


class ZenGCS(filesystem.Filesystem):
    """Filesystem that delegates to Google Cloud Store using gcsfs."""

    SUPPORTED_SCHEMES = ["gs://"]

    fs = gcsfs.GCSFileSystem()

    @staticmethod
    def open(path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: Path of the file to open.
            mode: Mode in which to open the file. Currently only
                'rb' and 'wb' to read and write binary files are supported.
        """
        return ZenGCS.fs.open(path=path, mode=mode)

    @staticmethod
    def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
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
        if not overwrite and ZenGCS.fs.exists(dst):
            raise FileExistsError(
                f"Unable to copy to destination '{dst}', "
                f"file already exists. Set `overwrite=True`"
                f"to copy anyway."
            )

        # TODO: [LOW] check if it works with overwrite=True or if we need to manually
        #  remove it first
        ZenGCS.fs.copy(path1=src, path2=dst)

    @staticmethod
    def exists(path: PathType) -> bool:
        """Check whether a path exists."""
        return ZenGCS.fs.exists(path=path)

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        """Return all paths that match the given glob pattern.

        Args:
            pattern: The glob pattern to match, which may include
                - '*' to match any number of characters
                - '?' to match a single character
                - '[...]' to match one of the characters inside the brackets
                - '**' as the full name of a path component to match to search
                  in subdirectories of any depth (e.g. '/some_dir/**/some_file)
        """
        return ZenGCS.fs.glob(path=pattern)

    @staticmethod
    def isdir(path: PathType) -> bool:
        """Check whether a path is a directory."""
        return ZenGCS.fs.isdir(path=path)

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        """Return a list of files in a directory."""
        return ZenGCS.fs.listdir(path=path)

    @staticmethod
    def makedirs(path: PathType) -> None:
        """Create a directory at the given path. If needed also
        create missing parent directories."""
        ZenGCS.fs.makedirs(path=path, exist_ok=True)

    @staticmethod
    def mkdir(path: PathType) -> None:
        """Create a directory at the given path."""
        ZenGCS.fs.makedir(path=path)

    @staticmethod
    def remove(path: PathType) -> None:
        """Remove the file at the given path."""
        ZenGCS.fs.rm_file(path=path)

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
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
        if not overwrite and ZenGCS.fs.exists(dst):
            raise FileExistsError(
                f"Unable to rename file to '{dst}', "
                f"file already exists. Set `overwrite=True`"
                f"to rename anyway."
            )

        # TODO: [LOW] check if it works with overwrite=True or if we need
        #  to manually remove it first
        ZenGCS.fs.rename(path1=src, path2=dst)

    @staticmethod
    def rmtree(path: PathType) -> None:
        """Remove the given directory."""
        try:
            ZenGCS.fs.delete(path=path, recursive=True)
        except FileNotFoundError as e:
            raise filesystem.NotFoundError() from e

    @staticmethod
    def stat(path: PathType) -> Any:
        """Return stat info for the given path."""
        ZenGCS.fs.stat(path=path)

    @staticmethod
    def walk(
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory.

        Args:
            top: Path of directory to walk.
            topdown: Unused argument to conform to interface.
            onerror: Unused argument to conform to interface.
        """
        # TODO: [LOW] additional params
        return ZenGCS.fs.walk(path=top)


# TODO: [LOW] The registration of the filesystem should happen probably at an
#   artifact store basis
filesystem_registry.DEFAULT_FILESYSTEM_REGISTRY.register(ZenGCS, priority=15)
