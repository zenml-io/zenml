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
"""Various utility functions for the io module."""

import fnmatch
import os
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import click

from zenml.constants import APP_NAME, ENV_ZENML_CONFIG_PATH, REMOTE_FS_PREFIX
from zenml.io.fileio import (
    convert_to_str,
    copy,
    exists,
    isdir,
    listdir,
    makedirs,
    mkdir,
    open,
    rename,
    walk,
)

if TYPE_CHECKING:
    from zenml.io.filesystem import PathType


def is_root(path: str) -> bool:
    """Returns true if path has no parent in local filesystem.

    Args:
        path: Local path in filesystem.

    Returns:
        True if root, else False.
    """
    return Path(path).parent == Path(path)


def get_global_config_directory() -> str:
    """Gets the global config directory for ZenML.

    Returns:
        The global config directory for ZenML.
    """
    env_var_path = os.getenv(ENV_ZENML_CONFIG_PATH)
    if env_var_path:
        return str(Path(env_var_path).resolve())
    return click.get_app_dir(APP_NAME)


def write_file_contents_as_string(file_path: str, content: str) -> None:
    """Writes contents of file.

    Args:
        file_path: Path to file.
        content: Contents of file.

    Raises:
        ValueError: If content is not of type str.
    """
    if not isinstance(content, str):
        raise ValueError(f"Content must be of type str, got {type(content)}")
    with open(file_path, "w") as f:
        f.write(content)


def read_file_contents_as_string(file_path: str) -> str:
    """Reads contents of file.

    Args:
        file_path: Path to file.

    Returns:
        Contents of file.

    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist!")
    with open(file_path) as f:
        return f.read()  # type: ignore[no-any-return]


def copy_dir(
    source_dir: str, destination_dir: str, overwrite: bool = False
) -> None:
    """Copies dir from source to destination.

    Args:
        source_dir: Path to copy from.
        destination_dir: Path to copy to.
        overwrite: Boolean. If false, function throws an error before overwrite.
    """
    for source_file in listdir(source_dir):
        source_path = os.path.join(source_dir, convert_to_str(source_file))
        destination_path = os.path.join(
            destination_dir, convert_to_str(source_file)
        )
        if isdir(source_path):
            if source_path == destination_dir:
                # if the destination is a subdirectory of the source, we skip
                # copying it to avoid an infinite loop.
                continue
            copy_dir(source_path, destination_path, overwrite)
        else:
            create_dir_recursive_if_not_exists(
                os.path.dirname(destination_path)
            )
            copy(str(source_path), str(destination_path), overwrite)


def find_files(dir_path: "PathType", pattern: str) -> Iterable[str]:
    """Find files in a directory that match pattern.

    Args:
        dir_path: The path to directory.
        pattern: pattern like *.png.

    Yields:
        All matching filenames in the directory.
    """
    for root, _, files in walk(dir_path):
        for basename in files:
            if fnmatch.fnmatch(convert_to_str(basename), pattern):
                filename = os.path.join(
                    convert_to_str(root), convert_to_str(basename)
                )
                yield filename


def is_remote(path: str) -> bool:
    """Returns True if path exists remotely.

    Args:
        path: Any path as a string.

    Returns:
        True if remote path, else False.
    """
    return any(path.startswith(prefix) for prefix in REMOTE_FS_PREFIX)


def create_file_if_not_exists(
    file_path: str, file_contents: str = "{}"
) -> None:
    """Creates file if it does not exist.

    Args:
        file_path: Local path in filesystem.
        file_contents: Contents of file.
    """
    full_path = Path(file_path)
    if not exists(file_path):
        create_dir_recursive_if_not_exists(str(full_path.parent))
        with open(str(full_path), "w") as f:
            f.write(file_contents)


def create_dir_if_not_exists(dir_path: str) -> None:
    """Creates directory if it does not exist.

    Args:
        dir_path: Local path in filesystem.
    """
    if not isdir(dir_path):
        mkdir(dir_path)


def create_dir_recursive_if_not_exists(dir_path: str) -> None:
    """Creates directory recursively if it does not exist.

    Args:
        dir_path: Local path in filesystem.
    """
    if not isdir(dir_path):
        makedirs(dir_path)


def resolve_relative_path(path: str) -> str:
    """Takes relative path and resolves it absolutely.

    Args:
        path: Local path in filesystem.

    Returns:
        Resolved path.
    """
    if is_remote(path):
        return path
    return str(Path(path).resolve())


def is_path_within_directory(path: str, directory: str) -> bool:
    """Checks if a path is contained within a given directory.

    This utility function verifies that a path (absolute or relative) resolves
    to a location that is within the specified directory. This is useful for
    security checks such as preventing path traversal attacks when extracting
    archives (CVE-2007-4559) or whenever path containment needs to be verified.

    Args:
        path: The path to check (can be relative or absolute).
        directory: The directory that should contain the path.

    Returns:
        Boolean indicating whether the path is contained within the directory (True)
        or not (False).
    """
    # Convert to absolute path, ensuring it's normalized
    abs_path = os.path.abspath(os.path.join(directory, path))
    # Check if the path is within the target directory
    dir_abs = os.path.abspath(directory)
    return abs_path.startswith(dir_abs + os.sep) or abs_path == dir_abs


def move(source: str, destination: str, overwrite: bool = False) -> None:
    """Moves dir or file from source to destination. Can be used to rename.

    Args:
        source: Local path to copy from.
        destination: Local path to copy to.
        overwrite: boolean, if false, then throws an error before overwrite.
    """
    rename(source, destination, overwrite)


def get_grandparent(dir_path: str) -> str:
    """Get grandparent of dir.

    Args:
        dir_path: The path to directory.

    Returns:
        The input paths parents parent.

    Raises:
        ValueError: If dir_path does not exist.
    """
    if not os.path.exists(dir_path):
        raise ValueError(f"Path '{dir_path}' does not exist.")
    return Path(dir_path).parent.parent.stem


def get_parent(dir_path: str) -> str:
    """Get parent of dir.

    Args:
        dir_path: The path to directory.

    Returns:
        Parent (stem) of the dir as a string.

    Raises:
        ValueError: If dir_path does not exist.
    """
    if not os.path.exists(dir_path):
        raise ValueError(f"Path '{dir_path}' does not exist.")
    return Path(dir_path).parent.stem
