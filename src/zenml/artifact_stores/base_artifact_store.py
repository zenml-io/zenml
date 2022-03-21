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
#
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

from abc import ABC
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from pydantic import root_validator
from tfx.dsl.io.fileio import NotFoundError

from zenml.enums import StackComponentType
from zenml.stack import StackComponent

PathType = Union[bytes, str]


def _catch_not_found_error(_func: Callable):
    def inner_function(*args, **kwargs):
        try:
            return _func(*args, **kwargs)
        except FileNotFoundError as e:
            raise NotFoundError() from e

    return inner_function


class BaseArtifactStore(StackComponent, ABC):
    """Base class for all ZenML artifact stores.

    Attributes:
        path: The root path of the artifact store.
    """

    # Instance attributes
    path: str

    # Class attributes
    TYPE: ClassVar[StackComponentType] = StackComponentType.ARTIFACT_STORE
    FLAVOR: ClassVar[str]
    SUPPORTED_SCHEMES: ClassVar[Set[str]]

    def __init__(self, *args, **kwargs):
        # Initiate the pydantic object and register the corresponding filesystem
        super(BaseArtifactStore, self).__init__(*args, **kwargs)
        self._register()

    @staticmethod
    def open(name: PathType, mode: str = "r") -> Any:
        raise NotImplementedError()

    @staticmethod
    def copyfile(src: PathType, dst: PathType, overwrite: bool = False) -> None:
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

    @root_validator
    def _ensure_complete(cls, values) -> Any:
        try:
            getattr(cls, "FLAVOR")
        except AttributeError:
            print("Please set a FLAVOR for your artifact store.")

        try:
            getattr(cls, "SUPPORTED_SCHEMES")
        except AttributeError:
            print(
                "Please set a list of SUPPORTED_SCHEMES for your artifact "
                "store."
            )

        return values

    def _register(self, priority: int = 5) -> None:
        """create"""
        from tfx.dsl.io.filesystem import Filesystem
        from tfx.dsl.io.filesystem_registry import DEFAULT_FILESYSTEM_REGISTRY

        filesystem_class = type(
            self.__class__.__name__,
            (Filesystem,),
            {
                "SUPPORTED_SCHEMES": self.SUPPORTED_SCHEMES,
                "open": staticmethod(_catch_not_found_error(self.open)),
                "copy": staticmethod(_catch_not_found_error(self.copyfile)),
                "exists": staticmethod(self.exists),
                "glob": staticmethod(self.glob),
                "isdir": staticmethod(self.isdir),
                "listdir": staticmethod(_catch_not_found_error(self.listdir)),
                "makedirs": staticmethod(self.makedirs),
                "mkdir": staticmethod(_catch_not_found_error(self.mkdir)),
                "remove": staticmethod(_catch_not_found_error(self.remove)),
                "rename": staticmethod(_catch_not_found_error(self.rename)),
                "rmtree": staticmethod(_catch_not_found_error(self.rmtree)),
                "stat": staticmethod(_catch_not_found_error(self.stat)),
                "walk": staticmethod(_catch_not_found_error(self.walk)),
            },
        )

        DEFAULT_FILESYSTEM_REGISTRY.register(
            filesystem_class, priority=priority
        )
