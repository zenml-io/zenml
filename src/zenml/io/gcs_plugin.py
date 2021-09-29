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
    SUPPORTED_SCHEMES = ["gs://"]

    fs = gcsfs.GCSFileSystem()

    @staticmethod
    def open(name: PathType, mode: str = "r") -> Any:
        return ZenGCS.fs.open(path=name, mode=mode)

    @staticmethod
    def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        # TODO: additional params
        ZenGCS.fs.copy(path1=src, path2=dst)

    @staticmethod
    def exists(path: PathType) -> bool:
        return ZenGCS.fs.exists(path=path)

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        return ZenGCS.fs.glob(path=pattern)

    @staticmethod
    def isdir(path: PathType) -> bool:
        return ZenGCS.fs.isdir(path=path)

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        return ZenGCS.fs.listdir(path=path)

    @staticmethod
    def makedirs(path: PathType) -> None:
        ZenGCS.fs.makedirs(path=path, exist_ok=True)

    @staticmethod
    def mkdir(path: PathType) -> None:
        ZenGCS.fs.makedir(path=path)

    @staticmethod
    def remove(path: PathType) -> None:
        ZenGCS.fs.rm_file(path=path)

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        # TODO: additional params
        ZenGCS.fs.rename(path1=src, path2=dst)

    @staticmethod
    def rmtree(path: PathType) -> None:
        try:
            ZenGCS.fs.delete(path=path, recursive=True)
        except FileNotFoundError as e:
            raise filesystem.NotFoundError() from e

    @staticmethod
    def stat(path: PathType) -> Any:
        ZenGCS.fs.stat(path=path)

    @staticmethod
    def walk(
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        # TODO: additional params
        return ZenGCS.fs.walk(path=top)


# TODO: [LOW] The registration of the filesystem should happen probably at an
#   artifact store basis
filesystem_registry.DEFAULT_FILESYSTEM_REGISTRY.register(ZenGCS, priority=15)
