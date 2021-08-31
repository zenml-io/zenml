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
from typing import Text
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.enums import ArtifactStoreTypes
from zenml.repo import GlobalConfig
from zenml.utils import path_utils


class BaseArtifactStore(BaseModel):
    """Base class for all ZenML Artifacts.

    Every ZenML Artifact Store should override this class.
    """

    path: str
    uuid: UUID = Field(default_factory=uuid4)
    store_type: ArtifactStoreTypes = ArtifactStoreTypes.local

    @staticmethod
    def get_component_name_from_uri(artifact_uri: Text) -> Text:
        """Gets component name from artifact URI.

        Args:
          artifact_uri: URI to artifact.

        Returns:
            Name of the component (str).
        """
        return path_utils.get_grandparent(artifact_uri)

    def resolve_uri_locally(
        self, artifact_uri: Text, path: Text = None
    ) -> Text:
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
                GlobalConfig.get_config_dir(),
                str(self.uuid),
                BaseArtifactStore.get_component_name_from_uri(artifact_uri),
                path_utils.get_parent(artifact_uri),  # unique ID from MLMD
            )

        # Create if not exists and download
        path_utils.create_dir_recursive_if_not_exists(path)
        path_utils.copy_dir(artifact_uri, path, overwrite=True)

        return path


class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    store_type: ArtifactStoreTypes = ArtifactStoreTypes.local


class GCPArtifactStore(BaseArtifactStore):
    """Artifact Store for Google Cloud Storage based artifacts."""

    store_type: ArtifactStoreTypes = ArtifactStoreTypes.gcp
