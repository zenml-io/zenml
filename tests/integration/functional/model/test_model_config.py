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

from zenml.client import Client
from zenml.model import ModelConfig
from zenml.models import ModelRequestModel


class TestModelConfig:
    def test_model_created_with_warning(self):
        try:
            mc = ModelConfig(name="super_model")
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                model = mc.get_or_create_model()
                logger.assert_called_once()
            assert model.name == "super_model"
        finally:
            Client().zen_store.delete_model("super_model")

    def test_model_exists(self):
        c = Client()
        try:
            model = c.zen_store.create_model(
                ModelRequestModel(
                    name="super_model",
                    user=c.active_user.id,
                    workspace=c.active_workspace.id,
                )
            )
            mc = ModelConfig(name="super_model")
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                model2 = mc.get_or_create_model()
                logger.assert_not_called()
            assert model.name == model2.name
            assert model.id == model2.id
        finally:
            c.zen_store.delete_model("super_model")

    def test_model_create_model_and_version(self):
        c = Client()
        try:
            mc = ModelConfig(name="super_model", create_new_model_version=True)
            with mock.patch(
                "zenml.model.model_config.logger.warning"
            ) as logger:
                mv = mc.get_or_create_model_version()
                logger.assert_called()
            assert mv.version == "running"
            assert mv.model.name == "super_model"
        finally:
            c.zen_store.delete_model("super_model")
