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
"""Model base model to support Model Control Plane feature."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, root_validator

from zenml.constants import (
    RUNNING_MODEL_VERSION,
)
from zenml.enums import ModelStages
from zenml.logger import get_logger
from zenml.models.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH

logger = get_logger(__name__)


class ModelBaseModel(BaseModel):
    """Model base model."""

    name: str = Field(
        title="The name of the model",
        max_length=STR_FIELD_MAX_LENGTH,
    )
    license: Optional[str] = Field(
        title="The license model created under",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    description: Optional[str] = Field(
        title="The description of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    audience: Optional[str] = Field(
        title="The target audience of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    use_cases: Optional[str] = Field(
        title="The use cases of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    limitations: Optional[str] = Field(
        title="The know limitations of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    trade_offs: Optional[str] = Field(
        title="The trade offs of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    ethic: Optional[str] = Field(
        title="The ethical implications of the model",
        max_length=TEXT_FIELD_MAX_LENGTH,
    )
    tags: Optional[List[str]] = Field(
        title="Tags associated with the model",
    )


class ModelConfigModel(ModelBaseModel):
    """ModelConfig class to pass into pipeline or step to set it into a model context.

    name: The name of the model.
    version: The model version name, number or stage is optional and points model context
        to a specific version/stage, if skipped and `create_new_model_version` is False -
        latest model version will be used.
    version_description: The description of the model version.
    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    delete_new_version_on_failure: Whether to delete failed runs with new versions for later recovery from it.
    suppress_warnings: Whether to suppress warnings during validation.
    """

    version: Optional[Union[ModelStages, int, str]]
    version_description: Optional[str]
    create_new_model_version: bool = False
    save_models_to_registry: bool = True
    delete_new_version_on_failure: bool = True
    suppress_warnings: bool = False

    class Config:
        """Config class."""

        smart_union = True

    @root_validator
    def _root_validator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all in one.

        Args:
            values: Dict of values.

        Returns:
            Dict of validated values.

        Raises:
            ValueError: If validation failed on one of the checks.
        """
        create_new_model_version = values.get(
            "create_new_model_version", False
        )
        delete_new_version_on_failure = values.get(
            "delete_new_version_on_failure", True
        )
        suppress_warnings = values.get("suppress_warnings", False)
        if not delete_new_version_on_failure and not create_new_model_version:
            if not suppress_warnings:
                logger.warning(
                    "Using `delete_new_version_on_failure=False` and `create_new_model_version=False` has no effect."
                    "Setting `delete_new_version_on_failure` to `True`."
                )
            values["delete_new_version_on_failure"] = True

        version = values.get("version", None)

        if create_new_model_version:
            misuse_message = (
                "`version` set to {set} cannot be used with `create_new_model_version`."
                "You can leave it default or set to a non-stage and non-numeric string.\n"
                "Examples:\n"
                " - `version` set to 1 or '1' is interpreted as a version number\n"
                " - `version` set to 'production' is interpreted as a stage\n"
                " - `version` set to 'my_first_version_in_2023' is a valid version to be created\n"
                " - `version` set to 'My Second Version!' is a valid version to be created\n"
            )
            if isinstance(version, ModelStages) or version in [
                stage.value for stage in ModelStages
            ]:
                raise ValueError(
                    misuse_message.format(set="a `ModelStages` instance")
                )
            if str(version).isnumeric():
                raise ValueError(misuse_message.format(set="a numeric value"))
            if version is None:
                if not suppress_warnings:
                    logger.info(
                        "Creation of new model version was requested, but no version name was explicitly provided."
                        f"Setting `version` to `{RUNNING_MODEL_VERSION}`."
                    )
                values["version"] = RUNNING_MODEL_VERSION
        if (
            version in [stage.value for stage in ModelStages]
            and not suppress_warnings
        ):
            logger.info(
                f"`version` `{version}` matches one of the possible `ModelStages` and will be fetched using stage."
            )
        if str(version).isnumeric() and not suppress_warnings:
            logger.info(
                f"`version` `{version}` is numeric and will be fetched using version number."
            )
        return values
