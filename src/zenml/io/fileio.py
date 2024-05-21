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
"""Functionality for reading, writing and managing files."""

import os
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type

# this import required for CI to get local filesystem
from zenml.io import local_filesystem  # noqa
from zenml.io.filesystem import BaseFilesystem, PathType
from zenml.io.filesystem_registry import default_filesystem_registry
from zenml.logger import get_logger

logger = get_logger(__name__)


def _get_filesystem(path: "PathType") -> Type["BaseFilesystem"]:
    """Returns a filesystem class for a given path from the registry.

    Args:
        path: The path to the file.

    Returns:
        The filesystem class.
    """
    return default_filesystem_registry.get_filesystem_for_path(path)


def convert_to_str(path: "PathType") -> str:
    """Converts a "PathType" to a str using UTF-8.

    Args:
        path: The path to convert.

    Returns:
        The path as a string.
    """
    if isinstance(path, str):
        return path
    else:
        return path.decode("utf-8")


def open(path: "PathType", mode: str = "r") -> Any:  # noqa
    """Opens a file.

    Args:
        path: The path to the file.
        mode: The mode to open the file in.

    Returns:
        The opened file.
    """
    return _get_filesystem(path).open(path, mode=mode)


def copy(src: "PathType", dst: "PathType", overwrite: bool = False) -> None:
    """Copy a file from the source to the destination.

    Args:
        src: The path of the file to copy.
        dst: The path to copy the source file to.
        overwrite: Whether to overwrite the destination file if it exists.

    Raises:
        FileExistsError: If a file already exists at the destination and
            `overwrite` is not set to `True`.
    """
    src_fs = _get_filesystem(src)
    dst_fs = _get_filesystem(dst)
    if src_fs is dst_fs:
        src_fs.copyfile(src, dst, overwrite=overwrite)
    else:
        if not overwrite and exists(dst):
            raise FileExistsError(
                f"Destination file '{convert_to_str(dst)}' already exists "
                f"and `overwrite` is false."
            )
        with open(src, mode="rb") as f:
            contents = f.read()

        with open(dst, mode="wb") as f:
            f.write(contents)


def exists(path: "PathType") -> bool:
    """Check whether a given path exists.

    Args:
        path: The path to check.

    Returns:
        `True` if the given path exists, `False` otherwise.
    """
    return _get_filesystem(path).exists(path)


def glob(pattern: "PathType") -> List["PathType"]:
    """Find all files matching the given pattern.

    Args:
        pattern: The pattern to match.

    Returns:
        A list of paths matching the pattern.
    """
    return _get_filesystem(pattern).glob(pattern)


def isdir(path: "PathType") -> bool:
    """Check whether the given path is a directory.

    Args:
        path: The path to check.

    Returns:
        `True` if the given path is a directory, `False` otherwise.
    """
    return _get_filesystem(path).isdir(path)


def listdir(path: str, only_file_names: bool = True) -> List[str]:
    """Lists all files in a directory.

    Args:
        path: The path to the directory.
        only_file_names: If True, only return the file names, not the full path.

    Returns:
        A list of files in the directory.
    """
    try:
        return [
            os.path.join(path, convert_to_str(f))
            if not only_file_names
            else convert_to_str(f)
            for f in _get_filesystem(path).listdir(path)
        ]
    except IOError:
        logger.debug(f"Dir {path} not found.")
        return []


def makedirs(path: "PathType") -> None:
    """Make a directory at the given path, recursively creating parents.

    Args:
        path: The path to the directory.
    """
    _get_filesystem(path).makedirs(path)


def mkdir(path: "PathType") -> None:
    """Make a directory at the given path; parent directory must exist.

    Args:
        path: The path to the directory.
    """
    _get_filesystem(path).mkdir(path)


def remove(path: "PathType") -> None:
    """Remove the file at the given path. Dangerous operation.

    Args:
        path: The path to the file to remove.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not exists(path):
        raise FileNotFoundError(f"{convert_to_str(path)} does not exist!")
    _get_filesystem(path).remove(path)


def rename(src: "PathType", dst: "PathType", overwrite: bool = False) -> None:
    """Rename a file.

    Args:
        src: The path of the file to rename.
        dst: The path to rename the source file to.
        overwrite: If a file already exists at the destination, this
            method will overwrite it if overwrite=`True` and
            raise a FileExistsError otherwise.

    Raises:
        NotImplementedError: If the source and destination file systems are not
            the same.
    """
    src_fs = _get_filesystem(src)
    dst_fs = _get_filesystem(dst)
    if src_fs is dst_fs:
        src_fs.rename(src, dst, overwrite=overwrite)
    else:
        raise NotImplementedError(
            f"Renaming from {convert_to_str(src)} to {convert_to_str(dst)} "
            f"using different file systems plugins is currently not supported."
        )


def rmtree(dir_path: str) -> None:
    """Deletes a directory recursively. Dangerous operation.

    Args:
        dir_path: The path to the directory to delete.

    Raises:
        TypeError: If the path is not pointing to a directory.
    """
    if not isdir(dir_path):
        raise TypeError(f"Path '{dir_path}' is not a directory.")

    _get_filesystem(dir_path).rmtree(dir_path)


def stat(path: "PathType") -> Any:
    """Get the stat descriptor for a given file path.

    Args:
        path: The path to the file.

    Returns:
        The stat descriptor.
    """
    return _get_filesystem(path).stat(path)


def size(path: "PathType") -> Optional[int]:
    """Get the size of a file or directory in bytes.

    Args:
        path: The path to the file.

    Returns:
        The size of the file or directory in bytes or `None` if the responsible
        file system does not implement the `size` method.
    """
    file_system = _get_filesystem(path)

    # If the file system does not implement the `size` method, return `None`.
    if file_system.size == BaseFilesystem.size:
        logger.warning(
            "Cannot get size of file or directory '%s' since the responsible "
            "file system `%s` does not implement the `size` method.",
            path,
            file_system.__name__,
        )
        return None

    # If the path does not exist, return 0.
    if not exists(path):
        return 0

    # If the path is a file, return its size.
    if not file_system.isdir(path):
        return file_system.size(path)

    # If the path is a directory, recursively sum the sizes of everything in it.
    files = file_system.listdir(path)
    file_sizes = [size(os.path.join(str(path), str(file))) for file in files]
    return sum(
        [file_size for file_size in file_sizes if file_size is not None]
    )


def walk(
    top: "PathType",
    topdown: bool = True,
    onerror: Optional[Callable[..., None]] = None,
) -> Iterable[Tuple["PathType", List["PathType"], List["PathType"]]]:
    """Return an iterator that walks the contents of the given directory.

    Args:
        top: The path of directory to walk.
        topdown: Whether to walk directories topdown or bottom-up.
        onerror: Callable that gets called if an error occurs.

    Returns:
        An Iterable of Tuples, each of which contain the path of the current
        directory path, a list of directories inside the current directory
        and a list of files inside the current directory.
    """
    return _get_filesystem(top).walk(top, topdown=topdown, onerror=onerror)


__all__ = [
    "copy",
    "exists",
    "glob",
    "isdir",
    "listdir",
    "makedirs",
    "mkdir",
    "open",
    "remove",
    "rename",
    "rmtree",
    "size",
    "stat",
    "walk",
]
