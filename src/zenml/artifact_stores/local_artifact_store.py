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

from pydantic import validator

from zenml.artifact_stores import BaseArtifactStore
from zenml.enums import ArtifactStoreFlavor
from zenml.io import fileio


class LocalArtifactStore(BaseArtifactStore):
    """Artifact Store for local artifacts."""

    supports_local_execution = True
    supports_remote_execution = False

    @property
    def flavor(self) -> ArtifactStoreFlavor:
        """The artifact store flavor."""
        return ArtifactStoreFlavor.LOCAL

    @validator("path")
    def ensure_path_is_local(cls, path: str) -> str:
        """Ensures that the artifact store path is local."""
        if fileio.is_remote(path):
            raise ValueError(
                f"Path '{path}' specified for LocalArtifactStore is not a "
                f"local path."
            )
        return path
