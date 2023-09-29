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
from unittest import mock

import pytest

from zenml.client import Client
from zenml.constants import RUNNING_MODEL_VERSION
from zenml.enums import ModelStages
from zenml.model import ModelConfig
from zenml.models import ModelRequestModel, ModelVersionRequestModel

MODEL_NAME = "super_model"


class ModelContext:
    def __init__(
        self,
        create_model: bool = True,
        model_version: str = None,
        stage: str = None,
    ):
        client = Client()
        self.workspace = client.active_workspace.id
        self.user = client.active_user.id
        self.create_model = create_model
        self.model_version = model_version
        self.stage = stage

    def __enter__(self):
        client = Client()
        if self.create_model:
            model = client.create_model(
                ModelRequestModel(
                    name=MODEL_NAME,
                    user=self.user,
                    workspace=self.workspace,
                )
            )
            if self.model_version is not None:
                mv = client.create_model_version(
                    ModelVersionRequestModel(
                        model=model.id,
                        version=self.model_version,
                        user=self.user,
                        workspace=self.workspace,
                    )
                )
                if self.stage is not None:
                    mv.set_stage(self.stage)
                return model, mv
            return model
        return None

    def __exit__(self, exc_type, exc_value, exc_traceback):
        try:
            Client().delete_model(MODEL_NAME)
        except KeyError:
            pass


class TestModelConfig:
    def test_model_created_with_warning(self):
        """Test if the model is created with a warning.

        It then checks if an info is logged during the creation process.
        Info is expected because the model is not yet created.
        """
        with ModelContext(create_model=False):
            mc = ModelConfig(name=MODEL_NAME)
            with mock.patch("zenml.model.model_config.logger.info") as logger:
                model = mc.get_or_create_model()
                logger.assert_called_once()
            assert model.name == MODEL_NAME

    def test_model_exists(self):
        """Test if model fetched fine, if exists."""
        with ModelContext() as model:
            mc = ModelConfig(name=MODEL_NAME)
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                model2 = mc.get_or_create_model()
                logger.assert_not_called()
            assert model.name == model2.name
            assert model.id == model2.id

    def test_model_create_model_and_version(self):
        """Test if model and version are created, not existing before."""
        with ModelContext(create_model=False):
            mc = ModelConfig(name=MODEL_NAME, create_new_model_version=True)
            with mock.patch("zenml.model.model_config.logger.info") as logger:
                mv = mc.get_or_create_model_version()
                logger.assert_called()
            assert mv.version == RUNNING_MODEL_VERSION
            assert mv.model.name == MODEL_NAME

    def test_model_fetch_model_and_version_by_number(self):
        """Test model and model version retrieval by exact version number."""
        with ModelContext(model_version="1.0.0") as (model, mv):
            mc = ModelConfig(name=MODEL_NAME, version="1.0.0")
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                mv_test = mc.get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_number_not_found(self):
        """Test model and model version retrieval fails by exact version number, if version missing."""
        with ModelContext():
            mc = ModelConfig(name=MODEL_NAME, version="1.0.0")
            with pytest.raises(KeyError):
                mc.get_or_create_model_version()

    def test_model_fetch_model_and_version_by_stage(self):
        """Test model and model version retrieval by exact stage number."""
        with ModelContext(
            model_version="1.0.0", stage=ModelStages.PRODUCTION
        ) as (model, mv):
            mc = ModelConfig(name=MODEL_NAME, stage=ModelStages.PRODUCTION)
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                mv_test = mc.get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_stage_not_found(self):
        """Test model and model version retrieval fails by exact stage number, if version in stage missing."""
        with ModelContext(model_version="1.0.0"):
            mc = ModelConfig(name=MODEL_NAME, version=ModelStages.PRODUCTION)
            with pytest.raises(KeyError):
                mc.get_or_create_model_version()

    def test_model_fetch_model_and_version_latest(self):
        """Test model and model version retrieval by latest version."""
        with ModelContext(model_version="1.0.0"):
            mc = ModelConfig(name=MODEL_NAME)
            mv = mc.get_or_create_model_version()

            assert mv.version == "1.0.0"

    def test_init_create_new_version_with_version_fails(self):
        """Test that it is not possible to use `version` and `create_new_model_version` together."""
        with pytest.raises(ValueError):
            ModelConfig(
                name=MODEL_NAME,
                version=ModelStages.PRODUCTION,
                create_new_model_version=True,
            )

        mc = ModelConfig(
            name=MODEL_NAME,
            create_new_model_version=True,
        )
        assert mc.name == MODEL_NAME
        assert mc.create_new_model_version
        assert mc.version == RUNNING_MODEL_VERSION

    def test_init_recovery_without_create_new_version_warns(self):
        """Test that use of `recovery` warn on `create_new_model_version` set to False."""
        with mock.patch("zenml.model.model_config.logger.warning") as logger:
            ModelConfig(name=MODEL_NAME, delete_new_version_on_failure=False)
            logger.assert_called_once()
        with mock.patch("zenml.model.model_config.logger.warning") as logger:
            ModelConfig(
                name=MODEL_NAME,
                delete_new_version_on_failure=False,
                create_new_model_version=True,
            )
            logger.assert_not_called()

    def test_init_stage_logic(self):
        """Test that if version is set to string contained in ModelStages user is informed about it."""
        with mock.patch("zenml.model.model_config.logger.info") as logger:
            mc = ModelConfig(
                name=MODEL_NAME,
                version=ModelStages.PRODUCTION.value,
            )
            logger.assert_called_once()
            assert mc.version == ModelStages.PRODUCTION.value

        mc = ModelConfig(name=MODEL_NAME, version=ModelStages.PRODUCTION)
        assert mc.version == ModelStages.PRODUCTION

    def test_recovery_flow(self):
        """Test that model context can recover same version after failure."""
        with ModelContext():
            mc = ModelConfig(
                name=MODEL_NAME,
                create_new_model_version=True,
                delete_new_version_on_failure=False,
            )
            mv1 = mc.get_or_create_model_version()
            del mc

            mc = ModelConfig(
                name=MODEL_NAME,
                create_new_model_version=True,
                delete_new_version_on_failure=False,
            )
            mv2 = mc.get_or_create_model_version()

            assert mv1.id == mv2.id
