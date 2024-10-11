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

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    pass


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
            tags=["tag1", "tag2"],  # set custom tags
        )
    ]:
        return ...
    ```

    Attributes:
        name: The name of the artifact.
        version: The version of the artifact.
        tags: The tags of the artifact.
        run_metadata: Metadata to add to the artifact.
        is_model_artifact: Whether the artifact is a model artifact.
        is_deployment_artifact: Whether the artifact is a deployment artifact.
    """

    name: Optional[str] = None
    version: Optional[Union[str, int]] = Field(
        default=None, union_mode="smart"
    )
    tags: Optional[List[str]] = None
    run_metadata: Optional[Dict[str, MetadataType]] = None

    is_model_artifact: bool = False
    is_deployment_artifact: bool = False

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_old_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove old attributes that are not used anymore.

        Args:
            data: The model data.

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

        return data
