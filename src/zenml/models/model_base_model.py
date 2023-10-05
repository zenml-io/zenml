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
"""Model base model to support Model WatchTower feature."""

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

    version_name: points model context to a specific version or stage.
    version_number: points model context to a specific version number.
    version_description: The description of the model version.
    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    delete_new_version_on_failure: Whether to delete failed runs with new versions for later recovery from it.
    """

    version_name: Optional[Union[ModelStages, str]] = Field(
        default=None,
        description="Model version or stage is optional and points model context to a specific version/stage, "
        "if skipped and `create_new_model_version` is False - latest model version will be used.",
    )
    version_number: Optional[int] = Field(
        default=None,
        description="Model version number is optional and points model context to a specific version number, "
        "this works only for reading from model version and not suitable with `create_new_model_version`.",
    )
    version_description: Optional[str]
    create_new_model_version: bool = False
    save_models_to_registry: bool = True
    delete_new_version_on_failure: bool = True

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
        if not delete_new_version_on_failure and not create_new_model_version:
            logger.warning(
                "Using `delete_new_version_on_failure=False` and `create_new_model_version=False` has no effect."
                "Setting `delete_new_version_on_failure` to `True`."
            )
            values["delete_new_version_on_failure"] = True

        version_number = values.get("version_number", None)
        version_name = values.get("version_name", None)

        if version_number and create_new_model_version:
            raise ValueError(
                "`version_number` cannot be used with `create_new_model_version`."
            )

        if version_number is not None and version_name is not None:
            logger.warning(
                "`version_number` has higher priority then `version_name`."
                "Setting `version_name` to `None`."
            )
            version_name = None
            values["version_name"] = None

        if create_new_model_version:
            if isinstance(version_name, ModelStages):
                raise ValueError(
                    "`version_name` set to `ModelStages` instance cannot be used with `create_new_model_version`."
                    "You can leave it default or set to a string name of a model version."
                )
            if version_name is None:
                logger.info(
                    "Creation of new model version was requested, but no version name was explicitly provided."
                    f"Setting `version_name` to `{RUNNING_MODEL_VERSION}`."
                )
                values["version_name"] = RUNNING_MODEL_VERSION
        if version_name in [stage.value for stage in ModelStages]:
            logger.info(
                f"`version_name` `{version_name}` matches one of the possible `ModelStages`, model will be fetched using stage."
            )
        return values
