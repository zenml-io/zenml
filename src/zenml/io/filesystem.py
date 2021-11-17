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
"""Interface for filesystem plugins."""

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from zenml.io.fileio_registry import default_fileio_registry

PathType = Union[bytes, str]


class NotFoundError(IOError):
    pass


class FileSystemMeta(type):
    """ Metaclass which is responsible for registering the defined filesystem
    in the default fileio registry."""

    def __new__(
            mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "FileSystemMeta":
        """ Creates the filesystem class and registers it"""
        cls = cast(Type["Filesystem"], super().__new__(mcs, name, bases, dct))
        if name != "Filesystem":
            assert cls.SUPPORTED_SCHEMES, (
                "You should specify a list of SUPPORTED_SCHEMES when creating "
                "a filesystem"
            )
            default_fileio_registry.register(cls)

        return cls


class Filesystem(metaclass=FileSystemMeta):
    """Abstract Filesystem class."""

    SUPPORTED_SCHEMES = []

    @staticmethod
    def open(name: PathType, mode: str = "r") -> Any:
        raise NotImplementedError()

    @staticmethod
    def copy(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        raise NotImplementedError()

    @staticmethod
    def exists(path: PathType) -> bool:
        raise NotImplementedError()

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        raise NotImplementedError()

    @staticmethod
    def isdir(path: PathType) -> bool:
        raise NotImplementedError()

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        raise NotImplementedError()

    @staticmethod
    def makedirs(path: PathType) -> None:
        raise NotImplementedError()

    @staticmethod
    def mkdir(path: PathType) -> None:
        raise NotImplementedError()

    @staticmethod
    def remove(path: PathType) -> None:
        raise NotImplementedError()

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        raise NotImplementedError()

    @staticmethod
    def rmtree(path: PathType) -> None:
        raise NotImplementedError()

    @staticmethod
    def stat(path: PathType) -> Any:
        raise NotImplementedError()

    @staticmethod
    def walk(
            top: PathType,
            topdown: bool = True,
            onerror: Optional[Callable[..., None]] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        raise NotImplementedError()
