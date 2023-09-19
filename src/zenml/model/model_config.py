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

from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from pydantic import Field, PrivateAttr, validator

from zenml.constants import RUNNING_MODEL_VERSION
from zenml.logger import get_logger
from zenml.model.base_model import ModelBaseModel
from zenml.model.model_stages import ModelStages

if TYPE_CHECKING:
    from zenml.models.model_models import (
        ModelRequestModel,
        ModelResponseModel,
        ModelVersionRequestModel,
        ModelVersionResponseModel,
    )
logger = get_logger(__name__)


class ModelConfig(ModelBaseModel):
    """ModelConfig class to pass into pipeline or step to set it into a model context.

    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    recovery: Whether to keep failed runs with new versions for later recovery from it.
    """

    version: Optional[str] = Field(
        default=None,
        description="Model version is optional and points model context to a specific version.",
    )
    stage: Optional[ModelStages] = Field(
        default=None,
        description="Model stage is optional and points model context to a specific stage.",
    )
    create_new_model_version: bool = False
    save_models_to_registry: bool = True
    recovery: bool = False

    _model: Optional["ModelResponseModel"] = PrivateAttr(default=None)
    _model_version: Optional["ModelVersionResponseModel"] = PrivateAttr(
        default=None
    )

    @validator("stage")
    def _validate_stage(
        cls, stage: ModelStages, values: Dict[str, Any]
    ) -> ModelStages:
        if stage is not None and values.get("version", None) is not None:
            raise ValueError("Cannot set both `version` and `stage`.")
        return stage

    @validator("create_new_model_version")
    def _validate_create_new_model_version(
        cls, create_new_model_version: bool, values: Dict[str, Any]
    ) -> bool:
        if create_new_model_version:
            if values.get("version", None) is not None:
                raise ValueError(
                    "`version` cannot be used with `create_new_model_version`."
                )
            if values.get("stage", None) is not None:
                raise ValueError(
                    "`stage` cannot be used with `create_new_model_version`."
                )
        return create_new_model_version

    @validator("recovery")
    def _validate_recovery(
        cls, recovery: bool, values: Dict[str, Any]
    ) -> bool:
        if recovery:
            if not values.get("create_new_model_version", False):
                logger.warning(
                    "Using `recovery` flag without `create_new_model_version=True` makes no effect"
                )
        return recovery

    @validator("save_models_to_registry")
    def _validate_save_models_to_registry(
        cls, save_models_to_registry: bool
    ) -> bool:
        if save_models_to_registry:
            logger.warning(
                "`save_models_to_registry` is not yet supported - no effect on pipeline execution."
            )
        return save_models_to_registry

    def _get_request_params(
        self,
        request_model: Union[
            Type["ModelRequestModel"], Type["ModelVersionRequestModel"]
        ],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        from zenml.client import Client

        zenml_client = Client()
        request_params = {
            k: v
            for k, v in self.dict().items()
            if k in request_model.schema()["properties"]
        }
        request_params.update(kwargs)
        request_params.update(
            {
                "user": zenml_client.active_user.id,
                "workspace": zenml_client.active_workspace.id,
            }
        )
        return request_params

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
            model = zenml_client.zen_store.get_model(
                model_name_or_id=self.name
            )
        except KeyError:
            model_request = ModelRequestModel.parse_obj(
                self._get_request_params(ModelRequestModel)
            )
            model = zenml_client.zen_store.create_model(model=model_request)
            logger.warning(f"New model `{self.name}` was created implicitly.")
        self._model = model
        return model

    def _get_or_create_model_version(
        self, model: "ModelResponseModel"
    ) -> "ModelVersionResponseModel":
        """This method should get or create a model version from Model WatchTower.

        New version will be created if `create_new_model_version`, otherwise
        will try to fetch based on `version`.

        Args:
            model: The model containing the model version.

        Returns:
            The model version based on configuration.
        """
        if self._model_version is not None:
            return self._model_version

        from zenml.client import Client
        from zenml.models.model_models import ModelVersionRequestModel

        zenml_client = Client()
        # if specific version requested
        if not self.create_new_model_version:
            # by stage
            if self.stage is not None:
                # raise if not found
                return zenml_client.zen_store.get_model_version_in_stage(
                    model_name_or_id=self.name,
                    model_stage=self.stage,
                )
            # by version
            else:
                # latest version requested
                if self.version is None:
                    # raise if not found
                    return zenml_client.zen_store.get_model_version_latest(
                        model_name_or_id=self.name
                    )
                # specific version requested
                else:
                    # raise if not found
                    return zenml_client.zen_store.get_model_version(
                        model_name_or_id=self.name,
                        model_version_name_or_id=self.version,
                    )
        # else new version requested
        self.version = RUNNING_MODEL_VERSION
        mv_request = ModelVersionRequestModel.parse_obj(
            self._get_request_params(ModelVersionRequestModel, model=model.id)
        )
        mv = None
        if self.recovery:
            try:
                mv = zenml_client.zen_store.get_model_version(
                    model_name_or_id=self.name,
                    model_version_name_or_id=self.version,
                )
            except KeyError:
                logger.warning(
                    f"Recovery mode: No `{self.version}` model version found."
                )
        if mv is None:
            mv = zenml_client.zen_store.create_model_version(
                model_version=mv_request
            )
            logger.warning(f"New model version `{self.name}` was created.")
        self._model_version = mv
        return mv

    def get_or_create_model_version(self) -> "ModelVersionResponseModel":
        """This method should get or create a model and a model version from Model WatchTower.

        New model is created implicitly, if missing, otherwise fetched.

        New version will be created if `create_new_model_version`, otherwise
        will try to fetch based on `model_version`.

        Returns:
            The model version based on configuration.
        """
        model = self.get_or_create_model()
        mv = self._get_or_create_model_version(model)
        return mv
