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

from pydantic import BaseModel, root_validator

from zenml.enums import ModelStages
from zenml.exceptions import StepContextError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.new.steps.step_context import get_step_context

if TYPE_CHECKING:
    from zenml.model.model import Model


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
        model_version: The identifier of a version of the model to link the artifact
            to. It can be an exact version ("my_version"), exact version number
            (42), stage (ModelStages.PRODUCTION or "production"), or
            (ModelStages.LATEST or None) for the latest version (default).
        is_model_artifact: Whether the artifact is a model artifact.
        is_deployment_artifact: Whether the artifact is a deployment artifact.
    """

    name: Optional[str] = None
    version: Optional[Union[str, int]] = None
    tags: Optional[List[str]] = None
    run_metadata: Optional[Dict[str, MetadataType]] = None

    model_name: Optional[str] = None
    model_version: Optional[Union[ModelStages, str, int]] = None
    is_model_artifact: bool = False
    is_deployment_artifact: bool = False

    @root_validator
    def _root_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        model_name = values.get("model_name", None)
        if model_name and values.get("model_version", None) is None:
            raise ValueError(
                f"Creation of new model version from `{cls}` is not allowed. "
                "Please either keep `model_name` and `model_version` both "
                "`None` to get the model version from the step context or "
                "specify both at the same time. You can use `ModelStages.LATEST` "
                "as `model_version` when latest model version is desired."
            )
        return values

    class Config:
        """Config class for ArtifactConfig."""

        smart_union = True

    @property
    def _model(self) -> Optional["Model"]:
        """The model linked to this artifact.

        Returns:
            The model or None if the model version cannot be determined.
        """
        try:
            model_ = get_step_context().model
        except (StepContextError, RuntimeError):
            model_ = None
        # Check if another model name was specified
        if (self.model_name is not None) and (
            model_ is None or model_.name != self.model_name
        ):
            # Create a new Model instance with the provided model name and version
            from zenml.model.model import Model

            on_the_fly_config = Model(
                name=self.model_name, version=self.model_version
            )
            return on_the_fly_config

        return model_
