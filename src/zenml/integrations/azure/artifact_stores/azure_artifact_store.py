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

from pydantic import validator

from zenml.artifact_stores import BaseArtifactStore
from zenml.enums import ArtifactStoreFlavor, StackComponentType
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)


@register_stack_component_class(
    component_type=StackComponentType.ARTIFACT_STORE,
    component_flavor=ArtifactStoreFlavor.AZURE,
)
class AzureArtifactStore(BaseArtifactStore):
    """Artifact Store for Microsoft Azure based artifacts."""

    supports_local_execution = True
    supports_remote_execution = True

    @property
    def flavor(self) -> ArtifactStoreFlavor:
        """The artifact store flavor."""
        return ArtifactStoreFlavor.AZURE

    @validator("path")
    def ensure_azure_path(cls, path: str) -> str:
        """Ensures that the path is a valid azure path."""
        path_prefixes = ["abfs://", "az://"]
        if not any(path.startswith(prefix) for prefix in path_prefixes):
            raise ValueError(
                f"Path '{path}' specified for AzureArtifactStore is not a "
                f"valid Azure Blob Storage path, i.e., starting with one of "
                f"{path_prefixes}."
            )
        return path
