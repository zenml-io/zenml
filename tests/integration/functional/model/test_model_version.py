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
from zenml.enums import ModelStages
from zenml.model.model_version import ModelVersion
from zenml.models.tag_models import TagRequestModel

MODEL_NAME = "super_model"


class ModelContext:
    def __init__(
        self,
        client: "Client",
        create_model: bool = True,
        model_version: str = None,
        stage: str = None,
    ):
        self.client = client
        self.workspace = client.active_workspace.id
        self.user = client.active_user.id
        self.create_model = create_model
        self.model_version = model_version
        self.stage = stage

    def __enter__(self):
        if self.create_model:
            model = self.client.create_model(
                name=MODEL_NAME,
            )
            if self.model_version is not None:
                mv = self.client.create_model_version(
                    model_name_or_id=model.id,
                    name=self.model_version,
                )
                if self.stage is not None:
                    mv.set_stage(self.stage)
                return model, mv
            return model
        return None

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass


class TestModelVersion:
    def test_model_created_with_warning(self, clean_client: "Client"):
        """Test if the model is created with a warning.

        It then checks if an info is logged during the creation process.
        Info is expected because the model is not yet created.
        """
        with ModelContext(clean_client, create_model=False):
            mv = ModelVersion(name=MODEL_NAME)
            with mock.patch("zenml.model.model_version.logger.info") as logger:
                model = mv._get_or_create_model()
                logger.assert_called_once()
            assert model.name == MODEL_NAME

    def test_model_exists(self, clean_client: "Client"):
        """Test if model fetched fine, if exists."""
        with ModelContext(clean_client) as model:
            mv = ModelVersion(name=MODEL_NAME)
            with mock.patch(
                "zenml.model.model_version.logger.warning"
            ) as logger:
                model2 = mv._get_or_create_model()
                logger.assert_not_called()
            assert model.name == model2.name
            assert model.id == model2.id

    def test_model_create_model_and_version(self, clean_client: "Client"):
        """Test if model and version are created, not existing before."""
        with ModelContext(clean_client, create_model=False):
            mv = ModelVersion(name=MODEL_NAME, tags=["tag1", "tag2"])
            with mock.patch("zenml.model.model_version.logger.info") as logger:
                mv = mv._get_or_create_model_version()
                logger.assert_called()
            assert mv.name == str(mv.number)
            assert mv.model.name == MODEL_NAME
            assert {t.name for t in mv.tags} == {"tag1", "tag2"}
            assert {t.name for t in mv.model.tags} == {"tag1", "tag2"}

    def test_create_model_version_makes_proper_tagging(
        self, clean_client: "Client"
    ):
        """Test if model versions get unique tags."""
        with ModelContext(clean_client, create_model=False):
            mv = ModelVersion(name=MODEL_NAME, tags=["tag1", "tag2"])
            mv = mv._get_or_create_model_version()
            assert mv.name == str(mv.number)
            assert mv.model.name == MODEL_NAME
            assert {t.name for t in mv.tags} == {"tag1", "tag2"}
            assert {t.name for t in mv.model.tags} == {"tag1", "tag2"}

            mv = ModelVersion(name=MODEL_NAME, tags=["tag3", "tag4"])
            mv = mv._get_or_create_model_version()
            assert mv.name == str(mv.number)
            assert mv.model.name == MODEL_NAME
            assert {t.name for t in mv.tags} == {"tag3", "tag4"}
            assert {t.name for t in mv.model.tags} == {"tag1", "tag2"}

    def test_model_fetch_model_and_version_by_number(
        self, clean_client: "Client"
    ):
        """Test model and model version retrieval by exact version number."""
        with ModelContext(clean_client, model_version="1.0.0") as (model, mv):
            mv = ModelVersion(name=MODEL_NAME, version="1.0.0")
            with mock.patch(
                "zenml.model.model_version.logger.warning"
            ) as logger:
                mv_test = mv._get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_number_not_found(
        self, clean_client: "Client"
    ):
        """Test model and model version retrieval fails by exact version number, if version missing."""
        with ModelContext(clean_client):
            mv = ModelVersion(name=MODEL_NAME, version="1.0.0")
            with pytest.raises(KeyError):
                mv._get_model_version()

    def test_model_fetch_model_and_version_by_stage(
        self, clean_client: "Client"
    ):
        """Test model and model version retrieval by exact stage number."""
        with ModelContext(
            clean_client, model_version="1.0.0", stage=ModelStages.PRODUCTION
        ) as (model, mv):
            mv = ModelVersion(name=MODEL_NAME, version=ModelStages.PRODUCTION)
            with mock.patch(
                "zenml.model.model_version.logger.warning"
            ) as logger:
                mv_test = mv._get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_stage_not_found(
        self, clean_client: "Client"
    ):
        """Test model and model version retrieval fails by exact stage number, if version in stage missing."""
        with ModelContext(clean_client, model_version="1.0.0"):
            mv = ModelVersion(name=MODEL_NAME, version=ModelStages.PRODUCTION)
            with pytest.raises(KeyError):
                mv._get_model_version()

    def test_model_fetch_model_and_version_latest(
        self, clean_client: "Client"
    ):
        """Test model and model version retrieval by latest version."""
        with ModelContext(clean_client, model_version="1.0.0"):
            mv = ModelVersion(name=MODEL_NAME, version=ModelStages.LATEST)
            mv = mv._get_or_create_model_version()

            assert mv.name == "1.0.0"

    def test_init_stage_logic(self, clean_client: "Client"):
        """Test that if version is set to string contained in ModelStages user is informed about it."""
        with mock.patch("zenml.model.model_version.logger.info") as logger:
            mv = ModelVersion(
                name=MODEL_NAME,
                version=ModelStages.PRODUCTION.value,
            )
            logger.assert_called_once()
            assert mv.version == ModelStages.PRODUCTION.value

        mv = ModelVersion(name=MODEL_NAME, version=ModelStages.PRODUCTION)
        assert mv.version == ModelStages.PRODUCTION

    def test_recovery_flow(self, clean_client: "Client"):
        """Test that model context can recover same version after failure."""
        with ModelContext(clean_client):
            mv = ModelVersion(name=MODEL_NAME)
            mv1 = mv._get_or_create_model_version()
            del mv

            mv = ModelVersion(name=MODEL_NAME, version=1)
            mv2 = mv._get_or_create_model_version()

            assert mv1.id == mv2.id

    def test_tags_properly_created(self, clean_client: "Client"):
        """Test that model context can create proper tag relationships."""
        clean_client.create_tag(TagRequestModel(name="foo", color="green"))
        mv = ModelVersion(
            name=MODEL_NAME,
            tags=["foo", "bar"],
        )

        # run 2 times to first create, next get
        for _ in range(2):
            model = mv._get_or_create_model()

            assert len(model.tags) == 2
            assert {t.name for t in model.tags} == {"foo", "bar"}
            assert {t.color for t in model.tags if t.name == "foo"} == {
                "green"
            }

    def test_tags_properly_updated(self, clean_client: "Client"):
        """Test that model context can update proper tag relationships."""
        mv = ModelVersion(
            name=MODEL_NAME,
            tags=["foo", "bar"],
        )
        model_id = mv._get_or_create_model_version().model.id

        clean_client.update_model(model_id, add_tags=["tag1", "tag2"])
        model = mv._get_or_create_model()
        assert len(model.tags) == 4
        assert {t.name for t in model.tags} == {
            "foo",
            "bar",
            "tag1",
            "tag2",
        }

        clean_client.update_model_version(
            model_id, "1", add_tags=["tag3", "tag4"]
        )
        model_version = mv._get_or_create_model_version()
        assert len(model_version.tags) == 4
        assert {t.name for t in model_version.tags} == {
            "foo",
            "bar",
            "tag3",
            "tag4",
        }

        clean_client.update_model(model_id, remove_tags=["tag1", "tag2"])
        model = mv._get_or_create_model()
        assert len(model.tags) == 2
        assert {t.name for t in model.tags} == {"foo", "bar"}

        clean_client.update_model_version(
            model_id, "1", remove_tags=["tag3", "tag4"]
        )
        model_version = mv._get_or_create_model_version()
        assert len(model_version.tags) == 2
        assert {t.name for t in model_version.tags} == {"foo", "bar"}

    def test_model_config_differs_from_db_warns(self, clean_client: "Client"):
        """Test that model context warns if model config differs from db."""
        mv = ModelVersion(
            name=MODEL_NAME,
            tags=["foo", "bar"],
        )
        mv._get_or_create_model()

        mv = ModelVersion(
            name=MODEL_NAME,
            tags=["bar", "new"],
            license="NEW",
            save_models_to_registry=False,
        )
        with mock.patch("zenml.model.model_version.logger.warning") as logger:
            mv._get_or_create_model()
            logger.assert_called_once()

            warning = logger.call_args[0][0]
            assert "license" in warning
            assert "save_models_to_registry" in warning

    def test_model_version_config_differs_from_db_warns(
        self, clean_client: "Client"
    ):
        """Test that model version context warns if model version config differs from db."""
        mv = ModelVersion(
            name=MODEL_NAME,
            version="1.0.0",
            tags=["foo", "bar"],
        )
        mv._get_or_create_model_version()

        mv = ModelVersion(
            name=MODEL_NAME,
            version="1.0.0",
            tags=["bar", "new"],
            license="NEW",
            description="NEW",
            save_models_to_registry=False,
        )
        with mock.patch("zenml.model.model_version.logger.warning") as logger:
            mv._get_or_create_model_version()
            logger.assert_called()
            assert logger.call_count == 2  # for model and model version

            warning = logger.call_args_list[1][0][0]
            assert "tags added" in warning
            assert "tags removed" in warning
            assert "description" in warning
