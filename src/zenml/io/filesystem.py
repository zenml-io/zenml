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
from typing import Any, Dict, Tuple, Type, Union, cast

from tfx.dsl.io.filesystem import Filesystem as BaseFileSystem

from zenml.io.fileio_registry import default_fileio_registry

PathType = Union[bytes, str]


class NotFoundError(IOError):
    """Auxiliary not found error"""


class FileSystemMeta(type):
    """Metaclass which is responsible for registering the defined filesystem
    in the default fileio registry."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "FileSystemMeta":
        """Creates the filesystem class and registers it"""
        cls = cast(Type["Filesystem"], super().__new__(mcs, name, bases, dct))
        if name != "Filesystem":
            assert cls.SUPPORTED_SCHEMES, (
                "You should specify a list of SUPPORTED_SCHEMES when creating "
                "a filesystem"
            )
            default_fileio_registry.register(cls)

        return cls


class Filesystem(BaseFileSystem, metaclass=FileSystemMeta):
    """Abstract Filesystem class."""
