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
    def open(name: PathType, mode: str = "r") -> Any:
        """Open a file at the given path."""
        return ZenGCS.fs.open(path=name, mode=mode)

    @staticmethod
    def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Copy a file."""
        # TODO: additional params
        ZenGCS.fs.copy(path1=src, path2=dst)

    @staticmethod
    def exists(path: PathType) -> bool:
        """Check whether a path exists."""
        return ZenGCS.fs.exists(path=path)

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        """Return all paths that match the given glob pattern."""
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
        """Rename source file to destination file."""
        # TODO: additional params
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
        """Return an iterator that walks the contents of the given directory."""
        # TODO: additional params
        return ZenGCS.fs.walk(path=top)


# TODO: [LOW] The registration of the filesystem should happen probably at an
#   artifact store basis
filesystem_registry.DEFAULT_FILESYSTEM_REGISTRY.register(ZenGCS, priority=15)
