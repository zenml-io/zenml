#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Data Lazy Loader definition."""

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from zenml.model.model_version import ModelVersion

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType
    from zenml.models import ArtifactVersionResponse


class DataLazyLoader(BaseModel):
    """Data Lazy Loader helper class.

    It helps the inner codes to fetch proper artifact,
    model version metadata or artifact metadata from the
    model version or directly from client during the
    runtime time of the step.
    """

    model_version: Optional[ModelVersion] = None
    artifact_name: Optional[str] = None
    artifact_version: Optional[str] = None
    metadata_name: Optional[str] = None

    def _get_artifact_or_none(
        self, ignore_metadata_name: bool = False
    ) -> Optional["ArtifactVersionResponse"]:
        """Get the artifact version from the model version or directly from client.

        Args:
            ignore_metadata_name: Whether to ignore the metadata name setting.

        Returns:
            The artifact version from the model version or directly from client.
            `None` if the artifact is not found.
        """
        from zenml.client import Client

        if (
            self.metadata_name is None or ignore_metadata_name
        ) and self.artifact_name:
            if self.model_version:
                return self.model_version.get_artifact(
                    name=self.artifact_name, version=self.artifact_version
                )
            else:
                return Client().get_artifact_version(
                    name_id_or_prefix=self.artifact_name,
                    version=self.artifact_version,
                )
        return None

    def _get_run_metadata_or_none(self) -> Optional["MetadataType"]:
        """Get the run metadata from the model version or directly from client.

        Returns:
            The run metadata from the model version or directly from client.
            `None` if the metadata is not found.
        """
        if self.artifact_name is None and self.metadata_name:
            if self.model_version:
                return self.model_version.run_metadata[
                    self.metadata_name
                ].value
        elif self.artifact_name and self.metadata_name:
            if artifact_ := self._get_artifact_or_none(
                ignore_metadata_name=True
            ):
                return artifact_.run_metadata[self.metadata_name].value
        return None
