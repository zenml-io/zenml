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
from typing import TYPE_CHECKING, List, Optional, Union

from pydantic import BaseModel

from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.new.steps.step_context import get_step_context

if TYPE_CHECKING:
    from zenml.model.model_config import ModelConfig


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
            model_name="my_model",  # link the artifact to a model
        )
    ]:
        return ...
    ```

    Attributes:
        name: The name of the artifact.
        version: The version of the artifact.
        tags: The tags of the artifact.
        model_name: The name of the model to link artifact to.
        model_version: The identifier of the model version to link artifact to.
            It can be an exact version ("23"), exact version number (42), stage
            (ModelStages.PRODUCTION) or None for the latest version (default).
        model_stage: The stage of the model version to link artifact to.
        is_model_artifact: Whether the artifact is a model artifact.
        is_deployment_artifact: Whether the artifact is a deployment artifact.
    """

    name: Optional[str] = None
    version: Optional[Union[str, int]] = None
    tags: Optional[List[str]] = None

    model_name: Optional[str] = None
    model_version: Optional[Union[ModelStages, str, int]] = None
    is_model_artifact: bool = False
    is_deployment_artifact: bool = False

    class Config:
        """Config class for ArtifactConfig."""

        smart_union = True

    @property
    def _model_config(self) -> Optional["ModelConfig"]:
        """The model configuration linked to this artifact.

        Returns:
            The model configuration or None if the model configuration cannot
            be acquired from @step or @pipeline or built on the fly from
            fields of this class.
        """
        try:
            model_config = get_step_context().model_config
        except (StepContextError, RuntimeError):
            model_config = None
        # Check if a specific model name is provided and it doesn't match the context name
        if (self.model_name is not None) and (
            model_config is None or model_config.name != self.model_name
        ):
            # Create a new ModelConfig instance with the provided model name and version
            from zenml.model.model_config import ModelConfig

            on_the_fly_config = ModelConfig(
                name=self.model_name,
                version=self.model_version,
                create_new_model_version=False,
            )
            return on_the_fly_config

        return model_config
