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
"""Artifact Config classes to support Model Control Plane feature."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from zenml.enums import ArtifactType
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.utils.pydantic_utils import before_validator_handler

logger = get_logger(__name__)


class ArtifactConfig(BaseModel):
    """Artifact configuration class.

    Can be used in step definitions to define various artifact properties.

    Example:
    ```python
    @step
    def my_step() -> Annotated[
        int, ArtifactConfig(
            name="my_artifact",  # override the default artifact name
            version=42,  # set a custom version
            artifact_type=ArtifactType.MODEL,  # Specify the artifact type
            tags=["tag1", "tag2"],  # set custom tags
        )
    ]:
        return ...
    ```

    Attributes:
        name: The name of the artifact:
            - static string e.g. "name"
            - dynamic string e.g. "name_{date}_{time}_{custom_placeholder}"
            If you use any placeholders besides `date` and `time`,
            you need to provide the values for them in the `substitutions`
            argument of the step decorator or the `substitutions` argument
            of `with_options` of the step.
        version: The version of the artifact.
        tags: The tags of the artifact.
        run_metadata: Metadata to add to the artifact.
        artifact_type: Optional type of the artifact. If not given, the type
            specified by the materializer that is used to save this artifact
            is used.
    """

    name: Optional[str] = None
    version: Optional[Union[str, int]] = Field(
        default=None, union_mode="smart"
    )
    tags: Optional[List[str]] = None
    run_metadata: Optional[Dict[str, MetadataType]] = None

    artifact_type: Optional[ArtifactType] = None

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_old_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove old attributes that are not used anymore.

        Args:
            data: The model data.

        Raises:
            ValueError: If the artifact is configured to be
                both a model and a deployment artifact.

        Returns:
            Model data without the removed attributes.
        """
        model_name = data.pop("model_name", None)
        model_version = data.pop("model_version", None)

        if model_name or model_version:
            logger.warning(
                "Specifying a model name or version for a step output "
                "artifact is not supported anymore."
            )

        is_model_artifact = data.pop("is_model_artifact", None)
        is_deployment_artifact = data.pop("is_deployment_artifact", None)

        if is_model_artifact and is_deployment_artifact:
            raise ValueError(
                "An artifact can only be a model artifact or deployment "
                "artifact."
            )
        elif is_model_artifact:
            logger.warning(
                "`ArtifactConfig(..., is_model_artifact=True)` is deprecated "
                "and will be removed soon. Use `ArtifactConfig(..., "
                "artifact_type=ArtifactType.MODEL)` instead. For more info: "
                "https://docs.zenml.io/user-guides/starter-guide/manage-artifacts"
            )
            data.setdefault("artifact_type", ArtifactType.MODEL)
        elif is_deployment_artifact:
            logger.warning(
                "`ArtifactConfig(..., is_deployment_artifact=True)` is "
                "deprecated and will be removed soon. Use `ArtifactConfig(..., "
                "artifact_type=ArtifactType.SERVICE)` instead. For more info: "
                "https://docs.zenml.io/user-guides/starter-guide/manage-artifacts"
            )
            data.setdefault("artifact_type", ArtifactType.SERVICE)

        return data
