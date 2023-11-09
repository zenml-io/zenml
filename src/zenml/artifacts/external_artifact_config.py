#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""External artifact definition."""
from typing import TYPE_CHECKING, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel

from zenml.config.source import Source
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

MaterializerClassOrSource = Union[str, Source, Type[BaseMaterializer]]

if TYPE_CHECKING:
    from zenml.models.artifact_models import ArtifactResponseModel


logger = get_logger(__name__)


class ExternalArtifactConfiguration(BaseModel):
    """External artifact configuration.

    Lightweight class to pass in the steps for runtime inference.
    """

    id: Optional[UUID] = None
    name: Optional[str] = None
    version: Optional[str] = None
    pipeline_run_name: Optional[str] = None
    pipeline_name: Optional[str] = None

    def _get_artifact_from_pipeline_run(self) -> "ArtifactResponseModel":
        """Get artifact from pipeline run.

        Returns:
            The fetched Artifact.

        Raises:
            RuntimeError: If neither pipeline run name nor pipeline name
                were provided.
            RuntimeError: If the artifact was not found.
        """
        from zenml.client import Client

        client = Client()

        if self.pipeline_run_name:
            pipeline_run = client.get_pipeline_run(self.pipeline_run_name)
        elif self.pipeline_name:
            pipeline = client.get_pipeline(self.pipeline_name)
            pipeline_run = pipeline.last_successful_run
        else:
            raise RuntimeError(
                "Either the pipeline run name or the pipeline name must be "
                "provided to fetch an artifact from a pipeline run."
            )

        for artifact in pipeline_run.artifacts:
            if artifact.name == self.name:
                return artifact

        raise RuntimeError(
            f"Artifact with name `{self.name}` was not found in pipeline run "
            f"{pipeline_run.name}`. "
        )

    def get_artifact_id(self) -> UUID:
        """Get the artifact.

        Returns:
            The artifact ID.

        Raises:
            RuntimeError: If the artifact store of the referenced artifact
                is not the same as the one in the active stack.
            RuntimeError: If neither the ID nor the name of the artifact was
                provided.
        """
        from zenml.client import Client

        client = Client()

        if self.id:
            response = client.get_artifact(self.id)
        elif self.name:
            if self.version:
                response = client.get_artifact(self.name, version=self.version)
            elif self.pipeline_run_name or self.pipeline_name:
                response = self._get_artifact_from_pipeline_run()
            else:
                response = client.get_artifact(self.name)
        else:
            raise RuntimeError(
                "Either the ID or name of the artifact must be provided. "
                "If you created this ExternalArtifact from a value, please "
                "ensure that `upload_by_value` was called before trying to "
                "fetch the artifact ID."
            )

        artifact_store_id = client.active_stack.artifact_store.id
        if response.artifact_store_id != artifact_store_id:
            raise RuntimeError(
                f"The artifact {response.name} (ID: {response.id}) "
                "referenced by an external artifact is not stored in the "
                "artifact store of the active stack. This will lead to "
                "issues loading the artifact. Please make sure to only "
                "reference artifacts stored in your active artifact store."
            )

        self.id = response.id

        return self.id
