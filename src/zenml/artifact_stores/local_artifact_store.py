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

import os
from typing import TYPE_CHECKING, ClassVar, Optional, Set, Type, Union

from pydantic import field_validator

from zenml.artifact_stores import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.exceptions import ArtifactStoreInterfaceError
from zenml.io.local_filesystem import LocalFilesystem
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

    @field_validator("path")
    @classmethod
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

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True


class LocalArtifactStore(LocalFilesystem, BaseArtifactStore):
    """Artifact Store for local artifacts.

    All methods are inherited from the default `LocalFilesystem`.
    """

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

    @property
    def custom_cache_key(self) -> Optional[bytes]:
        """Custom cache key.

        The client ID is returned here to invalidate caching when using the same
        local artifact store on multiple client machines.

        Returns:
            Custom cache key.
        """
        return GlobalConfiguration().user_id.bytes


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
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/local.svg"

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
