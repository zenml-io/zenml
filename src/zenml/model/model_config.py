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
""" ModelConfig user facing interface to pass into pipeline or step."""

from typing import Optional, Union

from pydantic import Field, validator

from zenml.client import Client
from zenml.logger import get_logger
from zenml.model.model_stages import ModelStages
from zenml.models import (
    ModelBaseModel,
    ModelRequestModel,
    ModelResponseModel,
    ModelVersionResponseModel,
)

logger = get_logger(__name__)


class ModelConfig(ModelBaseModel):
    """ModelConfig class to pass into pipeline or step to set it into
    a model context.

    create_new_model_version: Whether to create a new model version during execution
    save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
        if available in active stack.
    recovery: Whether to keep failed runs with new versions for later recovery from it.
    """

    version: Optional[Union[str, ModelStages]] = Field(
        default=None,
        description="Model version is optional and points model context to a specific version or stage. It can be a version number, stage, ",
    )
    create_new_model_version: bool = False
    save_models_to_registry: bool = True
    recovery: bool = False

    @validator("create_new_model_version")
    def validate_create_new_model_version(
        cls, create_new_model_version, values
    ):
        if create_new_model_version:
            if values.get("model_version", None) is not None:
                raise ValueError(
                    "`model_version` cannot be used with `create_new_model_version`."
                )
        return create_new_model_version

    @property
    def _db_version(self):
        return getattr(self.version, "value", self.version)

    def _get_or_create_model(self) -> ModelResponseModel:
        """This method should get or create a model from Model WatchTower.
        New model is created implicitly, if missing, otherwise fetched."""
        zenml_client = Client()
        request_params = {
            k: v
            for k, v in self.dict().items()
            if k in ModelRequestModel.schema()["properties"]
        }
        request_params.update(
            {
                "user": zenml_client.active_user.id,
                "workspace": zenml_client.active_workspace.id,
            }
        )
        model_request = ModelRequestModel.parse_obj(request_params)
        try:
            model = zenml_client.zen_store.get_model(self.name)
        except KeyError:
            model = zenml_client.zen_store.create_model(model=model_request)
            logger.warning(f"New model `{self.name}` was created implicitly.")
        return model

    def _get_or_create_model_version(self) -> ModelVersionResponseModel:
        """This method should get or create a model version from Model WatchTower.
        New version will be created if `create_new_model_version`, otherwise
        will try to fetch based on `model_version`."""
        pass
