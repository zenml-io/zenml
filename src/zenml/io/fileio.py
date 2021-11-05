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

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple, Type

from tfx.dsl.io.filesystem import Filesystem, PathType

from zenml.utils.path_utils import convert_to_str
from zenml.utils.source_utils import import_class_by_path

# TODO: [LOW] choose between is_dir vs isdir pattern (& standardize)


def _get_scheme(path: PathType) -> PathType:
    """Get filesystem plugin for given path."""
    # Assume local path by default, but extract filesystem prefix if available.
    if isinstance(path, str):
        path_bytes = path.encode("utf-8")
    elif isinstance(path, bytes):
        path_bytes = path
    else:
        raise ValueError("Invalid path type: %r." % path)
    result = re.match(b"^([a-z0-9]+://)", path_bytes)
    if result:
        return result.group(1).decode("utf-8")
    else:
        return ""


def _get_filesystem(path: PathType) -> Type[Filesystem]:
    """Returns a filesystem class for a given path."""
    scheme = _get_scheme(path)

    if scheme == "gs://":
        return import_class_by_path("zenml.io.gcs_plugin.ZenGCS")()  # type: ignore[no-any-return] # noqa
    elif scheme == "":
        return import_class_by_path(  # type: ignore[no-any-return] # noqa
            "tfx.dsl.io.plugins.local.LocalFilesystem"
        )()

    if isinstance(scheme, bytes):
        scheme = scheme.decode("utf-8")

    raise ValueError(
        f"No registered handler found for filesystem scheme `{scheme}`."
    )


def open(path: PathType, mode: str = "r") -> Any:  # noqa
    """Open a file at the given path."""
    return _get_filesystem(path).open(path, mode=mode)


def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
    """Copy a file from the source to the destination."""
    src_fs = _get_filesystem(src)
    dst_fs = _get_filesystem(dst)
    if src_fs is dst_fs:
        src_fs.copy(src, dst, overwrite=overwrite)
    else:
        if not overwrite and exists(dst):
            raise OSError(
                (
                    "Destination file %r already exists and argument `overwrite` is "
                    "false."
                )
                % dst
            )
        contents = open(src, mode="rb").read()
        open(dst, mode="wb").write(contents)


def exists(path: PathType) -> bool:
    """Return whether a path exists."""
    return _get_filesystem(path).exists(path)


def glob(pattern: PathType) -> List[PathType]:
    """Return the paths that match a glob pattern."""
    return _get_filesystem(pattern).glob(pattern)


def isdir(path: PathType) -> bool:
    # TODO: [Low] consider renaming to is_dir for standardization
    """Returns true if dir_path points to a dir.

    Args:
        dir_path: Local path in filesystem.

    Returns:
        True if is dir, else False.
    """
    return _get_filesystem(path).isdir(path)


def is_root(path: str) -> bool:
    """Returns true if path has no parent in local filesystem.

    Args:
        path: Local path in filesystem.

    Returns:
        True if root, else False.
    """
    return Path(path).parent == Path(path)


def listdir(path: PathType) -> List[PathType]:
    """Return the list of files in a directory."""
    return _get_filesystem(path).listdir(path)


def makedirs(path: PathType) -> None:
    """Make a directory at the given path, recursively creating parents."""
    _get_filesystem(path).makedirs(path)


def mkdir(path: PathType) -> None:
    """Make a directory at the given path; parent directory must exist."""
    _get_filesystem(path).mkdir(path)


def remove(path: PathType) -> None:
    """Remove the file at the given path."""
    _get_filesystem(path).remove(path)


def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
    """Rename a source file to a destination path."""
    src_fs = _get_filesystem(src)
    dst_fs = _get_filesystem(dst)
    if src_fs is dst_fs:
        src_fs.rename(src, dst, overwrite=overwrite)
    else:
        raise NotImplementedError(
            (
                "Rename from %r to %r using different filesystems plugins is "
                "currently not supported."
            )
            % (src, dst)
        )


def rmtree(path: PathType) -> None:
    """Remove the given directory and its recursive contents."""
    _get_filesystem(path).rmtree(path)


def stat(path: PathType) -> Any:
    """Return the stat descriptor for a given file path."""
    return _get_filesystem(path).stat(path)


def walk(
    top: PathType,
    topdown: bool = True,
    onerror: Optional[Callable[..., None]] = None,
) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
    """Walks down the dir_path.

    Args:
        dir_path: Path of dir to walk down.

    Returns:
        Iterable of tuples to walk down.
    """
    return _get_filesystem(top).walk(top, topdown=topdown, onerror=onerror)


def find_files(dir_path: PathType, pattern: str) -> Iterable[str]:
    # TODO [LOW]: correct docstring since 'None' is never returned
    """Find files in a directory that match pattern.

    Args:
        dir_path: Path to directory.
        pattern: pattern like *.png.

    Yields:
         All matching filenames if found, else None.
    """
    for root, dirs, files in walk(dir_path):
        for basename in files:
            if fnmatch.fnmatch(convert_to_str(basename), pattern):
                filename = os.path.join(
                    convert_to_str(root), convert_to_str(basename)
                )
                yield filename
