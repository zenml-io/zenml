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
"""Definition of an Artifact Store"""

import os

from zenml.config.global_config import GlobalConfig
from zenml.core.base_component import BaseComponent
from zenml.core.component_factory import artifact_store_factory
from zenml.enums import ArtifactStoreTypes
from zenml.utils import path_utils
from zenml.utils.path_utils import get_zenml_config_dir


@artifact_store_factory.register(ArtifactStoreTypes.base)
class BaseArtifactStore(BaseComponent):
    """Base class for all ZenML Artifact Store.

    Every ZenML Artifact Store should override this class.
    """

    path: str
    _ARTIFACT_STORE_DIR_NAME: str = "artifact_stores"

    @staticmethod
    def get_component_name_from_uri(artifact_uri: str) -> str:
        """Gets component name from artifact URI.

        Args:
          artifact_uri: URI to artifact.

        Returns:
            Name of the component (str).
        """
        return path_utils.get_grandparent(artifact_uri)

    def get_serialization_dir(self):
        """Gets the local path where artifacts are stored."""
        return os.path.join(
            get_zenml_config_dir(), self._ARTIFACT_STORE_DIR_NAME
        )

    def resolve_uri_locally(self, artifact_uri: str, path: str = None) -> str:
        """Takes a URI that points within the artifact store, downloads the
        URI locally, then returns local URI.

        Args:
          artifact_uri: uri to artifact.
          path: optional path to download to. If None, is inferred.

        Returns:
            Locally resolved uri (str).
        """
        if not path_utils.is_remote(artifact_uri):
            # Its already local
            return artifact_uri

        if path is None:
            # Create a unique path in local machine
            path = os.path.join(
                GlobalConfig().get_serialization_dir(),
                str(self.uuid),
                BaseArtifactStore.get_component_name_from_uri(artifact_uri),
                path_utils.get_parent(artifact_uri),  # unique ID from MLMD
            )

        # Create if not exists and download
        path_utils.create_dir_recursive_if_not_exists(path)
        path_utils.copy_dir(artifact_uri, path, overwrite=True)

        return path

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_artifact_store_"
