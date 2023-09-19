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
from zenml.model import ModelConfig, ModelStages
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
        zs = Client().zen_store
        if self.create_model:
            model = zs.create_model(
                ModelRequestModel(
                    name=MODEL_NAME,
                    user=self.user,
                    workspace=self.workspace,
                )
            )
            if self.model_version is not None:
                mv = zs.create_model_version(
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
        zs = Client().zen_store
        try:
            zs.delete_model(MODEL_NAME)
        except KeyError:
            pass


class TestModelConfig:
    def test_model_created_with_warning(self):
        with ModelContext(create_model=False):
            mc = ModelConfig(name=MODEL_NAME)
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                model = mc.get_or_create_model()
                logger.assert_called_once()
            assert model.name == MODEL_NAME

    def test_model_exists(self):
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
        with ModelContext(create_model=False):
            mc = ModelConfig(name=MODEL_NAME, create_new_model_version=True)
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                mv = mc.get_or_create_model_version()
                logger.assert_called()
            assert mv.version == RUNNING_MODEL_VERSION
            assert mv.model.name == MODEL_NAME

    def test_model_fetch_model_and_version_by_number(self):
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
        with ModelContext():
            mc = ModelConfig(name=MODEL_NAME, version="1.0.0")
            with pytest.raises(KeyError):
                mc.get_or_create_model_version()

    def test_model_fetch_model_and_version_by_stage(self):
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
        with ModelContext(model_version="1.0.0"):
            mc = ModelConfig(name=MODEL_NAME, stage=ModelStages.PRODUCTION)
            with pytest.raises(KeyError):
                mc.get_or_create_model_version()

    def test_init_create_new_version_with_version_fails(self):
        with pytest.raises(ValueError):
            ModelConfig(
                name=MODEL_NAME,
                stage=ModelStages.PRODUCTION,
                create_new_model_version=True,
            )

        mc = ModelConfig(
            name=MODEL_NAME,
            create_new_model_version=True,
        )
        assert mc.name == MODEL_NAME
        assert mc.create_new_model_version
        assert mc.version is None

    def test_init_recovery_without_create_new_version_warns(self):
        with mock.patch("zenml.model.model_config.logger.warning") as logger:
            ModelConfig(name=MODEL_NAME, recovery=True)
            logger.assert_called_once()
        with mock.patch("zenml.model.model_config.logger.warning") as logger:
            ModelConfig(
                name=MODEL_NAME,
                recovery=True,
                create_new_model_version=True,
            )
            logger.assert_not_called()

    def test_recovery_flow(self):
        with ModelContext():
            mc = ModelConfig(
                name=MODEL_NAME,
                create_new_model_version=True,
                recovery=True,
            )
            mv1 = mc.get_or_create_model_version()
            del mc

            mc = ModelConfig(
                name=MODEL_NAME,
                create_new_model_version=True,
                recovery=True,
            )
            mv2 = mc.get_or_create_model_version()

            assert mv1 == mv2

    def test_both_stage_and_version_fail(self):
        with ModelContext():
            with pytest.raises(ValueError):
                ModelConfig(
                    name=MODEL_NAME,
                    stage=ModelStages.PRODUCTION,
                    version="1.0.0",
                )
