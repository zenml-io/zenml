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
"""The local artifact store is a local implementation of the artifact store.

In ZenML, the inputs and outputs which go through any step is treated as an
artifact and as its name suggests, an `ArtifactStore` is a place where these
artifacts get stored.
"""

import glob
import os
import shutil
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from pydantic import validator

from zenml.artifact_stores import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.utils import io_utils

if TYPE_CHECKING:
    from uuid import UUID

PathType = Union[bytes, str]


class LocalArtifactStoreConfig(BaseArtifactStoreConfig):
    """Config class for the local artifact store.

    Attributes:
        path: The path to the local artifact store.
    """

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {""}

    path: str = ""

    @validator("path")
    def ensure_path_local(cls, path: str) -> str:
        """Pydantic validator which ensures that the given path is a local path.

        Args:
            path: The path to validate.

        Returns:
            str: The validated (local) path.

        Raises:
            ArtifactStoreInterfaceError: If the given path is not a local path.
        """
        remote_prefixes = ["gs://", "hdfs://", "s3://", "az://", "abfs://"]
        if any(path.startswith(prefix) for prefix in remote_prefixes):
            raise ArtifactStoreInterfaceError(
                f"The path '{path}' you defined for your local artifact store "
                f"starts with a remote prefix."
            )
        return path

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        This designation is used to determine if the stack component can be
        shared with other users or if it is only usable on the local host.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True


class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    _path: Optional[str] = None

    @staticmethod
    def get_default_local_path(id_: "UUID") -> str:
        """Returns the default local path for a local artifact store.

        Args:
            id_: The id of the local artifact store.

        Returns:
            str: The default local path.
        """
        return os.path.join(
            GlobalConfiguration().local_stores_path,
            str(id_),
        )

    @property
    def path(self) -> str:
        """Returns the path to the local artifact store.

        If the user has not defined a path in the config, this will create a
        sub-folder in the global config directory.

        Returns:
            The path to the local artifact store.
        """
        if self._path:
            return self._path

        if self.config.path:
            self._path = self.config.path
        else:
            self._path = self.get_default_local_path(self.id)
        io_utils.create_dir_recursive_if_not_exists(self._path)
        return self._path

    @property
    def local_path(self) -> Optional[str]:
        """Returns the local path of the artifact store.

        Returns:
            The local path of the artifact store.
        """
        return self.path

    @staticmethod
    def open(name: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            name: The path to the file.
            mode: The mode to open the file.

        Returns:
            Any: The file object.
        """
        return open(name, mode=mode)

    @staticmethod
    def copyfile(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Copy a file from the source to the destination.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.

        Raises:
            FileExistsError: If the destination file exists and overwrite is
                False.
        """
        if not overwrite and os.path.exists(dst):
            raise FileExistsError(
                f"Destination file {str(dst)} already exists and argument "
                f"`overwrite` is false."
            )
        shutil.copyfile(src, dst)  # type: ignore[type-var, arg-type]

    @staticmethod
    def exists(path: PathType) -> bool:
        """Returns `True` if the given path exists.

        Args:
            path: The path to check.

        Returns:
            bool: Whether the path exists.
        """
        return os.path.exists(path)

    @staticmethod
    def glob(pattern: PathType) -> List[PathType]:
        """Return the paths that match a glob pattern.

        Args:
            pattern: The glob pattern.

        Returns:
            List[PathType]: The paths that match the glob pattern.
        """
        return glob.glob(pattern)  # type: ignore[type-var]

    @staticmethod
    def isdir(path: PathType) -> bool:
        """Returns whether the given path points to a directory.

        Args:
            path: The path to check.

        Returns:
            bool: Whether the path points to a directory.
        """
        return os.path.isdir(path)

    @staticmethod
    def listdir(path: PathType) -> List[PathType]:
        """Returns a list of files under a given directory in the filesystem.

        Args:
            path: The path to the directory.

        Returns:
            List[PathType]: The list of files under the given directory.
        """
        return os.listdir(path)  # type:ignore[return-value]

    @staticmethod
    def makedirs(path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents.

        Args:
            path: The path to the directory.
        """
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def mkdir(path: PathType) -> None:
        """Make a directory at the given path; parent directory must exist.

        Args:
            path: The path to the directory.
        """
        os.mkdir(path)

    @staticmethod
    def remove(path: PathType) -> None:
        """Remove the file at the given path. Dangerous operation.

        Args:
            path: The path to the file.
        """
        os.remove(path)

    @staticmethod
    def rename(src: PathType, dst: PathType, overwrite: bool = False) -> None:
        """Rename source file to destination file.

        Args:
            src: The path of the file to rename.
            dst: The path to rename the source file to.
            overwrite: If a file already exists at the destination, this
                method will overwrite it if overwrite=`True`

        Raises:
            FileExistsError: If the destination file exists and overwrite is
                False.
        """
        if not overwrite and os.path.exists(dst):
            raise FileExistsError(
                f"Destination path {str(dst)} already exists and argument "
                f"`overwrite` is false."
            )
        os.rename(src, dst)

    @staticmethod
    def rmtree(path: PathType) -> None:
        """Deletes dir recursively. Dangerous operation.

        Args:
            path: The path to the directory.
        """
        shutil.rmtree(path)

    @staticmethod
    def stat(path: PathType) -> Any:
        """Return the stat descriptor for a given file path.

        Args:
            path: The path to the file.

        Returns:
            Any: The stat descriptor for the file.
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
            top: Path of directory to walk.
            topdown: Whether to walk directories topdown or bottom-up.
            onerror: Callable that gets called if an error occurs.

        Yields:
            An Iterable of Tuples, each of which contain the path of the
            current directory path, a list of directories inside the
            current directory and a list of files inside the current
            directory.
        """
        yield from os.walk(  # type: ignore[type-var, misc]
            top, topdown=topdown, onerror=onerror
        )


class LocalArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Class for the `LocalArtifactStoreFlavor`."""

    @property
    def name(self) -> str:
        """Returns the name of the artifact store flavor.

        Returns:
            str: The name of the artifact store flavor.
        """
        return "local"

    @property
    def config_class(self) -> Type[LocalArtifactStoreConfig]:
        """Config class for this flavor.

        Returns:
            The config class.
        """
        return LocalArtifactStoreConfig

    @property
    def implementation_class(self) -> Type[LocalArtifactStore]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        return LocalArtifactStore
