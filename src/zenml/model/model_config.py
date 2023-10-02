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

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from pydantic import PrivateAttr, validator

from zenml.enums import ModelStages
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models.model_base_model import ModelConfigModel

if TYPE_CHECKING:
    from zenml.models.model_models import (
        ModelResponseModel,
        ModelVersionResponseModel,
    )

logger = get_logger(__name__)


class ModelConfig(ModelConfigModel):
    """ModelConfig class to pass into pipeline or step to set it into a model context.

    version: points model context to a specific version or stage.
    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    delete_new_version_on_failure: Whether to delete failed runs with new versions for later recovery from it.
    """

    _model: Optional["ModelResponseModel"] = PrivateAttr(default=None)
    _model_version: Optional["ModelVersionResponseModel"] = PrivateAttr(
        default=None
    )

    @validator("create_new_model_version")
    def _validate_create_new_model_version(
        cls, create_new_model_version: bool, values: Dict[str, Any]
    ) -> bool:
        from zenml.constants import RUNNING_MODEL_VERSION

        if create_new_model_version:
            version = values.get("version", RUNNING_MODEL_VERSION)
            if version != RUNNING_MODEL_VERSION and version is not None:
                raise ValueError(
                    "`version` cannot be used with `create_new_model_version`."
                )
            values["version"] = RUNNING_MODEL_VERSION
        return create_new_model_version

    @validator("delete_new_version_on_failure")
    def _validate_recovery(
        cls, delete_new_version_on_failure: bool, values: Dict[str, Any]
    ) -> bool:
        if not delete_new_version_on_failure:
            if not values.get("create_new_model_version", False):
                logger.warning(
                    "Using `delete_new_version_on_failure=False` without `create_new_model_version=True` has no effect."
                )
        return delete_new_version_on_failure

    @validator("version")
    def _validate_version(
        cls, version: Union[str, ModelStages]
    ) -> Union[str, ModelStages]:
        if version in [stage.value for stage in ModelStages]:
            logger.info(
                f"`version` `{version}` matches one of the possible `ModelStages`, model will be fetched using stage."
            )
        return version

    def get_or_create_model(self) -> "ModelResponseModel":
        """This method should get or create a model from Model WatchTower.

        New model is created implicitly, if missing, otherwise fetched.

        Returns:
            The model based on configuration.
        """
        if self._model is not None:
            return self._model

        from zenml.client import Client
        from zenml.models.model_models import ModelRequestModel

        zenml_client = Client()
        try:
            self._model = zenml_client.get_model(model_name_or_id=self.name)
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
                self._model = zenml_client.create_model(model=model_request)
                logger.info(f"New model `{self.name}` was created implicitly.")
            except EntityExistsError:
                # this is backup logic, if model was created somehow in between get and create calls
                self._model = zenml_client.get_model(
                    model_name_or_id=self.name
                )

        return self._model

    def _create_model_version(
        self, model: "ModelResponseModel"
    ) -> "ModelVersionResponseModel":
        """This method creates a model version for Model WatchTower.

        Args:
            model: The model containing the model version.

        Returns:
            The model version based on configuration.
        """
        if self._model_version is not None:
            return self._model_version

        from zenml.client import Client
        from zenml.constants import RUNNING_MODEL_VERSION
        from zenml.models.model_models import ModelVersionRequestModel

        zenml_client = Client()
        self.version = RUNNING_MODEL_VERSION
        model_version_request = ModelVersionRequestModel(
            user=zenml_client.active_user.id,
            workspace=zenml_client.active_workspace.id,
            version=self.version,
            model=model.id,
        )
        mv_request = ModelVersionRequestModel.parse_obj(model_version_request)
        try:
            mv = zenml_client.get_model_version(
                model_name_or_id=self.name,
                model_version_name_or_id=self.version,
            )
            self._model_version = mv
        except KeyError:
            self._model_version = zenml_client.create_model_version(
                model_version=mv_request
            )
            logger.info(f"New model version `{self.name}` was created.")

        return self._model_version

    def _get_model_version(
        self, model: "ModelResponseModel"
    ) -> "ModelVersionResponseModel":
        """This method gets a model version from Model WatchTower.

        Args:
            model: The model containing the model version.

        Returns:
            The model version based on configuration.
        """
        from zenml.client import Client

        zenml_client = Client()
        if self.version is None:
            # raise if not found
            return zenml_client.get_model_version(model_name_or_id=self.name)
        # by version name or stage
        # raise if not found
        return zenml_client.get_model_version(
            model_name_or_id=self.name, model_version_name_or_id=self.version
        )

    def get_or_create_model_version(self) -> "ModelVersionResponseModel":
        """This method should get or create a model and a model version from Model WatchTower.

        A new model is created implicitly if missing, otherwise existing model is fetched. Model
        name is controlled by the `name` parameter.

        Model Version returned by this method is resolved based on model configuration:
        - If there is an existing model version leftover from the previous failed run with
        `delete_new_version_on_failure` is set to False and `create_new_model_version` is True,
        leftover model version will be reused.
        - Otherwise if `create_new_model_version` is True, a new model version is created.
        - If `create_new_model_version` is False a model version will be fetched based on the version:
            - If `version` is not set, the latest model version will be fetched.
            - If `version` is set to a string, the model version with the matching version will be fetched.
            - If `version` is set to a `ModelStage`, the model version with the matching stage will be fetched.

        Returns:
            The model version based on configuration.
        """
        model = self.get_or_create_model()
        if self.create_new_model_version:
            mv = self._create_model_version(model)
        else:
            mv = self._get_model_version(model)
        return mv
