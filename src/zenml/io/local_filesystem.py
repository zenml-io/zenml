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
"""Local filesystem-based filesystem plugin."""

import glob
import os
import shutil
from typing import Any, Callable, ClassVar, Iterable, List, Optional, Set, Tuple

from zenml.io.filesystem import Filesystem, PathType
from zenml.io.filesystem_registry import default_filesystem_registry


class LocalFilesystem(Filesystem):
    """Filesystem that uses local file operations.

    Implemention inspired by TFX:
    https://github.com/tensorflow/tfx/blob/master/tfx/dsl/io/plugins/local.py
    """

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {""}

    @staticmethod
    def open(name: PathType, mode: str = "r") -> Any:
        return open(name, mode=mode)

    @staticmethod
    def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        if not overwrite and os.path.exists(dst):
            raise OSError(
                (
                    "Destination file %r already exists and argument `overwrite` is "
                    "false."
                )
                % dst
            )
        shutil.copyfile(src, dst)

    @staticmethod
    def exists(path: PathType) -> bool:
        return os.path.exists(path)

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        return glob.glob(pattern)

    @staticmethod
    def isdir(path: PathType) -> bool:
        return os.path.isdir(path)

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        return os.listdir(path)

    @staticmethod
    def makedirs(path: PathType) -> None:
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def mkdir(path: PathType) -> None:
        os.mkdir(path)

    @staticmethod
    def remove(path: PathType) -> None:
        os.remove(path)

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        if not overwrite and os.path.exists(dst):
            raise OSError(
                (
                    "Destination path %r already exists and argument `overwrite` is "
                    "false."
                )
                % dst
            )
        os.rename(src, dst)

    @staticmethod
    def rmtree(path: PathType) -> None:
        shutil.rmtree(path)

    @staticmethod
    def stat(path: PathType) -> Any:
        return os.stat(path)

    @staticmethod
    def walk(
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        yield from os.walk(top, topdown=topdown, onerror=onerror)


default_filesystem_registry.register(LocalFilesystem)
