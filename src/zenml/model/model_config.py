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
"""ModelConfig user facing interface to pass into pipeline or step."""

from typing import Any, Dict, Optional, Union

from pydantic import Field, validator

from zenml.client import Client
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.model.model_stages import ModelStages
from zenml.models import (
    ModelBaseModel,
    ModelRequestModel,
    ModelResponseModel,
    ModelVersionRequestModel,
    ModelVersionResponseModel,
)

logger = get_logger(__name__)


class ModelConfig(ModelBaseModel):
    """ModelConfig class to pass into pipeline or step to set it into a model context.

    version: points model context to a specific version or stage.
    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    recovery: Whether to keep failed runs with new versions for later recovery from it.
    """

    class Config:
        """Configuration of Pydantic."""

        smart_union = True

    version: Optional[Union[str, ModelStages]] = Field(
        default=None,
        description="Model version is optional and points model context to a specific version or stage.",
    )
    create_new_model_version: bool = False
    save_models_to_registry: bool = True
    recovery: bool = False

    @validator("create_new_model_version")
    def _validate_create_new_model_version(
        cls, create_new_model_version: bool, values: Dict[str, Any]
    ) -> bool:
        if create_new_model_version:
            if values.get("version", None) is not None:
                raise ValueError(
                    "`version` cannot be used with `create_new_model_version`."
                )
        return create_new_model_version

    @validator("recovery")
    def _validate_recovery(
        cls, recovery: bool, values: Dict[str, Any]
    ) -> bool:
        if recovery:
            if not values.get("create_new_model_version", False):
                logger.warning(
                    "Using `recovery` flag without `create_new_model_version=True` has no effect."
                )
        return recovery

    @validator("version")
    def _validate_version(
        cls, version: Union[str, ModelStages]
    ) -> Union[str, ModelStages]:
        if isinstance(version, str) and version in [
            stage.value for stage in ModelStages
        ]:
            logger.info(
                f"`version` `{version}` matches one of the possible `ModelStages`, model will be fetched using stage."
            )
        return version

    @property
    def _stage(self) -> Optional[str]:
        if isinstance(self.version, ModelStages):
            return self.version.value
        return None

    def get_or_create_model(self) -> ModelResponseModel:
        """This method should get or create a model from Model WatchTower.

        New model is created implicitly, if missing, otherwise fetched.

        Returns:
            The model based on configuration.
        """
        zenml_client = Client()
        try:
            model = zenml_client.zen_store.get_model(
                model_name_or_id=self.name
            )
        except KeyError:
            model_request = ModelRequestModel(
                name=self.name,
                license=self.license,
                description=self.description,
                audience=self.audience,
                use_cases=self.use_cases,
                limitations=self.limitations,
                trade_offs=self.trade_offs,
                ethic=self.ethic,
                tags=self.tags,
                user=zenml_client.active_user.id,
                workspace=zenml_client.active_workspace.id,
            )
            model_request = ModelRequestModel.parse_obj(model_request)
            try:
                model = zenml_client.zen_store.create_model(
                    model=model_request
                )
                logger.warning(
                    f"New model `{self.name}` was created implicitly."
                )
            except EntityExistsError:
                # this is backup logic, if model was created somehow in between get and create calls
                model = zenml_client.zen_store.get_model(
                    model_name_or_id=self.name
                )
        return model

    def _create_model_version(
        self, model: ModelResponseModel
    ) -> ModelVersionResponseModel:
        """This method creates a model version for Model WatchTower.

        Args:
            model: The model containing the model version.

        Returns:
            The model version based on configuration.
        """
        zenml_client = Client()
        self.version = "running"
        model_version_request = ModelVersionRequestModel(
            user=zenml_client.active_user.id,
            workspace=zenml_client.active_workspace.id,
            version=self.version,
            model=model.id,
        )
        mv_request = ModelVersionRequestModel.parse_obj(model_version_request)
        try:
            return zenml_client.zen_store.get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_id=self.version,
            )
        except KeyError:
            if self.recovery:
                logger.warning(
                    f"Recovery mode: No `{self.version}` model version found."
                )
            mv = zenml_client.zen_store.create_model_version(
                model_version=mv_request
            )
            logger.warning(f"New model version `{self.name}` was created.")

            return mv

    def _get_model_version(
        self, model: ModelResponseModel
    ) -> ModelVersionResponseModel:
        """This method gets a model version from Model WatchTower.

        Args:
            model: The model containing the model version.

        Returns:
            The model version based on configuration.
        """
        zenml_client = Client()
        if self.version is None:
            # raise if not found
            return zenml_client.zen_store.get_model_version(
                model_name_or_id=self.name
            )
        # by version name or stage
        # raise if not found
        return zenml_client.zen_store.get_model_version(
            model_name_or_id=self.name, model_version_name_or_id=self.version
        )

    def get_or_create_model_version(self) -> ModelVersionResponseModel:
        """This method should get or create a model and a model version from Model WatchTower.

        New model is created implicitly, if missing, otherwise fetched.

        New version will be created if `create_new_model_version`, otherwise
        will try to fetch based on `model_version`.

        Returns:
            The model version based on configuration.
        """
        model = self.get_or_create_model()
        if self.create_new_model_version:
            mv = self._create_model_version(model)
        else:
            mv = self._get_model_version(model)
        return mv
