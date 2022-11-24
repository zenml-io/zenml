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
#
# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Local filesystem using Python's built-in modules (`os`, `shutil`, `glob`)."""

import glob
import os
import shutil
from typing import Any, Callable, ClassVar, Iterable, List, Optional, Set, Tuple

from zenml.io.filesystem import BaseFilesystem, PathType
from zenml.io.filesystem_registry import default_filesystem_registry


class LocalFilesystem(BaseFilesystem):
    """Filesystem that uses local file operations.

    Implementation inspired by TFX:
    https://github.com/tensorflow/tfx/blob/master/tfx/dsl/io/plugins/local.py
    """

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {""}

    @staticmethod
    def open(name: PathType, mode: str = "r") -> Any:
        """Opens a file.

        Args:
            name: The path to the file.
            mode: The mode to open the file in.

        Returns:
            The opened file.
        """
        return open(name, mode=mode)

    @staticmethod
    def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Copy a file from the source to the destination.

        Args:
            src: The path of the file to copy.
            dst: The path to copy the source file to.
            overwrite: Whether to overwrite the destination file if it exists.

        Raises:
            FileExistsError: If a file already exists at the destination and
                `overwrite` is not set to `True`.
        """
        if not overwrite and os.path.exists(dst):
            raise FileExistsError(
                f"Destination file {str(dst)} already exists and argument "
                f"`overwrite` is set to False."
            )
        shutil.copyfile(src, dst)

    @staticmethod
    def exists(path: PathType) -> bool:
        """Check whether a given path exists.

        Args:
            path: The path to check.

        Returns:
            `True` if the given path exists, `False` otherwise.
        """
        return os.path.exists(path)

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        """Find all files matching the given pattern.

        Args:
            pattern: The pattern to match.

        Returns:
            A list of paths matching the pattern.
        """
        return glob.glob(pattern)

    @staticmethod
    def isdir(path: PathType) -> bool:
        """Check whether the given path is a directory.

        Args:
            path: The path to check.

        Returns:
            `True` if the given path is a directory, `False` otherwise.
        """
        return os.path.isdir(path)

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        """Lists all files in a directory.

        Args:
            path: The path to the directory.

        Returns:
            A list of files in the directory.
        """
        return os.listdir(path)

    @staticmethod
    def makedirs(path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents.

        Args:
            path: Path to the directory.
        """
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def mkdir(path: PathType) -> None:
        """Make a directory at the given path; parent directory must exist.

        Args:
            path: Path to the directory.
        """
        os.mkdir(path)

    @staticmethod
    def remove(path: PathType) -> None:
        """Remove the file at the given path. Dangerous operation.

        Args:
            path: The path to the file to remove.
        """
        os.remove(path)

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Rename a file.

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
        if not overwrite and os.path.exists(dst):
            raise FileExistsError(
                f"Destination file {str(dst)} already exists and argument "
                f"`overwrite` is set to False."
            )
        os.rename(src, dst)

    @staticmethod
    def rmtree(path: PathType) -> None:
        """Deletes a directory recursively. Dangerous operation.

        Args:
            path: The path to the directory to delete.
        """
        shutil.rmtree(path)

    @staticmethod
    def stat(path: PathType) -> Any:
        """Get the stat descriptor for a given file path.

        Args:
            path: The path to the file.

        Returns:
            The stat descriptor.
        """
        return os.stat(path)

    @staticmethod
    def walk(
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Return an iterator that walks the contents of the given directory.

        Args:
            top: The path of directory to walk.
            topdown: Whether to walk directories topdown or bottom-up.
            onerror: Callable that gets called if an error occurs.

        Yields:
            A tuple which contains the path of the current directory path, a
            list of directories inside the current directory, and a list of
            files inside the current directory.
        """
        yield from os.walk(top, topdown=topdown, onerror=onerror)


default_filesystem_registry.register(LocalFilesystem)
