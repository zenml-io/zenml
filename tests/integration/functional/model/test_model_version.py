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

from tests.integration.functional.utils import model_killer, tags_killer
from zenml import get_step_context, pipeline, step
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.model.model_version import ModelVersion
from zenml.model.utils import log_model_version_metadata
from zenml.models.tag_models import TagRequestModel

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
                name=MODEL_NAME,
            )
            if self.model_version is not None:
                mv = client.create_model_version(
                    model_name_or_id=model.id,
                    name=self.model_version,
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


@step
def step_metadata_logging_functional():
    log_model_version_metadata({"foo": "bar"})
    assert get_step_context().model_version.metadata["foo"] == "bar"


class TestModelVersion:
    def test_model_created_with_warning(self):
        """Test if the model is created with a warning.

        It then checks if an info is logged during the creation process.
        Info is expected because the model is not yet created.
        """
        with ModelContext(create_model=False):
            mv = ModelVersion(name=MODEL_NAME)
            with mock.patch("zenml.model.model_version.logger.info") as logger:
                model = mv._get_or_create_model()
                logger.assert_called_once()
            assert model.name == MODEL_NAME

    def test_model_exists(self):
        """Test if model fetched fine, if exists."""
        with ModelContext() as model:
            mv = ModelVersion(name=MODEL_NAME)
            with mock.patch(
                "zenml.model.model_version.logger.warning"
            ) as logger:
                model2 = mv._get_or_create_model()
                logger.assert_not_called()
            assert model.name == model2.name
            assert model.id == model2.id

    def test_model_create_model_and_version(self):
        """Test if model and version are created, not existing before."""
        with ModelContext(create_model=False):
            mv = ModelVersion(name=MODEL_NAME)
            with mock.patch("zenml.model.model_version.logger.info") as logger:
                mv = mv._get_or_create_model_version()
                logger.assert_called()
            assert mv.name == str(mv.number)
            assert mv.model.name == MODEL_NAME

    def test_model_fetch_model_and_version_by_number(self):
        """Test model and model version retrieval by exact version number."""
        with ModelContext(model_version="1.0.0") as (model, mv):
            mv = ModelVersion(name=MODEL_NAME, version="1.0.0")
            with mock.patch(
                "zenml.model.model_version.logger.warning"
            ) as logger:
                mv_test = mv._get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_number_not_found(self):
        """Test model and model version retrieval fails by exact version number, if version missing."""
        with ModelContext():
            mv = ModelVersion(name=MODEL_NAME, version="1.0.0")
            with pytest.raises(KeyError):
                mv._get_model_version()

    def test_model_fetch_model_and_version_by_stage(self):
        """Test model and model version retrieval by exact stage number."""
        with ModelContext(
            model_version="1.0.0", stage=ModelStages.PRODUCTION
        ) as (model, mv):
            mv = ModelVersion(name=MODEL_NAME, version=ModelStages.PRODUCTION)
            with mock.patch(
                "zenml.model.model_version.logger.warning"
            ) as logger:
                mv_test = mv._get_or_create_model_version()
                logger.assert_not_called()
            assert mv_test.id == mv.id
            assert mv_test.model.name == model.name

    def test_model_fetch_model_and_version_by_stage_not_found(self):
        """Test model and model version retrieval fails by exact stage number, if version in stage missing."""
        with ModelContext(model_version="1.0.0"):
            mv = ModelVersion(name=MODEL_NAME, version=ModelStages.PRODUCTION)
            with pytest.raises(KeyError):
                mv._get_model_version()

    def test_model_fetch_model_and_version_latest(self):
        """Test model and model version retrieval by latest version."""
        with ModelContext(model_version="1.0.0"):
            mv = ModelVersion(name=MODEL_NAME, version=ModelStages.LATEST)
            mv = mv._get_or_create_model_version()

            assert mv.name == "1.0.0"

    def test_init_stage_logic(self):
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

    def test_recovery_flow(self):
        """Test that model context can recover same version after failure."""
        with ModelContext():
            mv = ModelVersion(name=MODEL_NAME)
            mv1 = mv._get_or_create_model_version()
            del mv

            mv = ModelVersion(name=MODEL_NAME, version=1)
            mv2 = mv._get_or_create_model_version()

            assert mv1.id == mv2.id

    def test_tags_properly_created(self):
        """Test that model context can create proper tag relationships."""
        with model_killer():
            with tags_killer():
                Client().create_tag(TagRequestModel(name="foo", color="green"))
                mv = ModelVersion(
                    name=MODEL_NAME,
                    tags=["foo", "bar"],
                    delete_new_version_on_failure=False,
                )

                # run 2 times to first create, next get
                for _ in range(2):
                    model = mv._get_or_create_model()

                    assert len(model.tags) == 2
                    assert {t.name for t in model.tags} == {"foo", "bar"}
                    assert {
                        t.color for t in model.tags if t.name == "foo"
                    } == {"green"}

    def test_tags_properly_updated(self):
        """Test that model context can update proper tag relationships."""
        with model_killer():
            with tags_killer():
                mv = ModelVersion(
                    name=MODEL_NAME,
                    tags=["foo", "bar"],
                    delete_new_version_on_failure=False,
                )
                model_id = mv._get_or_create_model().id

                Client().update_model(model_id, add_tags=["tag1", "tag2"])
                model = mv._get_or_create_model()
                assert len(model.tags) == 4
                assert {t.name for t in model.tags} == {
                    "foo",
                    "bar",
                    "tag1",
                    "tag2",
                }

                Client().update_model(model_id, remove_tags=["tag1", "tag2"])
                model = mv._get_or_create_model()
                assert len(model.tags) == 2
                assert {t.name for t in model.tags} == {"foo", "bar"}

    def test_metadata_logging(self):
        """Test that model version can be used to track metadata from object."""
        with model_killer():
            mv = ModelVersion(
                name=MODEL_NAME,
                description="foo",
            )
            mv.log_metadata({"foo": "bar"})

            assert len(mv.metadata) == 1
            assert mv.metadata["foo"] == "bar"

            mv.log_metadata({"bar": "foo"})

            assert len(mv.metadata) == 2
            assert mv.metadata["foo"] == "bar"
            assert mv.metadata["bar"] == "foo"

    def test_metadata_logging_functional(self):
        """Test that model version can be used to track metadata from function."""
        with model_killer():
            mv = ModelVersion(
                name=MODEL_NAME,
                description="foo",
            )
            mv._get_or_create_model_version()

            log_model_version_metadata(
                {"foo": "bar"}, model_name=mv.name, model_version=mv.number
            )

            assert len(mv.metadata) == 1
            assert mv.metadata["foo"] == "bar"

            with pytest.raises(ValueError):
                log_model_version_metadata({"foo": "bar"})

            log_model_version_metadata(
                {"bar": "foo"}, model_name=mv.name, model_version="latest"
            )

            assert len(mv.metadata) == 2
            assert mv.metadata["foo"] == "bar"
            assert mv.metadata["bar"] == "foo"

    def test_metadata_logging_in_steps(self):
        """Test that model version can be used to track metadata from function in steps."""
        with model_killer():

            @pipeline(
                model_version=ModelVersion(
                    name=MODEL_NAME,
                ),
                enable_cache=False,
            )
            def my_pipeline():
                step_metadata_logging_functional()

            my_pipeline()

            mv = ModelVersion(name=MODEL_NAME, version="latest")
            assert len(mv.metadata) == 1
            assert mv.metadata["foo"] == "bar"
